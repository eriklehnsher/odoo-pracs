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


class StockInventoryConsumer(models.Model):
    _name = 'stock.inventory.consumer'
    _description = 'Stock Inventory Consumer'

    _running_threads = {}

    def _is_thread_running(self, topic):
        return self._running_threads.get(topic, False)

    def _start_thread(self, topic, host_port, group_id):
        _logger.warning('Start thread.....')
        threaded_calculation = threading.Thread(target=self.start_consumer_cron,
                                                args=(topic, host_port, group_id))
        threaded_calculation.daemon = True
        threaded_calculation.start()
        self._running_threads[topic] = True
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
            consumer.subscribe([topic])
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
                        self._running_threads[topic] = False
                        raise KafkaException(message.error())
                else:
                    data = json.loads(message.value())
                    _logger.warning('Message received: %s \n Offset: %s \n Partition: %s' % (
                        json.loads(message.value()), message.offset(), message.partition()))
                    try:
                        # Lưu message trả về khi gửi request tạo phiếu kiểm kê từ wms => erp: erp tạo phiếu kiểm kê
                        with registry_get(self.env.cr.dbname).cursor() as cr:
                            env = api.Environment(cr, SUPERUSER_ID, {})
                            if data['objName'] == 'erpToWmsPhysicalInventoryResponse':
                                actionType = data['actionType']
                                requestId = data['objData']['requestId']
                                stock_inventory = env['stock.inventory'].search([('code', '=', requestId)])
                                if actionType == 'receive':
                                    stock_inventory.erp_message_receive = str(data)
                                elif actionType == 'create':
                                    if data['objData']['status'] == 'success':
                                        stock_inventory.erp_message_create = str(data)
                                elif actionType == 'error':
                                    if data['objData']['status'] == 'error':
                                        stock_inventory.erp_message_error = str(data)
                                else:
                                    pass

                            # Đồng bộ tạo lệnh kiểm kê từ ERP sang WMS: WMS tạo phiếu kiểm kê
                            if data['objName'] == 'erpToWmsPhysicalInventoryRequest' and data['actionType'] == 'create':
                                topic = 'wms.to.erp.physicalinv.response'
                                host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
                                message_id = self.env['stock.picking']._generate_queue_message_id()
                                msg_receive = {
                                    "messageId": message_id,
                                    "objName": "wmsToErpPhysicalInventoryResponse",
                                    "actionType": "receive",
                                    "objData": {
                                        "status": "success",
                                        "message": "receive successfully",
                                        "messageReceiveId": data['messageId'],
                                        "requestId": "",
                                        "fromSource": {
                                            "source": "ERP",
                                            "clientId": data['objData']['fromSource']['clientId'],
                                        },
                                        "errorDetails": None
                                    }
                                }
                                self.action_producer_to_kafka(host, topic, msg_receive)
                                odoo_message_consumption = self.action_sync_stock_inventory(data)
                                _logger.warning(
                                    'Odoo message consumption success with object: %s' % odoo_message_consumption)
                                message_id = self.env['stock.picking']._generate_queue_message_id()
                                msg_create = {
                                    "messageId": message_id,
                                    "objName": "wmsToErpPhysicalInventoryResponse",
                                    "actionType": "create",
                                    "objData": {
                                        "status": "success",
                                        "message": "create successfully",
                                        "requestId": "",
                                        "fromSource": {
                                            "source": "ERP",
                                            "clientId": data['objData']['fromSource']['clientId'],
                                        },
                                        "physicalInfo": {
                                            "orgId": data['objData']['physicalInfo']['orgId'],
                                            "documentNo": data['objData']['physicalInfo']['documentNo'],
                                            "documentId": data['objData']['physicalInfo']['documentId'],
                                            "documentStatus": data['objData']['physicalInfo']['documentStatus'],
                                            "createdAt": data['objData']['physicalInfo']['createdAt'],
                                            "updatedAt": data['objData']['physicalInfo']['updatedAt'],
                                        },
                                        "errorDetails": None
                                    }
                                }
                                self.action_producer_to_kafka(host, topic, msg_create)
                    except Exception as ex:
                        message_id = self.env['stock.picking']._generate_queue_message_id()
                        msg_error = {
                            "messageId": message_id,
                            "objName": "wmsToErpPhysicalInventoryResponse",
                            "actionType": "create",
                            "objData": {
                                "status": "error",
                                "message": "Lỗi đồng bộ phiếu kiểm kê từ ERP sang WMS.",
                                "requestId": "",
                                "fromSource": {
                                    "source": "ERP",
                                    "clientId": data['objData']['fromSource']['clientId'],
                                },
                                "physicalInfo": {
                                    "orgId": data['objData']['physicalInfo']['orgId'],
                                    "documentNo": data['objData']['physicalInfo']['documentNo'],
                                    "documentId": data['objData']['physicalInfo']['documentId'],
                                    "documentStatus": data['objData']['physicalInfo']['documentStatus'],
                                    "createdAt": data['objData']['physicalInfo']['createdAt'],
                                    "updatedAt": data['objData']['physicalInfo']['updatedAt'],
                                },
                                "errorDetails": {
                                    "pathCode": "500",
                                    "errorMsg": str(ex)
                                }
                            }
                        }
                        self.action_producer_to_kafka(host, topic, msg_error)
        except Exception as ex:
            _logger.error('Error running consuming kafka queue: %s' % ex)
        finally:
            self._running_threads[topic] = False
        return {}

    def action_producer_to_kafka(self, host, topic, msg):
        conf = {
            'bootstrap.servers': '%s' % host,
        }
        producer = Producer(conf)
        producer.produce(topic, json.dumps(msg).encode('utf-8'))
        producer.flush()

    def action_sync_stock_inventory(self, data):
        physicalInfo = data['objData']['physicalInfo']
        fromSource = data['objData']['fromSource']
        sourceWarehouse = data['objData']['sourceWarehouse']
        requestedBy = data['objData']['requestedBy']
        items = data['objData']['items']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            warehouse = env['stock.warehouse'].search([('erp_warehouse_id', '=', sourceWarehouse['warehouseId'])])
            val = {
                'erp_org_id': physicalInfo['orgId'],
                'erp_client_id': fromSource['clientId'],
                'erp_document_no': physicalInfo['documentNo'],
                'erp_document_id': physicalInfo['documentId'],
                'erp_document_state': physicalInfo['documentStatus'],
                'erp_document_type_id': physicalInfo['documentTypeId'],
                'erp_created_at': datetime.fromtimestamp(physicalInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(physicalInfo['updatedAt'] / 1000),
                'warehouse_id': warehouse.id,
                'date': datetime.fromtimestamp(data['objData']['requestDate'] / 1000),
                'erp_created_uid': requestedBy['userId'],
            }
            stock_inventory = env['stock.inventory'].search([('erp_document_id', '=', physicalInfo['documentId'])], limit=1)
            if stock_inventory:
                stock_inventory.write(val)
            else:
                stock_inventory = env['stock.inventory'].create(val)
            for item in items:
                item_val = {
                    'erp_line_id': item['lineId'],
                    'product_id': env['product.product'].search([('barcode', '=', item['barcodeValue'])]).id,
                    'erp_barcode_id': item['barcodeId'],
                    'erp_barcode_value': item['barcodeValue'],
                    'quantity': item['systemQuantity'],
                    'inventory_quantity': item['actualQuantity'],
                    'inventory_diff_quantity': item['difference'],
                    'uom_id': env['uom.uom'].search[('erp_uom_id', '=', item['uomId'])].id,
                    'stock_inventory_id': stock_inventory.id,
                }
                line = env['stock.inventory.line'].search([('erp_line_id', '=', item['lineId']), ('stock_inventory_id', '=', stock_inventory.id)], limit=1)
                if line:
                    line.write(item_val)
                else:
                    env['stock.inventory.line'].create(item_val)
            return stock_inventory
