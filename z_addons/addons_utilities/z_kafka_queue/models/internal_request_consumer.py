# -*- coding: utf-8 -*-

import logging
import threading
import json
from datetime import datetime
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka import Producer
from confluent_kafka.error import KafkaException, KafkaError
from odoo import models, fields, api, SUPERUSER_ID
from odoo import registry as registry_get
from odoo.tools import config

_logger = logging.getLogger(__name__)


class InternalRequestConsumer(models.Model):
    _name = 'internal.request.consumer'
    _description = 'ERP to WMS Internal Request Consumer'

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
            # consumer.subscribe(topic)
            consumer.assign([TopicPartition('erp.to.wms.internal.response', 0, 1)])
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
                    host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
                    irc_env = self.env['internal.request.consumer']
                    data = json.loads(message.value())
                    try:
                        _logger.warning('Message received: %s \n Offset: %s \n Partition: %s' % (
                            json.loads(message.value()), message.offset(), message.partition()))
                        # Đẩy dữ liệu tới kafka khi nhận yêu cầu
                        if 'response' not in data['objName'].lower():
                            received_obj_name, topic_send = irc_env.get_response_queue_data_by_obj_name(data['objName'])
                            msg_receive = irc_env.get_receive_msg_response(data, received_obj_name)
                            irc_env.action_producer_to_kafka(host, topic_send, msg_receive)
                        
                        data_created = False
                        picking_name = ''
                        # WMS-20
                        if data['objName'].lower() == 'erptowmsinternaluserequest' and 'actionType' in data and data['actionType'] == 'create':
                            odoo_msg_consumption, picking_name = self.action_sync_picking_internal(data)
                            data_created = True
                            _logger.warning('Odoo message consumption success with object: %s' % odoo_msg_consumption)
                        # WMS-27
                        elif data['objName'].lower() == 'erptowmssointernalrequest' and 'actionType' in data and data['actionType'] == 'create':
                            # odoo_msg_consumption = self.action_create_internal_sale_request(data)
                            # data_created = True
                            _logger.warning('Odoo message consumption success for WMS-27')
                        # WMS-28 - 1
                        elif data['objName'].lower() == 'erptowmspointernalrequest' and 'actionType' in data and data['actionType'] == 'create':
                            self.action_sync_erp_po_to_internal_transfer(data)
                            data_created = True
                            _logger.warning('Odoo message consumption success for WMS-28 - 1')
                        # WMS-28 - 2
                        elif data['objName'].lower() == 'erptowmsreceiptinternalrequest' and 'actionType' in data and data['actionType'] == 'create':
                            picking_name = self.action_create_internal_purchase_request(data)
                            data_created = True
                            _logger.warning('Odoo message consumption success for WMS-28 - 2')
                            _logger.warning('Odoo message consumption success with object: %s' % picking_name)
                        # WMS-21
                        elif data['objName'].lower() == 'erptowmspoimportgoodrequest' and 'actionType' in data and data['actionType'] == 'create':
                            odoo_msg_consumption = self.action_create_import_po_request(data)
                            data_created = True
                            _logger.warning('Odoo message consumption success for WMS-21')
                            _logger.warning('Odoo message consumption success with object: %s' % odoo_msg_consumption)
                        # Đẩy picking thành công (WMS-25) sang ERP thì lấy response để mapping id (tương đương với WMS-34)
                        elif data['objName'].lower() == 'erptowmssointernalresponse' and 'actionType' in data and data['actionType'] == 'create':
                            self.action_mapping_wms_ho_to_ho_request(data)
                            _logger.warning('Odoo message consumption success for WMS-25-ERP Response (WMS-34)')
                        # WMS-35
                        elif data['objName'].lower() == 'erptowmsreceiptinternalresponse' and 'actionType' in data and data['actionType'] == 'create':
                            self.action_sync_po_documents(data)
                            _logger.warning('Odoo message consumption success for WMS-35')
                        # 4.16. Request tạo thông tin hóa đơn nhập hàng mua nội bộ từ ERP sang WMS
                        elif data['objName'].lower() == 'erptowmspoinvoiceinternalrequest' and 'actionType' in data and data['actionType'] == 'create':
                            self.action_sync_po_invoice(data)
                            _logger.warning('Odoo message consumption success for 4.16. Request tạo thông tin hóa đơn nhập hàng mua nội bộ từ ERP sang WMS')
                        else:
                            pass
                        
                        # Đẩy dữ liệu về kafka khi tạo phiếu thành công
                        if data_created:
                            created_obj_name, topic_send = irc_env.get_response_queue_data_by_obj_name(data['objName'])
                            msg_create = irc_env.get_success_create_msg_response(data, created_obj_name, picking_name)
                            irc_env.action_producer_to_kafka(host, topic_send, msg_create)
                    except Exception as ex:
                        # Đẩy dữ liệu tới kafka khi tạo phiếu lỗi
                        error_obj_name, topic_send = irc_env.get_response_queue_data_by_obj_name(data['objName'])
                        msg_error = irc_env.get_error_msg_response(data, ex, error_obj_name)
                        irc_env.action_producer_to_kafka(host, topic_send, msg_error)
        except Exception as ex:
            _logger.error('Error running consuming kafka queue: %s' % ex)
        finally:
            self._running_threads[topic[0]] = False
        return {}
    
    @api.model
    def action_producer_to_kafka(self, host, topic, msg):
        conf = {
            'bootstrap.servers': '%s' % host,
        }
        producer = Producer(conf)
        producer.produce(topic, json.dumps(msg).encode('utf-8'))
        producer.flush()

    @api.model
    def get_receive_msg_response(self, data, obj_name):
        obj_data = data['objData']
        message_id = self.env['stock.picking']._generate_queue_message_id()
        receive_obj_data = obj_data
        receive_obj_data['status'] = 'success'
        receive_obj_data['message'] = 'receive successfully'
        receive_obj_data['messageReceiveId'] = data.get('messageId', '')
        receive_obj_data['requestId'] = ''
        receive_obj_data['errorDetails'] = None
        receive_obj_data['fromSource'] = {
            'source': 'WMS',
            'clientId': 1000001,
        }
        return {
            "messageId": message_id,
            "objName": obj_name,
            "actionType": "receive",
            "objData": receive_obj_data
        }

    @api.model
    def get_success_create_msg_response(self, data, obj_name, picking_name):
        obj_data = data['objData']
        message_id = self.env['stock.picking']._generate_queue_message_id()
        create_obj_data = obj_data
        create_obj_data['status'] = 'success'
        create_obj_data['message'] = 'create successfully'
        create_obj_data['requestId'] = picking_name
        create_obj_data['errorDetails'] = None
        create_obj_data['fromSource'] = {
            'source': 'WMS',
            'clientId': 1000001,
        }
        return {
            "messageId": message_id,
            "objName": obj_name,
            "actionType": "create",
            "objData": create_obj_data
        }

    @api.model
    def get_error_msg_response(self, data, error, obj_name):
        obj_data = data['objData']
        message_id = self.env['stock.picking']._generate_queue_message_id()
        error_obj_data = obj_data
        error_obj_data['status'] = 'error'
        error_obj_data['message'] = 'Invalid request data'
        error_obj_data['requestId'] = ''
        error_obj_data['errorDetails'] = {
            'pathCode': "code from WMS",
            'errorMsg': str(error)
        }
        return {
            "messageId": message_id,
            "objName": obj_name,
            "actionType": "create",
            "objData": error_obj_data
        }

    @api.model
    def get_response_queue_data_by_obj_name(self, obj_name):
        # Trả về dữ liệu objName, queue nam của response cần gửi
        if obj_name == 'erpToWmsInternalUseRequest':
            return "wmsToErpInternalUseResponse", "wms.to.erp.internaluse.response"
        elif obj_name == 'erpToWmsPOImportGoodRequest':
            return "wmsToErpPOImportGoodResponse", "wms.to.erp.poimportgood.response"
        elif obj_name == 'erpToWmsSOInternalRequest':
            return "wmsToErpSOInternalResponse", "wms.to.erp.internal.response"
        elif obj_name == 'erpToWmsPOInternalRequest':
            return "wmsToErpPOInternalResponse", "wms.to.erp.internal.response"
        elif obj_name == 'erpToWmsReceiptInternalRequest':
            return "wmsToErpReceiptInternalResponse", "wms.to.erp.internal.response"
        elif obj_name == 'erpToWmsTransferRequest':
            return "wmsToErpTransferResponse", "wms.to.erp.transfer.response"
        elif obj_name == 'erpToWmsPhysicalInventoryRequest':
            return "wmsToErpPhysicalInventoryResponse", "wms.to.erp.physicalinv.response"
        else:
            return '', ''

    def action_sync_picking_internal(self, data):
        internalUseInfo = data['objData']['internalUseInfo']
        fromSource = data['objData']['fromSource']
        sourceWarehouse = data['objData']['sourceWarehouse']
        departmentInfo = data['objData']['departmentInfo']
        requestedBy = data['objData']['requestedBy']
        items = data['objData']['items']
        warehouseId = sourceWarehouse['warehouseId']
        note = data['objData']['remarks']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            warehouse = env['stock.warehouse'].search([('erp_warehouse_id', '=', warehouseId)], limit=1)
            user_id = env['res.users'].search([('erp_user_id', '=', requestedBy['userId'])], limit=1)
            department = env['erp.hr.departmnet'].search([('erp_hr_department_id', '=', departmentInfo['departmentId'])], limit=1)
            val = {
                'erp_document_id': internalUseInfo['documentId'],
                'erp_document_no': internalUseInfo['documentNo'],
                'erp_org_id': internalUseInfo['orgId'],
                'z_transfer_type_sync': 'erp_internal_export',
                'erp_client_id': fromSource['clientId'],
                'picking_type_id': warehouse.out_type_id.id,
                'source_warehouse_id': warehouse.id,
                'schedule_date': datetime.fromtimestamp(data['objData']['requestDate'] / 1000),
                'erp_user_id': requestedBy['userId'],
                'department_id': department.id,
                'erp_state_document': internalUseInfo['documentStatus'],
                'erp_created_at': datetime.fromtimestamp(internalUseInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(internalUseInfo['updatedAt'] / 1000),
                'note': note,
            }
            stock_picking = env['stock.picking'].search([('erp_document_id', '=', internalUseInfo['documentId'])], limit=1)
            if stock_picking:
                pass
            else:
                stock_picking = env['stock.picking'].create(val)
                stock_picking.user_id = user_id.id
                stock_picking.erp_msg_create = data
                product_by_barcode = env['product.product'].search([('barcode', '=', items['barcodeValue'])])
                product_uom = env['uom.uom'].search([('erp_uom_id', '=', items['uomId'])])
                val_stock_move = {
                    'erp_line_id': items['lineId'],
                    'picking_id': stock_picking.id,
                    'product_id': product_by_barcode.id,
                    'product_uom_qty': items['quantity'],
                    'product_uom': product_uom.id,
                }
                stock_move = env['stock.move'].search([('erp_line_id', '=', items['lineId']), ('picking_id', '=', stock_picking.id)], limit=1)
                if stock_move:
                    pass
                else:
                    stock_move = env['stock.move'].create(val_stock_move)
            stock_picking.action_confirm()
            return stock_picking, stock_picking.name

    # không tạo thêm nữa do đây là SO đẩy về mà thông tin SO này lấy từ response khi đẩy phiếu điều chuyển nội bộ sang
    def action_create_internal_sale_request(self, data):
        soInternalOrderInfo = data['objData']['soInternalOrderInfo']
        fromSource = data['objData']['fromSource']
        sourceWarehouse = data['objData']['sourceWarehouse']
        destinationWarehouse = data['objData']['destinationWarehouse']
        requestedBy = data['objData']['requestedBy']
        soInternalInOutInfo = data['objData']['soInternalInOutInfo'][0]
        items = soInternalInOutInfo['inOutLinesInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            source_warehouse = env['stock.warehouse'].search([('erp_warehouse_id', '=', sourceWarehouse['warehouseId'])], limit=1)
            destination_warehouse = env['stock.warehouse'].search([('erp_warehouse_id', '=', destinationWarehouse['warehouseId'])], limit=1)
            user = env['res.users'].search([('erp_user_id', '=', requestedBy['userId'])])
            val = {
                'erp_document_id': soInternalInOutInfo['documentId'],
                'erp_so_internal_no': soInternalOrderInfo['documentNo'],
                'erp_so_internal_id': soInternalOrderInfo['documentId'],
                'erp_document_no': soInternalInOutInfo['documentNo'],
                'erp_org_id': soInternalInOutInfo['orgId'],
                'erp_client_id': fromSource['clientId'],
                'picking_type_id': source_warehouse.int_type_id.id,
                'warehouse_id': source_warehouse.id,
                'warehouse_dest_id': destination_warehouse.id,
                'schedule_date': datetime.fromtimestamp(data['objData']['requestDate'] / 1000),
                'erp_user_id': requestedBy['userId'],
                'z_transfer_type_sync': 'erp_internal_sale',
                'erp_state_document': soInternalInOutInfo['documentStatus'],
                'erp_created_at': datetime.fromtimestamp(soInternalInOutInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(soInternalInOutInfo['updatedAt'] / 1000),
                'note': data['objData']['remarks'],
            }
            stock_picking = env['stock.picking'].search([('erp_document_id', '=', soInternalOrderInfo['documentId'])], limit=1)
            if stock_picking:
                pass
            else:
                stock_picking = env['stock.picking'].create(val)
                stock_picking.user_id = user.id
                stock_picking.erp_msg_create = data
            erp_barcode = env['erp.barcode'].search([('erp_barcode_id', '=', items['barcodeId'])], limit=1)
            product = env['product.product'].search([('barcode', '=', erp_barcode.erp_barcode_value)], limit=1)
            val_stock_move = {
                'erp_line_id': items['inOutLineId'],
                'erp_barcode_id': items['barcodeId'],
                'picking_id': stock_picking.id,
                'product_id': product.id,
                'product_uom_qty': items['quantity'],
                'product_uom': product.uom_id.id,
            }
            stock_move = env['stock.move'].search([('erp_line_id', '=', items['inOutLineId']), ('picking_id', '=', stock_picking.id)], limit=1)
            if stock_move:
                stock_move.write(val_stock_move)
            else:
                env['stock.move'].create(val_stock_move)
            return stock_picking

    # ERP đẩy về thông tin phiếu nhập, không xử lý gì vì thông tin phiếu nhập + xuất trên ERP = 1 phiếu điều chuyển nội bộ trên WMS
    # đẩy message về cho ERP
    def action_create_internal_purchase_request(self, data):
        poInternalOrderInfo = data['objData']['poInternalOrderInfo']
        soInternalInvoiceInfo = poInternalOrderInfo['soInternalInvoiceInfo']
        soOrderId = soInternalInvoiceInfo['soOrderId']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            stock_picking = env['stock.picking'].search([('erp_so_internal_id', '=', soOrderId)], limit=1)
            return stock_picking.name if stock_picking else ''

    def action_sync_erp_po_to_internal_transfer(self, data):
        poInternalOrderInfo = data['objData']['poInternalOrderInfo']
        soInternalInvoiceInfo = poInternalOrderInfo['soInternalInvoiceInfo']
        soOrderId = soInternalInvoiceInfo['soOrderId']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            stock_picking = env['stock.picking'].search([('erp_so_internal_id', '=', soOrderId)], limit=1)
            if stock_picking:
                stock_picking.write({'po_internal_order_info': poInternalOrderInfo})
                return stock_picking

    def action_create_import_po_request(self, data):
        POImportGoodInfo = data['objData']['POImportGoodInfo']
        customsDeclarationInfo = POImportGoodInfo['customsDeclarationInfo']
        fromSource = data['objData']['fromSource']
        sourceWarehouse = data['objData']['sourceWarehouse']
        requestedBy = data['objData']['requestedBy']
        items = data['objData']['items']
        vendorInfo = POImportGoodInfo['vendorInfo']
        erp_partner_id = vendorInfo['bpartnerId']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            # sinh biến thể sản phẩm
            env['product.template'].action_init_product_product(items['productCode'], items['barcodeId'])
            partner = env['res.partner'].search([('erp_bpartner_id', '=', erp_partner_id)], limit=1)
            source_warehouse = env['stock.warehouse'].search([('erp_warehouse_id', '=', sourceWarehouse['warehouseId'])], limit=1)
            user = env['res.users'].search([('erp_user_id', '=', requestedBy['userId'])])
            val = {
                'erp_document_id': POImportGoodInfo['documentId'],
                'erp_document_no': POImportGoodInfo['documentNo'],
                'erp_org_id': POImportGoodInfo['orgId'],
                'z_transfer_type_sync': 'erp_foreign_trade',
                'partner_id': partner.id if partner else False,
                'erp_client_id': fromSource['clientId'],
                'picking_type_id': source_warehouse.in_type_id.id,
                'warehouse_dest_id': source_warehouse.id,
                'scheduled_date': datetime.fromtimestamp(data['objData']['requestDate'] / 1000),
                'erp_user_id': requestedBy['userId'],
                # 'erp_state_document': POImportGoodInfo['documentStatus'],
                'erp_created_at': datetime.fromtimestamp(POImportGoodInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(POImportGoodInfo['updatedAt'] / 1000),
                'note': data['objData']['remarks'],
            }
            stock_picking = env['stock.picking'].search([('erp_document_id', '=', POImportGoodInfo['documentId'])], limit=1)
            if stock_picking:
                pass
            else:
                stock_picking = env['stock.picking'].create(val)
                stock_picking.user_id = user.id
                stock_picking.erp_msg_create = data
            product = env['product.product'].search([('barcode', '=', items['barcodeValue'])], limit=1)
            uom = env['uom.uom'].search([('erp_uom_id', '=', items['uomId'])], limit=1)
            val_stock_move = {
                'name': stock_picking.name,
                'erp_line_id': items['lineId'],
                'erp_barcode_id': items['barcodeId'],
                'picking_id': stock_picking.id,
                'product_id': product.id,
                'product_uom_qty': items['quantity'],
                'product_uom': uom.id,
                'location_id': env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': source_warehouse.lot_stock_id.id,
            }
            stock_move = env['stock.move'].search([('erp_line_id', '=', items['lineId']), ('picking_id', '=', stock_picking.id)], limit=1)
            if stock_move:
                stock_move.write(val_stock_move)
            else:
                env['stock.move'].create(val_stock_move)
            # WMS-06 tạo danh mục Tờ khai nhập khẩu
            if customsDeclarationInfo:
                customs_declaration_val = {
                    "erp_id": customsDeclarationInfo['declarationId'],
                    "number_declaration": customsDeclarationInfo['declarationNo'],
                    "name": customsDeclarationInfo['declarationName'],
                    "description": customsDeclarationInfo['declarationDescription'],
                    "date": datetime.fromtimestamp(customsDeclarationInfo['declarationDate'] / 1000) if customsDeclarationInfo['declarationDate'] else False,
                }
                customs_declaration_record = env['stock.customs.declaration'].search([('erp_id', '=', customsDeclarationInfo['declarationId'])], limit=1)
                if customs_declaration_record:
                    customs_declaration_record.write(customs_declaration_val)
                else:
                    env['stock.customs.declaration'].create(customs_declaration_val)
            return stock_picking

    def action_mapping_wms_ho_to_ho_request(self, data):
        requestId = data['objData'].get('requestId', False)
        soInternalOrderInfo = data['objData'].get('soInternalOrderInfo', False)
        soInternalInvoiceInfo = data['objData'].get('soInternalInvoiceInfo', False)
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if requestId:
                stock_picking = env['stock.picking'].search([('name', '=', requestId)], limit=1)
                picking_val = {}
                if soInternalOrderInfo:
                    erp_so_internal_id = soInternalOrderInfo.get('documentId', False)
                    picking_val['erp_so_internal_id'] = erp_so_internal_id
                if soInternalOrderInfo:
                    picking_val['so_internal_order_info'] = soInternalOrderInfo
                if soInternalInvoiceInfo:
                    if len(soInternalInvoiceInfo) > 0:
                        picking_val['so_internal_invoice_info'] = soInternalInvoiceInfo[0]
                if stock_picking:
                    stock_picking.write(picking_val)

    def action_sync_po_documents(self, data):
        requestId = data['objData'].get('requestId', False)
        poInternalOrderInfo = data['objData'].get('poInternalOrderInfo', False)
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if requestId:
                stock_picking = env['stock.picking'].search([('name', '=', requestId)], limit=1)
                picking_val = {}
                if poInternalOrderInfo:
                    picking_val['po_internal_order_info'] = poInternalOrderInfo
                if stock_picking:
                    stock_picking.write(picking_val)

    def action_sync_po_invoice(self, data):
        poInternalOrderInfo = data['objData']['poInternalOrderInfo']
        poInternalInvoiceInfo = data['objData']['poInternalInvoiceInfo']
        soInternalInvoiceInfo = poInternalOrderInfo['soInternalInvoiceInfo']
        soOrderId = soInternalInvoiceInfo['soOrderId']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            stock_picking = env['stock.picking'].search([('erp_so_internal_id', '=', soOrderId)], limit=1)
            if stock_picking:
                stock_picking.write({'po_internal_invoice_info': poInternalInvoiceInfo})