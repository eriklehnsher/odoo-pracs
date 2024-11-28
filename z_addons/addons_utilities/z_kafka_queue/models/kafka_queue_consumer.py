# -*- coding: utf-8 -*-

import json
import logging
import threading
import time
from datetime import datetime

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.error import KafkaException, KafkaError
from odoo import models, fields, api, SUPERUSER_ID
from odoo import registry as registry_get
from odoo.tools import config

_logger = logging.getLogger(__name__)


class KafkaQueue(models.Model):
    _name = 'kafka.queue.consumer'
    _description = 'Kafka Queue Consumer'
    _rec_name = 'topic'

    _sql_constraints = [
        ('unique_topic', 'UNIQUE(topic)', 'The topic must be unique.'),
    ]

    topic = fields.Char(string='Topic')
    active = fields.Boolean(string='Active', default=True)
    group_id = fields.Char(string='Group ID')
    host = fields.Char(string='Host')
    port = fields.Char(string='Port')
    offset = fields.Integer(string='Offset', default=0)
    limit = fields.Integer(string='Limit', default=100)
    last_offset_message = fields.Integer(string='Last Offset Message', default=0)

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

    # def thread_poll(self):
    #     threaded_calculation = threading.Thread(target=self._run_delayed_calculations,
    #                                             args=(thread_id, company_code, data_config))
    #     threaded_calculation.setDaemon(True)
    #     threaded_calculation.start()

    # def _run_delayed_calculations(self, thread_id, company_code, data_config):
    #     try:
    #         # time.sleep(3)
    #         with api.Environment.manage():
    #             try:
    #                 credentials = pika.PlainCredentials(username=data_config['user'], password=data_config['password'])
    #                 connection = pika.BlockingConnection(
    #                     pika.ConnectionParameters(host=data_config['host'], port=data_config['port'],
    #                                               credentials=credentials, heartbeat=600),
    #                 )
    #                 channel = connection.channel()
    #
    #                 def callback(ch, method, properties, body):
    #                     try:
    #                         _logger.warning(" [x] Received " + str(body))
    #                         res = self._send_to_webhook(data_config, json.loads(body)['headers'],
    #                                                     json.loads(body)['request_body'],
    #                                                     json.loads(body)['id'], json.loads(body)['reseller_name'])
    #                     except Exception as e:
    #                         _logger.error(f"Error in callback: {e}")
    #
    #                 channel.queue_declare(queue=company_code, durable=True)
    #                 channel.basic_consume(company_code,
    #                                       callback,
    #                                       auto_ack=True)
    #
    #                 _logger.warning(' [*] Waiting for messages:')
    #                 channel.start_consuming()
    #             except Exception as e:
    #                 _logger.error(f"Unable connection!!!!!!!!: {e}")
    #     except Exception as e:
    #         _logger.error(f"Error in thread: {e}")
    #     finally:
    #         self._running_threads[thread_id] = False
    #     return {}

    # def _start_thread(self, thread_id, company_code, data_config):
    #     threaded_calculation = threading.Thread(target=self._run_delayed_calculations,
    #                                             args=(topic))
    #     threaded_calculation.setDaemon(True)
    #     threaded_calculation.start()
    #     self._running_threads[thread_id] = True

    # def receive_response(self, cancel_backorder=False):
    #     company_id = self.env['res.company'].search([], limit=1)
    #     company_code = company_id.company_code
    #     data_config = self.get_info_config_rabbitmq()
    #     if data_config:
    #         if not self._is_thread_running(company_id.id):
    #             self._start_thread(company_id.id, company_code, data_config)

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
            # offset = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_last_offset')
            # consumer.assign([TopicPartition(topic, 0, int(offset))])
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
                    _logger.warning('Message received: %s \n Offset: %s \n Partition: %s' % (
                        json.loads(message.value()), message.offset(), message.partition()))
                    try:
                        data = json.loads(message.value())
                        # Đồng bộ dữ liệu đơn vị (model == erp.res.company)
                        if data['objName'].lower() == 'organization':
                            odoo_message_consumption = self.action_sync_erp_res_company(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        # Đồng bộ dữ liệu kho, vị trí
                        elif data['objName'].lower() == 'warehouse':
                            odoo_message_consumption = self.action_sync_erp_warehouse_location(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        # Đồng bộ dữ liệu khách hàng, nhà cung cấp, nhân viên
                        elif data['objName'].lower() == 'bpartner':
                            odoo_message_consumption = self.action_sync_erp_res_partner(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        # Đồng bộ dữ liệu user đăng nhập
                        elif data['objName'].lower() == 'user':
                            odoo_message_consumption = self.action_sync_res_users(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        # Đồng bộ dữ liệu đơn vị tính
                        elif data['objName'].lower() == 'uom':
                            odoo_message_consumption = self.action_sync_uom_uom(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        elif data['objName'].lower() == 'currency':
                            odoo_message_consumption = self.action_sync_erp_res_currency(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        elif data['objName'].lower() == 'product':
                            odoo_message_consumption = self.action_sync_product_template(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        elif data['objName'].lower() == 'barcode':
                            odoo_message_consumption = self.action_sync_barcode(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        elif data['objName'].lower() == 'attributeset':
                            odoo_message_consumption = self.action_sync_attribute_set(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                        elif data['objName'].lower() == 'attributevalue':
                            odoo_message_consumption = self.action_sync_product_attribute_value(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)
                        elif data['objName'].lower() == 'documenttype':
                            odoo_message_consumption = self.action_sync_document_type(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)
                        elif data['objName'].lower() == 'department':
                            odoo_message_consumption = self.action_sync_department(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)
                        elif data['objName'].lower() == 'brandaccount':
                            odoo_message_consumption = self.action_sync_product_brand(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)
                        elif data['objName'].lower() == 'tax':
                            odoo_message_consumption = self.action_sync_tax(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)
                        elif data['objName'].lower() == 'charge':
                            odoo_message_consumption = self.action_sync_charge(data)
                            _logger.warning(
                                'Odoo message consumption success with object: %s' % odoo_message_consumption)

                    except Exception as ex:
                        self.env['kafka.queue.error.logging'].create({
                            'message': data,
                            'error': str(ex),
                            'offset': message.offset(),
                            'partition': message.partition(),
                            'topic': message.topic(),
                        })
                        self._cr.commit()
                        _logger.error('Error sync master data: %s' % ex)
                        continue
        except Exception as ex:
            _logger.error('Error running consuming kafka queue: %s' % ex)
        finally:
            self._running_threads[topic] = False
        return {}

    def start_consumer(self):
        try:
            consumer_conf = {
                'bootstrap.servers': '14.160.32.8:9093',
                'group.id': 'stock_transfer_group',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            consumer = Consumer(consumer_conf)
            consumer.assign([TopicPartition('wms.to.erp.transfer.response', 0, 1)])
            while True:
                message = consumer.poll(timeout=5)
                if message is None:
                    continue
                data = json.loads(message.value())
                print(json.loads(message.value()), message.offset())
            pass
        except KafkaException as e:
            _logger.error('Error start consumer: %s' % e)

    def action_sync_erp_res_company(self, data):
        clientInfo = data['objData']['clientInfo']
        orgInfo = data['objData']['orgInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_client_id': int(clientInfo['clientId']),
                'erp_client_name': clientInfo['clientName'],
                'erp_org_id': int(orgInfo['orgId']),
                'erp_org_code': orgInfo['orgCode'],
                'erp_org_name': orgInfo['orgName'],
                'erp_org_address': orgInfo['orgAddress'],
                'erp_tax_code': orgInfo['taxCode'],
                'erp_phone': orgInfo['phone'],
                'erp_fax': orgInfo['fax'],
                'erp_email': orgInfo['email'],
                'erp_is_active': orgInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(orgInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(orgInfo['updatedAt'] / 1000),
            }
            company = env['erp.res.company'].search([('erp_org_id', '=', int(orgInfo['orgId']))], limit=1)
            if company:
                company.write(val)
            else:
                company = env['erp.res.company'].create(val)
            return company

    def action_sync_erp_warehouse_location(self, data):
        clientInfo = data['objData']['clientInfo']
        warehouseInfo = data['objData']['warehouseInfo']
        locatorInfo = warehouseInfo['locatorInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            erp_res_company = env['erp.res.company'].search(
                [('erp_org_id', '=', int(warehouseInfo['orgInfo']['orgId']))], limit=1)
            val_stock_warehouse = {
                'erp_client_id': int(clientInfo['clientId']),
                'erp_org_id': int(warehouseInfo['orgInfo']['orgId']),
                'erp_warehouse_id': warehouseInfo['warehouseId'],
                'code': warehouseInfo['warehouseCode'],
                'name': warehouseInfo['warehouseName'],
                'erp_location_id': int(warehouseInfo['locationId']),
                'active': warehouseInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(warehouseInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(warehouseInfo['updatedAt'] / 1000),
                'erp_res_company_id': erp_res_company.id if erp_res_company else None,
            }
            warehouse_obj = env['stock.warehouse'].search([
                ('erp_warehouse_id', '=', warehouseInfo['warehouseId']),
                ('active', 'in', (True, False))
            ], limit=1)
            if warehouse_obj:
                location_active = warehouse_obj.lot_stock_id.active
                if not warehouseInfo['isActive']:
                    warehouse_obj.active = False
                    warehouse_obj.lot_stock_id.active = location_active
                elif warehouseInfo['isActive']:
                    warehouse_obj.active = True
                    warehouse_obj.lot_stock_id.active = location_active

                warehouse_obj.write({
                    'erp_client_id': int(clientInfo['clientId']),
                    'erp_org_id': int(warehouseInfo['orgInfo']['orgId']),
                    # 'erp_warehouse_id': warehouseInfo['warehouseId'],
                    # 'code': warehouseInfo['warehouseCode'],
                    'name': warehouseInfo['warehouseName'],
                    'erp_location_id': int(warehouseInfo['locationId']),
                    # 'active': warehouseInfo['isActive'],
                    'erp_created_at': datetime.fromtimestamp(warehouseInfo['createdAt'] / 1000),
                    'erp_updated_at': datetime.fromtimestamp(warehouseInfo['updatedAt'] / 1000),
                    'erp_res_company_id': erp_res_company.id if erp_res_company else None,
                })
            else:
                warehouse_obj = env['stock.warehouse'].create(val_stock_warehouse)
            for item in locatorInfo:
                val_stock_location = {
                    'erp_locator_id': item['locatorId'],
                    'name': item['locatorCode'],
                    # 'active': item['isActive'],
                    'erp_is_default': item['isDefault'],
                }
                warehouse_obj.lot_stock_id.write(val_stock_location)
                if not item['isActive']:
                    env.cr.execute("""
                        UPDATE stock_location SET active = FALSE WHERE id = %s
                    """ % warehouse_obj.lot_stock_id.id)
                elif item['isActive']:
                    env.cr.execute("""
                        UPDATE stock_location SET active = TRUE WHERE id = %s
                    """ % warehouse_obj.lot_stock_id.id)
            return warehouse_obj

    def action_sync_erp_res_partner(self, data):
        clientInfo = data['objData']['clientInfo']
        bpartnerInfo = data['objData']['bpartnerInfo']
        orgInfo = bpartnerInfo['orgInfo']
        bpartnerLocationInfo = bpartnerInfo['bpartnerLocationInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            partner = self.env['res.partner'].search([('erp_bpartner_id', '=', bpartnerInfo['bpartnerId'])])
            if partner:
                return partner
            child_ids = self._create_partner_child_ids(bpartnerLocationInfo)
            erp_res_company = env['erp.res.company'].search([('erp_client_id', '=', clientInfo['clientId'])], limit=1)
            partner = self._create_partner(bpartnerInfo, erp_res_company, orgInfo, child_ids)
            return partner

    def action_sync_res_users(self, data):
        clientInfo = data['objData']['clientInfo']
        userInfo = data['objData']['userInfo']
        orgInfo = userInfo['orgInfo']
        bpartnerInfo = userInfo['bpartnerInfo']
        bpartnerLocationInfo = bpartnerInfo['bpartnerLocationInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            erp_res_company = env['erp.res.company'].search([('erp_client_id', '=', clientInfo['clientId'])], limit=1)
            child_ids = None
            partner = None
            for item in bpartnerInfo['bpartnerLocationInfo']:
                res_partner = env['res.partner'].search([('erp_bpartner_location_id', '=', item['bpartnerLocationId'])],
                                                        limit=1)
                if not res_partner:
                    # Create res_partner with type == 'other'
                    child_ids = self._create_partner_child_ids(bpartnerLocationInfo)

            res_partner = env['res.partner'].search([('erp_bpartner_id', '=', bpartnerInfo['bpartnerId'])], limit=1)
            if not res_partner:
                # Create res_partner
                val_bpartner = {
                    'name': bpartnerInfo['bpartnerName'],
                    'ref': bpartnerInfo['bpartnerCode'],
                    'street': orgInfo['orgAddress'],
                    'vat': orgInfo['taxCode'],
                    'phone': orgInfo['phone'],
                    'email': orgInfo['email'],
                    'active': orgInfo['isActive'],
                    'erp_fax': orgInfo['fax'],
                    'erp_bpartner_id': bpartnerInfo['bpartnerId'],
                    'erp_client_id': erp_res_company.id if erp_res_company else None,
                    'erp_org_id': orgInfo['orgId'],
                    'erp_is_customer': bpartnerInfo['isCustomer'],
                    'erp_is_vendor': bpartnerInfo['isVendor'],
                    'erp_is_employee': bpartnerInfo['isEmployee'],
                    'erp_is_sales_rep': bpartnerInfo['isSalesRep'],
                    'erp_created_at': datetime.fromtimestamp(bpartnerInfo['createdAt'] / 1000),
                    'erp_updated_at': datetime.fromtimestamp(bpartnerInfo['updatedAt'] / 1000),
                }
                if child_ids:
                    val_bpartner.update({
                        'child_ids': [(6, 0, child_ids.ids)]
                    })
                partner = env['res.partner'].create(val_bpartner)
                # partner = self._create_partner(bpartnerInfo, erp_res_company, orgInfo, child_ids)
            val_res_user = {
                'login': userInfo['userName'],
                'erp_user_code': userInfo['userCode'],
                'erp_user_id': userInfo['userId'],
                'active': userInfo['isActive'],
                'partner_id': res_partner.id if res_partner else partner.id,
                'erp_created_at': datetime.fromtimestamp(userInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(userInfo['updatedAt'] / 1000),
            }
            res_users = env['res.users'].search([('erp_user_id', '=', userInfo['userId'])], limit=1)
            if res_users:
                res_users.write(val_res_user)
            else:
                res_users = env['res.users'].create(val_res_user)
            return res_users

    def _create_partner_child_ids(self, bpartnerLocationInfo):
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            vals_child_ids = {}
            for item in bpartnerLocationInfo:
                val = {
                    'name': item['bpartnerLocationName'],
                    'erp_bpartner_location_id': item['bpartnerLocationId'],
                    'active': item['isActive'],
                    'phone': item['phone'],
                    'email': item['email'],
                    'erp_location_id': item['locationId'],
                    'street': item['locationAddress'],
                    'erp_created_at': datetime.fromtimestamp(item['createdAt'] / 1000),
                    'erp_updated_at': datetime.fromtimestamp(item['updatedAt'] / 1000),
                    'type': 'other',  # Mặc định là địa chỉ khác
                }
                vals_child_ids.update(val)
            child_ids = env['res.partner'].create(vals_child_ids)
            return child_ids

    def _create_partner(self, bpartnerInfo, erp_res_company, orgInfo, child_ids=None):
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val_bpartner = {
                'name': bpartnerInfo['bpartnerName'],
                'ref': bpartnerInfo['bpartnerCode'],
                'street': orgInfo['orgAddress'],
                'vat': orgInfo['taxCode'],
                'phone': orgInfo['phone'],
                'email': orgInfo['email'],
                'active': orgInfo['isActive'],
                'erp_fax': orgInfo['fax'],
                'erp_bpartner_id': bpartnerInfo['bpartnerId'],
                'erp_client_id': erp_res_company.id if erp_res_company else None,
                'erp_org_id': orgInfo['orgId'],
                'erp_is_customer': bpartnerInfo['isCustomer'],
                'erp_is_vendor': bpartnerInfo['isVendor'],
                'erp_is_employee': bpartnerInfo['isEmployee'],
                'erp_is_sales_rep': bpartnerInfo['isSalesRep'],
                'erp_created_at': datetime.fromtimestamp(bpartnerInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(bpartnerInfo['updatedAt'] / 1000),
            }
            if child_ids:
                val_bpartner.update({
                    'child_ids': [(6, 0, child_ids.ids)]
                })
            partner = env['res.partner'].create(val_bpartner)
            return partner

    def action_sync_uom_uom(self, data):
        uomInfo = data['objData']['uomInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            # Tạo trước uom_category do không có dữ liệu uom_type
            val_categ_uom = {
                'name': uomInfo['uomName'],
            }
            uom_category = env['uom.category'].search([('name', '=', uomInfo['uomName'])], limit=1)
            if not uom_category:
                uom_category = env['uom.category'].create(val_categ_uom)
            val = {
                'category_id': uom_category.id,
                'erp_uom_id': uomInfo['uomId'],
                'erp_uom_symbol': uomInfo['uomSymbol'],
                'name': uomInfo['uomName'],
                'description': uomInfo['uomDescription'],
                'active': uomInfo['isActive'],
                'erp_uom_trl_info': uomInfo['uomTrlInfo'],
            }
            uom_uom = env['uom.uom'].search([('erp_uom_id', '=', uomInfo['uomId'])], limit=1)
            if uom_uom:
                uom_uom.write(val)
            else:
                uom_uom = env['uom.uom'].create(val)
            return uom_uom

    def action_sync_erp_res_currency(self, data):
        currencyInfo = data['objData']['currencyInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_currency_id': currencyInfo['currencyId'],
                'code': currencyInfo['ISOCode'],
                'symbol': currencyInfo['currencySymbol'],
                'description': currencyInfo['currencyDescription'],
                'active': currencyInfo['isActive'],
            }
            res = env['erp.res.currency'].search([('erp_currency_id', '=', currencyInfo['currencyId'])], limit=1)
            if res:
                res.write(val)
            else:
                res = env['erp.res.currency'].create(val)
            return res

    def action_sync_product_template(self, data):
        clientInfo = data['objData']['clientInfo']
        productInfo = data['objData']['productInfo']
        orgInfo = productInfo['orgInfo']
        brandInfo = productInfo['brandInfo']
        genderInfo = productInfo['genderInfo']
        productGroupInfo = productInfo['productGroupInfo']
        productSubGroupInfo = productInfo['productSubGroupInfo']
        productLineInfo = productInfo['productLineInfo']
        uomInfo = productInfo['uomInfo']
        taxInfo = productInfo['taxInfo']
        attributeSetInfo = productInfo['attributeSetInfo']
        supplierInfo = productInfo['supplierInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            categ = None
            sub_categ = None
            # Tạo mới product_category nếu chưa có
            if productGroupInfo['productGroupId'] != 0:
                categ = env['product.category'].search([('erp_categ_id', '=', productGroupInfo['productGroupId'])])
                if not categ:
                    categ = env['product.category'].create({
                        'name': productGroupInfo['productGroupName'],
                        'erp_code': productGroupInfo['productGroupCode'],
                        'erp_categ_id': productGroupInfo['productGroupId'],
                    })
            if productSubGroupInfo['productSubGroupId'] != 0:
                sub_categ = env['product.category'].search(
                    [('erp_categ_id', '=', productSubGroupInfo['productSubGroupId'])])
                if not sub_categ:
                    sub_categ = env['product.category'].create({
                        'name': productSubGroupInfo['productSubGroupName'],
                        'erp_code': productSubGroupInfo['productSubGroupCode'],
                        'erp_categ_id': productSubGroupInfo['productSubGroupId'],
                    })
            uom_uom = env['uom.uom'].search([('erp_uom_id', '=', uomInfo['uomId'])])
            tax = env['erp.account.tax'].search([('erp_tax_id', '=', taxInfo['taxId'])], limit=1)
            brand_val = {
                'erp_id': brandInfo['brandId'],
                'code': brandInfo['brandCode'],
                'name': brandInfo['brandName']
            }
            product_brand = env['erp.brand.segment'].search([('erp_id', '=', brandInfo['brandId'])], limit=1)
            if product_brand:
                product_brand.write(brand_val)
            else:
                product_brand = env['erp.brand.segment'].create(brand_val)
            product_gender = env['product.gender'].search([('erp_product_gender_id', '=', genderInfo['genderId'])], limit=1)
            gender_val = {
                'erp_product_gender_id': genderInfo['genderId'],
                'code': genderInfo['genderCode'],
                'name': genderInfo['genderName'],
            }
            if product_gender:
                product_gender.write(gender_val)
            else:
                product_gender = env['product.gender'].create(gender_val)
            product_line_val = {
                'erp_product_line_id': productLineInfo['productLineId'],
                'line_code': productLineInfo['productLineCode'],
                'line_name': productLineInfo['productLineName'],
            }
            product_line = env['product.line'].search([('erp_product_line_id', '=', productLineInfo['productLineId'])], limit=1)
            if product_line:
                product_line.write(product_line_val)
            else:
                product_line = env['product.line'].create(product_line_val)
            erp_product_attribite_set = env['erp.product.attribute.set'].search(
                [('erp_product_attribute_set_id', '=', attributeSetInfo['attributeSetId'])])
            val = {
                'erp_client_id': clientInfo['clientId'],
                'erp_org_id': orgInfo['orgId'],
                'erp_product_template_id': productInfo['productId'],
                'default_code': productInfo['productCode'],
                'name': productInfo['productName'],
                'erp_product_fullname': productInfo['productFullName'],
                'erp_product_name_eng': productInfo['productNameEng'],
                'active': productInfo['isActive'],
                'erp_is_stocked': productInfo['isStocked'],
                'purchase_ok': productInfo['isPurchased'],
                'sale_ok': productInfo['isSold'],
                'erp_is_discontinued': productInfo['isDiscontinued'],
                'brand_segment_id': product_brand.id if product_brand else None,
                'product_gender_id': product_gender.id if product_gender else None,
                'product_line_id': product_line.id if product_line else None,
                'categ_id': categ.id if categ else None,
                'sub_categ_id': sub_categ.id if sub_categ else None,
                'uom_id': uom_uom.id if uom_uom else None,
                'uom_po_id': uom_uom.id if uom_uom else None,
                'erp_tax_id': tax.id if tax else None,
                'erp_product_attribute_set_id': erp_product_attribite_set.id if erp_product_attribite_set else None,
                'erp_verdor_product_no': supplierInfo['verdorProductNo'],
                'erp_vendor_code': supplierInfo['vendorCode'],
                'erp_verdor_cate1': supplierInfo['verdorCate1'],
                'erp_vendor_cate2': supplierInfo['vendorCate2'],
                'erp_vendor_cate3': supplierInfo['vendorCate3'],
                'erp_dcs_code': supplierInfo['DCSCode'],
                'erp_created_at': datetime.fromtimestamp(productInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(productInfo['updatedAt'] / 1000),
                'detailed_type': 'product',
                'tracking': 'none',
            }
            product_template = env['product.template'].search(
                [('erp_product_template_id', '=', productInfo['productId']), ('active', 'in', (True, False))])
            if product_template:
                if not productInfo['isActive']:
                    product_template.active = False
                elif productInfo['isActive']:
                    product_template.active = True
                else:
                    pass
                product_template.write(
                    {
                        'erp_client_id': clientInfo['clientId'],
                        'erp_org_id': orgInfo['orgId'],
                        # 'erp_product_template_id': productInfo['productId'],
                        # 'erp_default_code': productInfo['productCode'],
                        'name': productInfo['productName'],
                        'erp_product_fullname': productInfo['productFullName'],
                        'erp_product_name_eng': productInfo['productNameEng'],
                        # 'active': productInfo['isActive'],
                        'erp_is_stocked': productInfo['isStocked'],
                        'purchase_ok': productInfo['isPurchased'],
                        'sale_ok': productInfo['isSold'],
                        'erp_is_discontinued': productInfo['isDiscontinued'],
                        'product_brand_id': product_brand.id if product_brand else None,
                        'product_gender_id': product_gender.id if product_gender else None,
                        'product_line_id': product_line.id if product_line else None,
                        'categ_id': categ.id if categ else None,
                        'sub_categ_id': sub_categ.id if sub_categ else None,
                        'uom_id': uom_uom.id if uom_uom else None,
                        'uom_po_id': uom_uom.id if uom_uom else None,
                        'erp_tax_id': tax.id if tax else None,
                        'erp_product_attribute_set_id': erp_product_attribite_set.id if erp_product_attribite_set else None,
                        'erp_verdor_product_no': supplierInfo['verdorProductNo'],
                        'erp_vendor_code': supplierInfo['vendorCode'],
                        'erp_verdor_cate1': supplierInfo['verdorCate1'],
                        'erp_vendor_cate2': supplierInfo['vendorCate2'],
                        'erp_vendor_cate3': supplierInfo['vendorCate3'],
                        'erp_dcs_code': supplierInfo['DCSCode'],
                        'erp_created_at': datetime.fromtimestamp(productInfo['createdAt'] / 1000),
                        'erp_updated_at': datetime.fromtimestamp(productInfo['updatedAt'] / 1000),
                        'detailed_type': 'product',
                        'tracking': 'none',
                    }
                )
            else:
                product_template = env['product.template'].create(val)
            return product_template

    def action_sync_barcode(self, data):
        clientInfo = data['objData']['clientInfo']
        barcodeInfo = data['objData']['barcodeInfo']
        orgInfo = barcodeInfo['orgInfo']
        attributeInfo = barcodeInfo['attributeInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            barcode_line_val = []
            for item in attributeInfo:
                product_attribute = env['product.attribute'].search(
                    [('erp_product_attribute_id', '=', item['attributeId'])])
                product_attribute_value = None
                if item['attributeValueId']:
                    product_attribute_value = env['product.attribute.value'].search(
                        [('erp_product_attribute_value_id', '=', item['attributeValueId'])])
                barcode_line_val.append(
                    (0, 0, {
                        'product_attribute_id': product_attribute.id if product_attribute else None,
                        'product_attribute_value_id': product_attribute_value.id if product_attribute_value else None,
                        'erp_product_attribute_id': item['attributeId'],
                        'erp_product_attribute_value_id': item['attributeValueId'],
                    })
                )

            erp_barcode_val = {
                'erp_client_id': clientInfo['clientId'],
                'erp_org_id': orgInfo['orgId'],
                'erp_barcode_id': barcodeInfo['barcodeId'],
                'erp_barcode_value': barcodeInfo['barcodeValue'],
                'erp_serial': barcodeInfo['serial'],
                'erp_lot': barcodeInfo['lot'],
                'erp_ean_code': barcodeInfo['EANCode'],
                'active': barcodeInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(barcodeInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(barcodeInfo['updatedAt'] / 1000),
                'barcode_line_ids': barcode_line_val
            }
            erp_barcode_record = env['erp.barcode'].search([('erp_barcode_id', '=', barcodeInfo['barcodeId'])])
            if erp_barcode_record:
                erp_barcode_record.barcode_line_ids.unlink()
                erp_barcode_record.write(erp_barcode_val)
            else:
                erp_barcode_record = env['erp.barcode'].create(erp_barcode_val)
                # Update vào bảng thuộc tính biến thể: Barcode
                product_attribute = env['product.attribute'].search([('name', '=', 'Barcode')])
                product_attribute_value = env['product.attribute.value'].create({
                    'attribute_id': product_attribute.id,
                    'name': erp_barcode_val['erp_barcode_value'],
                    'value': erp_barcode_val['erp_barcode_value'],
                })
            return erp_barcode_record

    def action_sync_attribute_set(self, data):
        attributeSetInfo = data['objData']['attributeSetInfo']
        attributeUseInfo = attributeSetInfo['attributeUseInfo']
        product_attribute_ids = []
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            for item in attributeUseInfo:
                product_attribute = env['product.attribute'].search(
                    [('erp_product_attribute_id', '=', item['attributeId'])])
                if product_attribute:
                    product_attribute_ids.append(product_attribute.id)
                else:
                    # Tạo mới trước product.attribute
                    val_prod_attr = {
                        'erp_product_attribute_id': item['attributeId'],
                        'name': item['attributeCode'],
                        'create_variant': 'always',  # Auto tạo biến thể sản phẩm
                        'erp_is_active': item['isActive'],
                        'erp_created_at': datetime.fromtimestamp(item['createdAt'] / 1000),
                        'erp_updated_at': datetime.fromtimestamp(item['updatedAt'] / 1000),
                    }
                    new_prod_attr = env['product.attribute'].create(val_prod_attr)
                    product_attribute_ids.append(new_prod_attr.id)
            val = {
                'erp_product_attribute_set_id': attributeSetInfo['attributeSetId'],
                'name': attributeSetInfo['attributeSetName'],
                'active': attributeSetInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(item['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(item['updatedAt'] / 1000),
                'product_attribute_ids': [(6, 0, product_attribute_ids)],
            }
            attribute_set = env['erp.product.attribute.set'].search(
                [('erp_product_attribute_set_id', '=', attributeSetInfo['attributeSetId'])], limit=1)
            if attribute_set:
                attribute_set.write(val)
            else:
                attribute_set = env['erp.product.attribute.set'].create(val)
            return attribute_set

    def action_sync_product_attribute_value(self, data):
        attributeValueInfo = data['objData']['attributeValueInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            product_attribute = env['product.attribute'].search(
                [('erp_product_attribute_id', '=', attributeValueInfo['attributeId'])])
            val = {
                'erp_product_attribute_value_id': attributeValueInfo['attributeValueId'],
                'value': attributeValueInfo['value'],
                'name': attributeValueInfo['name'],
                'erp_created_at': datetime.fromtimestamp(attributeValueInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(attributeValueInfo['updatedAt'] / 1000),
                'message_id': data['messageId'],
                'active': attributeValueInfo['isActive'],
                'attribute_id': product_attribute.id if product_attribute else None,
            }
            product_attribute_value = env['product.attribute.value'].search(
                [('erp_product_attribute_value_id', '=', attributeValueInfo['attributeValueId'])])
            if product_attribute_value:
                product_attribute_value.write(val)
            else:
                product_attribute_value = env['product.attribute.value'].create(val)
            return product_attribute_value

    def action_sync_document_type(self, data):
        DocumentTypeInfo = data['objData']['documentTypeInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_document_type_id': DocumentTypeInfo['documentTypeId'],
                'name': DocumentTypeInfo['documentTypeName'],
                'active': DocumentTypeInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(DocumentTypeInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(DocumentTypeInfo['updatedAt'] / 1000),
            }
            document_type = env['stock.document.type'].search(
                [('erp_document_type_id', '=', DocumentTypeInfo['documentTypeId'])], limit=1)
            if document_type:
                document_type.write(val)
            else:
                document_type = env['stock.document.type'].create(val)
            return document_type

    def action_sync_department(self, data):
        DepartmentInfo = data['objData']['departmentInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_hr_department_id': DepartmentInfo['departmentId'],
                'name': DepartmentInfo['departmentName'],
                'code': DepartmentInfo['departmentValue'],
                'active': DepartmentInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(DepartmentInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(DepartmentInfo['updatedAt'] / 1000),
            }
            department = env['erp.hr.department'].search(
                [('erp_hr_department_id', '=', DepartmentInfo['departmentId'])], limit=1)
            if department:
                department.write(val)
            else:
                department = env['erp.hr.department'].create(val)
            return department

    def action_sync_product_brand(self, data):
        ProductBrandInfo = data['objData']['brandAccountInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_product_brand_id': ProductBrandInfo['brandAccountId'],
                'brand_name': ProductBrandInfo['brandAccountName'],
                'brand_code': ProductBrandInfo['brandAccountValue'],
                'active': ProductBrandInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(ProductBrandInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(ProductBrandInfo['updatedAt'] / 1000),
            }
            brand = env['product.brand'].search([('erp_product_brand_id', '=', ProductBrandInfo['brandAccountId'])],
                                                limit=1)
            if brand:
                brand.write(val)
            else:
                brand = env['product.brand'].create(val)
            return brand

    def action_sync_tax(self, data):
        TaxInfo = data['objData']['taxInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_tax_id': TaxInfo['taxId'],
                'tax_name': TaxInfo['taxName'],
                'tax_amount': TaxInfo['taxRate'],
                'active': TaxInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(TaxInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(TaxInfo['updatedAt'] / 1000),
            }
            tax = env['erp.account.tax'].search([('erp_tax_id', '=', TaxInfo['taxId'])], limit=1)
            if tax:
                tax.write(val)
            else:
                tax = env['erp.account.tax'].create(val)
            return tax

    def action_sync_charge(self, data):
        ChargeInfo = data['objData']['chargeInfo']
        with registry_get(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            val = {
                'erp_charge_id': ChargeInfo['chargeId'],
                'name': ChargeInfo['chargeName'],
                'active': ChargeInfo['isActive'],
                'erp_created_at': datetime.fromtimestamp(ChargeInfo['createdAt'] / 1000),
                'erp_updated_at': datetime.fromtimestamp(ChargeInfo['updatedAt'] / 1000),
            }
            charge = env['erp.charge'].search([('erp_charge_id', '=', ChargeInfo['chargeId'])], limit=1)
            if charge:
                charge.write(val)
            else:
                charge = env['erp.charge'].create(val)
            return charge
