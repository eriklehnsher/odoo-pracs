# -*- coding: utf-8 -*-

import logging
import threading
from datetime import datetime
import json
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka import Producer
from confluent_kafka.error import KafkaException, KafkaError
from odoo import models, fields, api, SUPERUSER_ID
from odoo import registry as registry_get
from odoo.tools import config

_logger = logging.getLogger(__name__)


class StockTransferConsumer(models.Model):
    _name = 'stock.transfer.consumer'
    _description = 'Stock Transfer Consumer'

    _running_threads = {}

    def _is_thread_running(self, topic):
        return self._running_threads.get(topic[0], False)

    def _start_thread(self, topic, host_port, group_id):
        _logger.warning('Start thread.....')
        threaded_calculation = threading.Thread(target=self.start_consumer_cron,
                                                args=(topic, host_port, group_id))
        threaded_calculation.daemon = True
        threaded_calculation.start()
        self._running_threads[topic[0]] = True
        threaded_calculation.join()
        _logger.error(threaded_calculation.is_alive())

    def receive_response(self, topic, host_port, group_id):
        if not self._is_thread_running(topic):
            self._start_thread(topic, host_port, group_id)

    def start_consumer_cron(self, topic, host_port, group_id):
        try:
            consumer_conf = {
                'bootstrap.servers': str(host_port),
                'group.id': str(group_id),
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
            }
            consumer = Consumer(consumer_conf)
            consumer.subscribe(topic)
            while True:
                message = consumer.poll(timeout=5)
                if message is None:
                    continue
                elif message.error():
                    if message.error().code == KafkaError._PARTITION_EOF:
                        _logger.error('Error kafka partition: %s [%d] reached end at offset %d' % (
                            message.topic(), message.partition(), message.offset()
                        ))
                    elif message.error():
                        self._running_threads[topic[0]] = False
                        raise KafkaException(message.error())
                else:
                    _logger.warning('Message received: %s \n Offset: %s \n Partition: %s' % (
                        json.loads(message.value()), message.offset(), message.partition()))
                    data = json.loads(message.value())
                    try:
                        # Giao dịch chuyển khi thực hiện trên WMS
                        # Lưu message ERP trả về khi gửi dữ liệu thành công
                        with registry_get(self.env.cr.dbname).cursor() as cr:
                            env = api.Environment(cr, SUPERUSER_ID, {})
                            # Giao dịch chuyển kho thực hiện trên ERP, đẩy dữ liệu về WMS
                            # WMS tạo picking sau đó đẩy dữ liệu nhận/tạo mới/lỗi về ERP
                            if data['objName'] == 'erpToWmsTransferRequest' and (
                                    'actionType' in data and data['actionType'] == 'create'):
                                msg_log = env['msg.log'].create({
                                    'message_receive': data,
                                    'topic_receive': 'erp.to.wms.transfer.request',
                                    'action_type': 'create',
                                    'obj_name': 'erpToWmsTransferRequest',
                                })
                                # Gửi lại message khi nhận message thành công
                                self.action_send_msg_when_receive_msg(data, msg_log)
                                # WMS-23/ WMS-24
                                odoo_message_consumption = self.action_sync_stock_picking(data)
                                _logger.warning(
                                    'Odoo message consumption success with object: %s' % odoo_message_consumption)
                            # WMS-29
                            elif data['objName'] == 'erpToWmsTransferResponse' and (
                                    'actionType' in data and data['actionType'] == 'create'):
                                self.action_confirm_picking_from_erp(data)
                            # WMS-30
                            elif data['objName'] == 'erpToWmsTransferRequest' and (
                                    'actionType' in data and data['actionType'] == 'confirm'):
                                # Gửi lại message khi nhận message thành công
                                self.action_send_msg_when_confirm_picking_success(data)
                                self.action_complete_picking_from_erp(data)
                    except Exception as ex:
                        _logger.error('Error sync stock transfer: %s' % ex)
        except Exception as ex:
            _logger.error('Error running consuming kafka queue: %s' % ex)
        finally:
            self._running_threads[topic[0]] = False
        return {}

    def action_producer_to_kafka(self, host, topic, msg):
        conf = {
            'bootstrap.servers': '%s' % host,
        }
        producer = Producer(conf)
        producer.produce(topic, json.dumps(msg).encode('utf-8'))
        producer.flush()

    # WMS-23, WMS-24
    def action_sync_stock_picking(self, data):
        movementInfo = data['objData']['movementInfo']
        fromSource = data['objData']['fromSource']
        sourceWarehouse = data['objData']['sourceWarehouse']
        warehouseCode = sourceWarehouse['warehouseCode']
        destinationWarehouse = data['objData']['destinationWarehouse']
        requestedBy = data['objData']['requestedBy']
        departmentInfo = data['objData']['departmentInfo']
        items = data['objData']['items']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            source_warehouse = env['stock.warehouse'].search(
                [('erp_warehouse_id', '=', sourceWarehouse['warehouseId'])], limit=1)
            destination_warehouse = env['stock.warehouse'].search(
                [('erp_warehouse_id', '=', destinationWarehouse['warehouseId'])], limit=1)
            department = env['erp.hr.department'].search([('erp_hr_department_id', '=', departmentInfo['departmentId'])]) if departmentInfo else None
            z_transfer_type_sync = 'erp_ho_to_shop'
            if warehouseCode.lower() not in ('han.ho', 'hcmho'):
                z_transfer_type_sync = 'erp_shop_to_ho'
            picking_type_id = source_warehouse.out_type_id
            user_id = env['res.users'].search([('erp_user_id', '=', requestedBy['userId'])], limit=1)
            val = {
                'erp_org_id': movementInfo['orgId'],
                'picking_type_id': picking_type_id.id,
                'z_transfer_type_sync': z_transfer_type_sync,
                'erp_document_no': movementInfo['documentNo'],
                'erp_document_id': movementInfo['documentId'],
                'erp_document_status': movementInfo['documentStatus'],
                'erp_document_type_id': movementInfo['documentTypeInfo']['documentTypeId'],
                'erp_created_at': datetime.fromtimestamp(movementInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(movementInfo['updatedAt'] / 1000),
                'erp_document_confirm_id': movementInfo['documentConfirmId'],
                'erp_document_confirm_no': movementInfo['documentConfirmNo'],
                'erp_client_id': fromSource['clientId'],
                'warehouse_id': source_warehouse.id,
                'warehouse_dest_id': destination_warehouse.id,
                'erp_user_id': requestedBy['userId'],
                'department_id': department.id if department else None,
                'erp_msg_create': data,
            }
            if z_transfer_type_sync == 'erp_shop_to_ho':
                picking_type_id = source_warehouse.in_type_id
                val = {
                    'erp_org_id': movementInfo['orgId'],
                    'picking_type_id': picking_type_id.id,
                    'z_transfer_type_sync': z_transfer_type_sync,
                    'erp_document_no': movementInfo['documentNo'],
                    'erp_document_id': movementInfo['documentId'],
                    'erp_document_status': movementInfo['documentStatus'],
                    'erp_document_type_id': movementInfo['documentTypeInfo']['documentTypeId'],
                    'erp_created_at': datetime.fromtimestamp(movementInfo['createdAt'] / 1000),
                    'erp_updated_at': datetime.fromtimestamp(movementInfo['updatedAt'] / 1000),
                    'erp_document_confirm_id': movementInfo['documentConfirmId'],
                    'erp_document_confirm_no': movementInfo['documentConfirmNo'],
                    'erp_client_id': fromSource['clientId'],
                    'warehouse_id': source_warehouse.id,
                    'warehouse_dest_id': destination_warehouse.id,
                    'erp_user_id': requestedBy['userId'],
                    'department_id': department.id if department else None,
                    'erp_msg_create': data,
                }
            stock_picking = env['stock.picking'].search([('erp_document_id', '=', movementInfo['documentId'])], limit=1)
            if stock_picking:
                pass
            else:
                stock_picking = env['stock.picking'].create(val)
                stock_picking.user_id = user_id.id
                stock_picking.erp_msg_create = data
            val_move = {
                'name': stock_picking.name,
                'picking_id': stock_picking.id,
                'erp_line_id': items['lineId'],
                'location_id': source_warehouse.lot_stock_id.id,
                'location_dest_id': env['stock.location'].search([('usage', '=', 'customer')], limit=1).id,
                'product_id': env['product.product'].search([('barcode', '=', items['barcodeValue'])]).id,
                'product_uom_qty': items['quantity'],
                'product_uom': env['uom.uom'].search([('erp_uom_id', '=', items['uomId'])]).id,
            }
            if z_transfer_type_sync == 'erp_shop_to_ho':
                val_move = {
                    'name': stock_picking.name,
                    'picking_id': stock_picking.id,
                    'erp_line_id': items['lineId'],
                    'location_id': env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id,
                    'location_dest_id': destination_warehouse.lot_stock_id.id,
                    'product_id': env['product.product'].search([('barcode', '=', items['barcodeValue'])]).id,
                    'product_uom_qty': items['quantity'],
                    'product_uom': env['uom.uom'].search([('erp_uom_id', '=', items['uomId'])]).id,
                }
            stock_move = env['stock.move'].search(
                [('picking_id', '=', stock_picking.id), ('erp_line_id', '=', items['lineId'])])
            if stock_move:
                pass
            else:
                env['stock.move'].create(val_move)
            stock_picking.action_confirm()
            return [stock_picking, stock_picking.name]

    def action_confirm_picking_from_erp(self, data):
        objData = data.get('objData', {})
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if objData:
                status = objData.get('status', False)
                if status == 'success':
                    picking_name = objData.get('requestId', False)
                    movementInfo = objData.get('movementInfo', False)
                    if picking_name and movementInfo:
                        erp_picking_id = movementInfo.get('documentId', False)
                        erp_picking_no = movementInfo.get('documentNo', False)
                        erp_org_id = movementInfo.get('orgId', False)
                        erp_document_status = movementInfo.get('documentStatus', False)
                        erp_document_confirm_id = movementInfo.get('documentConfirmId', False)
                        erp_document_confirm_no = movementInfo.get('documentConfirmNo', False)
                        if erp_picking_id:
                            picking = env['stock.picking'].search([('name', '=', picking_name)])
                            if picking:
                                picking.write({
                                    'erp_document_id': erp_picking_id,
                                    'erp_document_no': erp_picking_no,
                                    'erp_org_id': erp_org_id,
                                    'erp_document_status': erp_document_status,
                                    'erp_document_confirm_id': erp_document_confirm_id,
                                    'erp_document_confirm_no': erp_document_confirm_no,
                                })

    def action_complete_picking_from_erp(self, data):
        objData = data.get('objData', {})
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if objData:
                movementInfo = objData.get('movementInfo', {})
                if movementInfo:
                    erp_picking_id = movementInfo.get('documentId', False)
                    erp_document_status = movementInfo.get('documentStatus', False)
                    picking = env['stock.picking'].search([('erp_document_id', '=', erp_picking_id)], limit=1)
                    if picking:
                        picking.button_validate()

    def action_send_msg_when_receive_msg(self, data, msg_log):
        topic_send = 'wms.to.erp.transfer.response'
        host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
        message_id = self.env['stock.picking']._generate_queue_message_id()
        msg_receive = {
            'messageId': message_id,
            'objName': 'wmsToErpTransferResponse',
            'actionType': 'receive',
            'objData': {
                'status': 'success',
                'message': 'receive successfully',
                'messageReceiveId': data['messageId'],
                'fromSource': {'source': 'WMS', 'clientId': 1000001},
                'movementInfo': data['objData']['movementInfo'],
                'errorDetails': None
            }
        }
        self.action_producer_to_kafka(host, topic_send, msg_receive)
        msg_log.write({
            'topic_send': topic_send,
            'message_send': msg_receive,
        })

    def action_send_msg_when_confirm_picking_success(self, data):
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            msg_log = env['msg.log'].create({
                'message_receive': data,
                'topic_receive': 'erp.to.wms.transfer.request',
                'obj_name': 'wmsToErpTransferResponse',
                'action_type': 'receive',
            })
            topic_send = 'wms.to.erp.transfer.response'
            host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
            request_id = ''
            movementInfo = data['objData'].get('movementInfo', {})
            erp_picking_id = movementInfo.get('documentId', False)
            erp_picking_id = movementInfo.get('documentId', False)
            erp_document_status = movementInfo.get('documentStatus', False)
            picking = env['stock.picking'].search([('erp_document_id', '=', erp_picking_id)], limit=1)
            request_id = picking.name
            msg_send_receive = {
                'messageId': env['stock.picking']._generate_queue_message_id(),
                'objName': 'wmsToErpTransferResponse',
                'actionType': 'receive',
                'objData': {
                    'status': 'success',
                    'message': 'receive successfully',
                    'messageReceiveId': data['messageId'],
                    'requestId': request_id,
                    'fromSource': {
                        'source': 'WMS',
                        'clientId': 1000001
                    },
                    'movementInfo': data['objData']['movementInfo'],
                    'errorDetails': None
                }
            }
            self.action_producer_to_kafka(host, topic_send, msg_send_receive)
            msg_log.write({
                'message_send': msg_send_receive,
                'topic_send': 'wms.to.erp.transfer.response',
            })
