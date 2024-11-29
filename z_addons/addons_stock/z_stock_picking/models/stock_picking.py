# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from confluent_kafka import Producer, KafkaError, KafkaException
import uuid
import json
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from odoo.modules import get_module_path
from datetime import datetime

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    warehouse_id = fields.Many2one('stock.warehouse', string='Source Warehouse')
    warehouse_dest_id = fields.Many2one('stock.warehouse', string='Destination Warehouse')
    document_type_id = fields.Many2one('stock.document.type', string='Document Type')
    pick_location_in = fields.Boolean(string='Pick Location In', default=False, copy=False)
    is_pick_location_out = fields.Boolean(string='Pick Location Out', default=False, copy=False)
    is_pick_location_in = fields.Boolean(string='Pick Location In', default=False, copy=False)
    z_transfer_type = fields.Selection([
        ('wms_ho_to_shop', 'WMS - Chuyển kho từ HO ra cửa hàng'),  # WMS-22
        ('wms_ho_to_ho', 'WMS - Chuyển kho giữa 2 HO'),  # WMS-25 + # WMS-26
        ('wms_transfer_location', 'WMS - Điều chuyển vị trí'),
    ], string='Loại điều chuyển')

    z_transfer_type_sync = fields.Selection([
        ('erp_internal_export', 'ERP - Xuất dùng nội bộ'),  # WMS-20
        ('erp_ho_to_shop', 'ERP - Chuyển kho từ HO ra cửa hàng'),  # WMS-23
        ('erp_shop_to_ho', 'ERP - Chuyển kho từ cửa hàng về HO'),  # WMS-24
        ('erp_internal_sale', 'ERP - Bán nội bộ giữa 2 HO'),  # WMS-27
        ('erp_internal_purchase', 'ERP - Mua nội bộ giữa 2 HO'),  # WMS-28
        ('erp_foreign_trade', 'ERP - Nhập hàng nhập khẩu'),  # WMS-21
    ], string='Type Transfer ERP')
    erp_so_internal_id = fields.Integer()
    erp_so_internal_no = fields.Char()
    po_internal_order_info = fields.Json('Thông tin chứng từ đơn hàng mua nội bộ')
    po_internal_invoice_info = fields.Json('Thông tin chứng từ hóa đơn nhập nội bộ')
    so_internal_order_info = fields.Json('Thông tin chứng từ đơn hàng bán nội bộ')
    so_internal_invoice_info = fields.Json('Thông tin chứng từ hóa đơn xuất nội bộ')
    is_confirm_internal_export = fields.Char('Đã xác nhận giao dịch chuyển kho giữa 2 HO', default=False)
    picking_type_code = fields.Selection(
        related='picking_type_id.code',
        readonly=True)
    x_warehouse_dest_id_domain_ids = fields.Many2many('stock.warehouse', 'warehouse_dest_rel')
    x_warehouse_id_domain_ids = fields.Many2many('stock.warehouse', 'warehouse_rel')
    x_picking_type_code = fields.Selection([
        ('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer')
    ], store=True)
    is_invisible = fields.Boolean(default=False)

    # xác nhận giao dịch chuyển kho giữa 2 HO khác miền (xuất)
    def action_confirm_internal_export(self):
        if self.z_transfer_type == 'wms_ho_to_ho':
            host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
            topic = 'wms.to.erp.internal.request'
            list_msg = self._prepare_wms_ho_to_ho_queue_msg()
            for item in list_msg:
                conf = {
                    'bootstrap.servers': '%s' % host,
                }
                producer = Producer(conf)
                producer.produce(topic, json.dumps(item).encode('utf-8'))
                producer.flush()
                self.is_confirm_internal_export = True

    # def action_confirm(self):
    #     return super(StockPicking, self).action_confirm()
    #
    #     if self.z_transfer_type == 'wms_ho_to_ho':
    #         host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
    #         topic = 'wms.to.erp.internal.request'
    #         list_msg = self._prepare_wms_ho_receipt_from_ho_queue_msg()
    #         conf = {
    #             'bootstrap.servers': '%s' % host,
    #         }
    #         producer = Producer(conf)
    #         producer.produce(topic, json.dumps(list_msg).encode('utf-8'))
    #         producer.flush()
    #     return res

    # WMS-22
    def _prepare_wms_ho_to_shop_queue_msg(self):
        self.ensure_one()
        list_msg = []
        sql = """
            SELECT create_date FROM stock_picking WHERE id = %s;  
        """ % self.id
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        soup = BeautifulSoup(self.note) if self.note else None
        text_note = soup.get_text() if soup else ''
        for i, item in enumerate(self.move_ids_without_package):
            barcode = self.env['erp.barcode'].search([('erp_barcode_value', '=', item.product_id.barcode)])
            msg = {
                'messageId': self.env['stock.picking']._generate_queue_message_id(),
                'objName': 'wmsToErpTransferRequest',
                'actionType': 'create',
                'objData': {
                    'metaData': {
                        'sequenceId': i + 1,
                        'totalLines': len(self.move_ids_without_package),
                    },
                    'requestId': self.name,
                    'fromSource': {
                        'source': 'WMS',
                        'clientId': 1000001,
                    },
                    'sourceWarehouse': {
                        'orgId': self.warehouse_id.erp_org_id,
                        'warehouseId': self.warehouse_id.erp_warehouse_id,
                        'warehouseCode': self.warehouse_id.code,
                        'warehouseName': self.warehouse_id.name,
                    },
                    'destinationWarehouse': {
                        'orgId': self.warehouse_dest_id.erp_org_id,
                        'warehouseId': self.warehouse_dest_id.erp_warehouse_id,
                        'warehouseCode': self.warehouse_dest_id.code,
                        'warehouseName': self.warehouse_dest_id.name,
                    },
                    'requestDate': int(self.create_date.timestamp() * 1000),
                    'requestedBy': {
                        'userId': self.create_uid.erp_user_id,
                        'userCode': self.create_uid.ref,
                        'userName': self.create_uid.login,
                    },
                    'items': {
                        'lineId': item.id,
                        'productId': item.product_id.product_tmpl_id.erp_product_template_id,
                        'productCode': item.product_id.product_tmpl_id.default_code,
                        'productName': item.product_id.product_tmpl_id.name,
                        'barcodeId': barcode.erp_barcode_id if barcode else None,
                        'barcodeValue': item.product_id.barcode,
                        'quantity': item.product_uom_qty,
                        'uomId': item.product_id.product_tmpl_id.uom_id.erp_uom_id,
                    },
                    'remarks': text_note,
                    'status': 'Approved'
                }
            }
            if self.department_id and self.department_id.erp_hr_department_id:
                msg['objData']['departmentInfo'] = {
                    'departmentId': self.department_id.erp_hr_department_id,
                    'departmentValue': self.department_id.code or '',
                    'departmentName': self.department_id.name or '',
                }
            list_msg.append(msg)
        return list_msg

    # WMS-25
    def _prepare_wms_ho_to_ho_queue_msg(self):
        self.ensure_one()
        list_msg = []
        soup = BeautifulSoup(self.note) if self.note else None
        text_note = soup.get_text() if soup else ''
        for i, item in enumerate(self.move_ids_without_package):
            erp_barcode = self.env['erp.barcode'].search([('erp_barcode_value', '=', item.product_id.barcode)], limit=1)
            msg = {
                "messageId": self.env['stock.picking']._generate_queue_message_id(),
                "objName": "wmsToErpSOInternalRequest",
                "actionType": "create",
                "objData": {
                    "metaData": {
                        "sequenceId": 1,
                        "totalLines": len(self.move_ids_without_package),
                    },
                    "requestId": self.name,
                    "fromSource": {
                        "source": "WMS",
                        "clientId": self.erp_client_id,
                    },
                    "sourceWarehouse": {
                        "orgId": self.location_id.warehouse_id.erp_org_id,
                        "warehouseId": self.warehouse_id.erp_warehouse_id,
                        "warehouseCode": self.warehouse_id.code,
                        "warehouseName": self.warehouse_id.name,
                    },
                    "destinationWarehouse": {
                        "orgId": self.location_dest_id.warehouse_id.erp_org_id,
                        "warehouseId": self.warehouse_dest_id.erp_warehouse_id,
                        "warehouseCode": self.warehouse_dest_id.code,
                        "warehouseName": self.warehouse_dest_id.name,
                    },
                    "requestDate": int(self.scheduled_date.timestamp()),
                    "requestedBy": {
                        "userId": self.create_uid.erp_user_id,
                        "userCode": self.create_uid.ref,
                        "userName": self.create_uid.login,
                    },
                    "items": {
                        "lineId": i,
                        "productId": item.product_id.product_tmpl_id.erp_product_template_id,
                        "productCode": item.product_id.product_tmpl_id.default_code,
                        "productName": item.product_id.product_tmpl_id.name,
                        "barcodeId": erp_barcode.erp_barcode_id if erp_barcode else '',
                        "barcodeValue": item.product_id.barcode,
                        "quantity": item.quantity_done if item.state == 'done' else item.product_uom_qty,
                        "uomId": item.product_id.product_tmpl_id.uom_id.erp_uom_id,
                    },
                    "remarks": text_note,
                    "status": "Approved"
                }
            }
            list_msg.append(msg)
        return list_msg

    # WMS-26
    def _prepare_wms_ho_receipt_from_ho_queue_msg(self):
        self.ensure_one()
        list_msg = []
        for i, item in enumerate(self.move_ids_without_package):
            erp_barcode = self.env['erp.barcode'].search([('erp_barcode_value', '=', item.product_id.barcode)], limit=1)
            msg = {
                "messageId": self.env['stock.picking']._generate_queue_message_id(),
                "objName": "wmsToErpReceiptInternalRequest",
                "actionType": "create",
                "objData": {
                    "metaData": {
                        "sequenceId": 1,
                        "totalLines": len(self.move_ids_without_package),
                    },
                    "requestId": self.name,
                    "fromSource": {
                        "source": "WMS",
                        "clientId": self.erp_client_id,
                    },
                    "sourceWarehouse": {
                        "orgId": self.location_id.warehouse_id.erp_org_id,
                        "warehouseId": self.location_id.warehouse_id.erp_warehouse_id,
                        "warehouseCode": self.location_id.warehouse_id.code,
                        "warehouseName": self.location_id.warehouse_id.name,
                    },
                    "destinationWarehouse": {
                        "orgId": self.location_dest_id.warehouse_id.erp_org_id,
                        "warehouseId": self.location_dest_id.warehouse_id.erp_warehouse_id,
                        "warehouseCode": self.location_dest_id.warehouse_id.code,
                        "warehouseName": self.location_dest_id.warehouse_id.name,
                    },
                    "requestDate": int(self.scheduled_date.timestamp()),
                    "requestedBy": {
                        "userId": self.create_uid.erp_user_id,
                        "userCode": self.create_uid.ref,
                        "userName": self.create_uid.login,
                    },
                    "items": {
                        "lineId": i,
                        "productId": item.product_id.product_tmpl_id.erp_product_template_id,
                        "productCode": item.product_id.product_tmpl_id.default_code,
                        "productName": item.product_id.product_tmpl_id.name,
                        "barcodeId": erp_barcode.erp_barcode_id if erp_barcode else '',
                        "barcodeValue": item.product_id.barcode,
                        "quantity": item.quantity_done if item.state == 'done' else item.product_uom_qty,
                        "uomId": item.product_id.product_tmpl_id.uom_id.erp_uom_id,
                    },
                    "poInternalOrderInfo": self.po_internal_order_info,
                    "remarks": "Tạo mới lệnh",
                    "status": "Approved"
                }
            }
            list_msg.append(msg)
        return list_msg

    # WMS-31
    def _prepare_validate_transfer_from_wms_queue_msg(self):
        self.ensure_one()
        msg = {
            "messageId": self.env['stock.picking']._generate_queue_message_id(),
            "objName": "wmsToErpTransferRequest",
            "actionType": "confirm",
            "objData": {
                "fromSource": {
                    "source": "WMS",
                    "clientId": self.erp_client_id
                },
                "status": "Complete",
                "movementInfo": {
                    "orgId": self.erp_org_id,
                    "documentNo": self.erp_document_no,
                    "documentId": self.erp_document_id,
                    "documentStatus": self.erp_document_status,
                    "createdAt": int(self.create_date.timestamp()),
                    "updatedAt": int(self.write_date.timestamp()),
                    "documentConfirmId": self.erp_document_confirm_id,
                    "documentConfirmNo": self.erp_document_confirm_no
                }
            }
        }
        return msg

    @api.model
    def _generate_queue_message_id(self):
        return str(uuid.uuid4())

    def action_open_location_out_popup(self):
        sml_pick = self.env['stock.move.location.pick']
        sml_pick_line = self.env['stock.move.location.pick.line']
        move_location_pick = sml_pick.search([('picking_id', '=', self.id), ('type', '=', 'pick_out')])
        if self.state == 'draft':
            if not move_location_pick:
                move_location_pick = sml_pick.create({
                    'picking_id': self.id,
                    'type': 'pick_out',
                })
            for item in self.move_ids_without_package:
                sql = """
                        WITH PackageAvailability AS (
                            SELECT 
                                sq.location_id, 
                                sq.package_id, 
                                sq.product_id, 
                                pp.barcode, 
                                sq.quantity,
                                (
                                    SELECT COALESCE(SUM(sml.quantity), 0)
                                    FROM stock_move_line sml
                                    JOIN stock_picking sp ON sml.picking_id = sp.id
                                    WHERE sml.product_id = sq.product_id 
                                      AND sml.package_id = sq.package_id
                                      AND sml.location_id = sq.location_id
                                      AND sp.state NOT IN ('done', 'cancel')
                                ) AS reserved_qty
                            FROM stock_quant sq
                            JOIN stock_location sl ON sq.location_id = sl.id
                            JOIN stock_quant_package pack ON sq.package_id = pack.id
                            JOIN product_product pp ON sq.product_id = pp.id
                            WHERE pp.id = %s
                              AND pack.state = 'ready'
                              AND sq.quantity > (
                                  SELECT COALESCE(SUM(sml.quantity), 0)
                                  FROM stock_move_line sml
                                  JOIN stock_picking sp ON sml.picking_id = sp.id
                                  WHERE sml.product_id = sq.product_id 
                                    AND sml.package_id = sq.package_id
                                    AND sml.location_id = sq.location_id
                                    AND sp.state NOT IN ('done', 'cancel')
                              )
                            ORDER BY sl.name ASC
                        )
                        SELECT * FROM PackageAvailability;
                    """

                self._cr.execute(sql, (item.product_id.id,))
                available_packages = self._cr.dictfetchall()

                remaining_qty = item.product_uom_qty
                for pkg in available_packages:
                    if remaining_qty <= 0:
                        pick_to_unlink = line_pick.move_location_pick_id.move_location_pick_ids.filtered(
                            lambda x: x.id != line_pick.id and x.product_id.id == line_pick.product_id.id)
                        pick_to_unlink.unlink()
                        break

                    available_in_pkg = pkg['quantity'] - pkg['reserved_qty']

                    pick_qty = min(remaining_qty, available_in_pkg)

                    val = {
                        'default_code': item.product_id.default_code,
                        'move_id': item.id,
                        'product_id': item.product_id.id,
                        'uom_id': item.product_uom.id,
                        'quantity': pick_qty,
                        'package_id': pkg['package_id'],
                        'location_id': pkg['location_id'],
                        'move_location_pick_id': move_location_pick.id,
                    }

                    line_pick = sml_pick_line.search([
                        ('move_id', '=', item.id),
                        ('package_id', '=', pkg['package_id']),
                        ('move_location_pick_id', '=', move_location_pick.id)
                    ])

                    if not line_pick:
                        sml_pick_line.create(val)
                    else:
                        line_pick.write(val)

                    # Update remaining quantity
                    remaining_qty -= pick_qty
                if not available_packages:
                    val = {
                        'default_code': item.product_id.default_code,
                        'move_id': item.id,
                        'product_id': item.product_id.id,
                        'uom_id': item.product_uom.id,
                        'quantity': item.product_uom_qty,
                        'move_location_pick_id': move_location_pick.id,
                    }

                    line_pick = sml_pick_line.search([
                        ('move_id', '=', item.id),
                        ('move_location_pick_id', '=', move_location_pick.id)
                    ])

                    if not line_pick:
                        sml_pick_line.create(val)
                    else:
                        sml_pick_line.write(val)

        # Disable editing if picking is done or cancelled
        if self.state in ('done', 'cancel', 'assigned'):
            move_location_pick.can_edit = False
        return {
            'name': _('Location Pick Out'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.location.pick',
            'res_id': move_location_pick.id,
            'view_mode': 'form',
            'view_id': self.env.ref('z_stock_picking.stock_move_location_pick_view').id,
            'target': 'new',
        }

    def action_open_location_in_popup(self):
        sml_pick = self.env['stock.move.location.pick']
        sml_pick_line = self.env['stock.move.location.pick.line']
        move_location_pick = sml_pick.search([('picking_id', '=', self.id), ('type', '=', 'pick_in')])
        if self.state in ('draft', 'confirmed'):
            if not move_location_pick:
                move_location_pick = sml_pick.create(
                    {
                        'picking_id': self.id,
                        'type': 'pick_in',
                    }
                )
            for i, item in enumerate(self.move_ids_without_package):
                package = self.env['stock.quant.package'].search([('location_id', '=', item.picking_id.warehouse_dest_id.lot_stock_id.id)])
                val = {
                    'default_code': item.product_id.default_code,
                    'move_id': item.id,
                    'product_id': item.product_id.id,
                    'uom_id': item.product_uom.id,
                    'quantity': item.product_uom_qty,
                    'location_id': item.picking_id.warehouse_dest_id.lot_stock_id.id,
                    'package_id': package[0] if package else None,
                    'move_location_pick_id': move_location_pick.id,
                }
                line_pick = sml_pick_line.search([
                    ('move_id', '=', item.id),
                    ('move_location_pick_id', '=', move_location_pick.id)
                ])
                if not line_pick:
                    sml_pick_line.create(val)
                else:
                    line_pick.write(val)

        if self.state in ('done', 'cancel', 'assigned'):
            move_location_pick.can_edit = False
        return {
            'name': _('Location Pick In'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.location.pick',
            'res_id': move_location_pick.id,
            'view_mode': 'form',
            'view_id': self.env.ref('z_stock_picking.stock_move_location_pick_view').id,
            'target': 'new',
        }

    def action_confirm(self):
        pick_out = self.env['stock.move.location.pick'].search(
            [('picking_id', '=', self.id), ('type', '=', 'pick_out')])
        if not self.erp_created_at:
            if self.state == 'draft' and self.picking_type_code in ('outgoing', 'internal'):
                pick_out = self.env['stock.move.location.pick'].search(
                        [('picking_id', '=', self.id), ('type', '=', 'pick_out')])
                if not pick_out or not pick_out.move_location_pick_ids:
                    raise UserError(_('Not enough locations have been declared for the product.\n'
                                      'Please declare enough import/export warehouse locations for the product!'))
                for item in pick_out.move_location_pick_ids:
                    if not item.location_id:
                        raise UserError(_('Not enough locations have been declared for the product.\n'
                                          'Please declare enough import/export warehouse locations for the product!'))
        sum1 = 0
        for item in self.move_ids_without_package:
            sum1 += item.product_uom_qty
        sum2 = 0
        for item in pick_out.move_location_pick_ids:
            sum2 += item.quantity
        if sum2 > sum1:
            picking_confirm = self.env['stock.picking.confirm'].create({
                'picking_id': self.id,
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking.confirm',
                'res_id': picking_confirm.id,
                'view_mode': 'form',
                'view_id': self.env.ref('z_stock_picking.stock_picking_confirm').id,
                'target': 'new',
            }
        else:
            self.action_confirm_popup()



    def action_confirm_popup(self):
        res = super(StockPicking, self).action_confirm()
        if self.z_transfer_type == 'wms_ho_to_ho':
            self.action_confirm_internal_export()
        if self.z_transfer_type == 'wms_ho_to_shop':
            host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
            topic = 'wms.to.erp.transfer.request'
            list_msg = self._prepare_wms_ho_to_shop_queue_msg()
            for item in list_msg:
                print(json.dumps(item).encode('utf-8'))
                conf = {
                    'bootstrap.servers': '%s' % host,
                }
                producer = Producer(conf)
                producer.produce(topic, json.dumps(item).encode('utf-8'))
                producer.flush()
                msg_log = self.env['msg.log'].sudo().create({
                    'topic_send': 'wms.to.erp.transfer.request',
                    'action_type': 'create',
                    'message_send': item,
                    'obj_name': 'wmsToErpTransferRequest',
                })
        pick_out = self.env['stock.move.location.pick'].search(
            [('picking_id', '=', self.id), ('type', '=', 'pick_out')])
        if pick_out:
            pick_out.can_edit = False
        return res


    def push_action(self):

        _logger.error(self.po_internal_order_info)
        _logger.error(self.so_internal_order_info)
        _logger.error(self.so_internal_invoice_info)
        _logger.error(self.po_internal_invoice_info)
        return

        sql = """
            SELECT create_date, write_date FROM stock_picking WHERE id = %s;
        """ % self.id
        self._cr.execute(sql)
        res_sql = self._cr.dictfetchall()

        host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
        document_type = self.env['stock.document.type'].sudo().search([('erp_document_type_id', '=', self.erp_document_type_id)], limit=1)
        msg = {
            'messageId': self._generate_queue_message_id(),
            'objName': 'wmsToErpTransferRequest',
            'actionType': 'confirm',
            'objData': {
                'requestId': self.name,
                'approvedBy': {
                    'userId': self.user_id.erp_user_id,
                    'userCode': self.user_id.ref,
                    'userName': self.user_id.name,
                    'approvedDate': int(datetime.now().timestamp() * 1000),
                },
                'movementInfo': {
                    'orgId': self.erp_org_id,
                    'documentNo': self.erp_document_no,
                    'documentId': self.erp_document_id,
                    'documentStatus': 'InProcess',
                    'createdAt': int(self.erp_created_at.timestamp() * 1000) if self.erp_created_at else int(self.create_date.timestamp() * 1000),
                    'updatedAt':  int(self.erp_updated_at.timestamp() * 1000) if self.erp_updated_at else int(self.write_date.timestamp() * 1000),
                    'documentTypeInfo': {
                        'documentTypeId': self.erp_document_type_id if self.erp_document_type_id else None,
                        'documentTypeName': document_type.name if document_type else None
                    },
                    'documentConfirmId': self.erp_document_confirm_id,
                    'documentConfirmNo': self.erp_document_confirm_no,
                },
                'fromSource': {
                    'source': 'WMS',
                    'clientId': 1000001,
                },
                'status': 'Complete',
            }
        }
        conf = {
            'bootstrap.servers': '%s' % host,
        }
        producer = Producer(conf)
        producer.produce('wms.to.erp.transfer.request', json.dumps(msg).encode('utf-8'))
        producer.flush()

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        return res
        # Nếu tích xuất cả thùng trên dòng pick location, khi xác nhận phiếu kho => chuyển trạng thái thùng sang done
        for move in self.move_line_ids_without_package:
            if move.package_id:
                line_pick = self.env['stock.move.location.pick.line'].sudo().search(
                    [('move_id', '=', move.move_id.id), ('package_id', '=', move.package_id.id)])
                for item in line_pick:
                    if item.is_out_of_package:
                        item.package_id.state = 'done'
        sql = """
            SELECT create_date, write_date FROM stock_picking WHERE id = %s;
        """ % self.id
        self._cr.execute(sql)
        res_sql = self._cr.dictfetchall()

        host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
        if self.z_transfer_type in ['wms_ho_to_shop'] or self.z_transfer_type_sync in ['erp_ho_to_shop', 'erp_shop_to_ho', 'erp_internal_export']:
            document_type = self.env['stock.document.type'].sudo().search([('erp_document_type_id', '=', self.erp_document_type_id)], limit=1)
            msg = {
                'messageId': self._generate_queue_message_id(),
                'objName': 'wmsToErpTransferRequest',
                'actionType': 'confirm',
                'objData': {
                    'requestId': self.name,
                    'approvedBy': {
                        'userId': self.user_id.erp_user_id,
                        'userCode': self.user_id.ref,
                        'userName': self.user_id.name,
                        'approvedDate': int(datetime.now().timestamp() * 1000),
                    },
                    'movementInfo': {
                        'orgId': self.erp_org_id,
                        'documentNo': self.erp_document_no,
                        'documentId': self.erp_document_id,
                        'documentStatus': 'InProcess',
                        'createdAt': int(self.erp_created_at.timestamp() * 1000) if self.erp_created_at else int(self.create_date.timestamp() * 1000),
                        'updatedAt':  int(self.erp_updated_at.timestamp() * 1000) if self.erp_updated_at else int(self.write_date.timestamp() * 1000),
                        'documentTypeInfo': {
                            'documentTypeId': self.erp_document_type_id if self.erp_document_type_id else None,
                            'documentTypeName': document_type if document_type else None
                        },
                        'documentConfirmId': self.erp_document_confirm_id,
                        'documentConfirmNo': self.erp_document_confirm_no,
                    },
                    'fromSource': {
                        'source': 'WMS',
                        'clientId': 1000001,
                    },
                    'status': 'Complete',
                }
            }
            conf = {
                'bootstrap.servers': '%s' % host,
            }
            producer = Producer(conf)
            producer.produce('wms.to.erp.transfer.request', json.dumps(msg).encode('utf-8'))
            producer.flush()
        return res

    def action_assign(self):
        if self.state in ('waiting', 'confirmed', 'assigned') and self.picking_type_code in ('internal', 'incoming'):
            pick_in = self.env['stock.move.location.pick'].search(
                        [('picking_id', '=', self.id), ('type', '=', 'pick_in')])
            if not pick_in or not pick_in.move_location_pick_ids:
                raise UserError(_('Not enough locations have been declared for the product.\n'
                                  'Please declare enough import/export warehouse locations for the product!'))
            for item in pick_in.move_location_pick_ids:
                if not item.location_id:
                    raise UserError(_('Not enough locations have been declared for the product.\n'
                                      'Please declare enough import/export warehouse locations for the product!'))

        res = super(StockPicking, self).action_assign()
        # Create stock_move_line from stock_move_location_pick_line
        if self.move_line_ids_without_package:
            self.move_line_ids_without_package.unlink()
        move_pick_out = self.env['stock.move.location.pick'].search([('picking_id', '=', self.id), ('type', '=', 'pick_out')])
        move_pick_in = self.env['stock.move.location.pick'].search([('picking_id', '=', self.id), ('type', '=', 'pick_in')])

        if self.picking_type_code == 'outgoing':
            move_line_vals = []
            for item in move_pick_out.move_location_pick_ids:
                val = self._prepare_move_line_vals_from_pick_location(item)
                val.update({
                    'location_id': item.location_id.id,
                    'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                })
                move_line_vals.append(val)
        elif self.picking_type_code == 'incoming':
            move_line_vals = []
            for item in move_pick_in.move_location_pick_ids:
                val = self._prepare_move_line_vals_from_pick_location(item)
                val.update({
                    'location_id': self.env.ref('stock.stock_location_suppliers').id,
                    'location_dest_id': item.location_id.id,
                })
                move_line_vals.append(val)
        elif self.picking_type_code == 'internal':
            move_line_vals = []
            for item in move_pick_out.move_location_pick_ids:
                val = self._prepare_move_line_vals_from_pick_location(item)
                line_pick_in = move_pick_in.move_location_pick_ids.filtered(lambda x: x.move_id == item.move_id and x.product_id == item.product_id)
                val.update({
                    'location_id': item.location_id.id,
                    'location_dest_id': line_pick_in.location_id.id,
                })
                move_line_vals.append(val)

        move_lines = self.env['stock.move.line'].create(move_line_vals)
        return res

    def _prepare_move_line_vals_from_pick_location(self, pick_loc_line):
        self.ensure_one()
        vals = {
            'move_id': pick_loc_line.move_id.id,
            'product_id': pick_loc_line.product_id.id,
            'product_uom_id': pick_loc_line.uom_id.id,
            'picking_id': self.id,
            'quantity': pick_loc_line.quantity,
            'company_id': self.company_id.id,
            'package_id': pick_loc_line.package_id.id,
            'owner_id': False,
        }
        return vals

    @api.model
    def barcode_product_search(self, barcode, pick_location_id):
        product = self.env['product.product'].search([('barcode', '=', barcode)])
        if not product:
            package = self.env['stock.quant.package'].search([('barcode', '=', barcode)])
            if not package:
                return True
        if product:
            pick_location = self.env['stock.move.location.pick'].search([('id', '=', pick_location_id)])
            pick_location_line = pick_location.move_location_pick_ids.filtered(lambda x: x.product_id.id == product.id)
            # if pick_location_line:
            #     for item in pick_location_line:
            #         item.quantity += 1
            stock_quant = self.env['stock.quant'].search([('product_id', '=', product.id), ('package_id', '!=', None)])
            quant_pick = self.env['stock.quant.package.pick'].search(
                [('pick_location_id', '=', pick_location.id), ('product_id', '=', product.id)])
            if not quant_pick:
                quant_pick = self.env['stock.quant.package.pick'].create({
                    'pick_location_id': pick_location.id,
                    'product_id': product.id,
                })
                quant_pick.quant_ids = [(6, 0, stock_quant.ids)]
            return ['product', quant_pick.id]
        elif package:
            pick_location = self.env['stock.move.location.pick'].search([('id', '=', pick_location_id)])
            list_1 = [(item.quantity, item.product_id.default_code) for item in pick_location.move_location_pick_ids]
            list_2 = [(item.quantity, item.product_id.default_code) for item in package.quant_ids]
            if list_1 != list_2:
                raise UserError(_('Product and quantity are not enough to export the carton "%s"') % package.name)
            else:
                for item in pick_location.move_location_pick_ids:
                    item.package_id = package.id
            return ['package', None]

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        for item in self:
            if item.warehouse_id:
                if item.z_transfer_type == 'wms_ho_to_shop':
                    stock_picking_type = self.env['stock.picking.type'].sudo().search([
                        ('warehouse_id', '=', item.warehouse_id.id),
                        ('code', '=', 'outgoing'),
                    ], limit=1)
                    item.picking_type_id = stock_picking_type.id
                if item.z_transfer_type == 'wms_ho_to_ho':
                    stock_picking_type = self.env['stock.picking.type'].sudo().search([
                        ('warehouse_id', '=', item.warehouse_id.id),
                        ('code', '=', 'internal'),
                    ], limit=1)
                    item.picking_type_id = stock_picking_type.id
                if item.z_transfer_type == 'wms_transfer_location':
                    stock_picking_type = self.env['stock.picking.type'].sudo().search([
                        ('warehouse_id', '=', item.warehouse_id.id),
                        ('code', '=', 'outgoing'),
                    ], limit=1)
                    item.picking_type_id = stock_picking_type.id

    @api.onchange('z_transfer_type')
    def _onchange_transfer_type(self):
        for item in self:
            item.warehouse_id = None
            item.warehouse_dest_id = None
            warehouse = self.env['stock.warehouse']
            if item.z_transfer_type == 'wms_ho_to_shop':
                item.x_picking_type_code = 'outgoing'
                item.is_invisible = False
                item.x_warehouse_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', True)]).ids)]
                item.x_warehouse_dest_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', False)]).ids)]
            elif item.z_transfer_type == 'wms_ho_to_ho':
                item.x_picking_type_code = 'internal'
                item.is_invisible = False
                item.x_warehouse_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', True)]).ids)]
                item.x_warehouse_dest_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', True)]).ids)]
            elif item.z_transfer_type == 'wms_transfer_location':
                item.x_picking_type_code = 'outgoing'
                item.is_invisible = True
                item.x_warehouse_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', True)]).ids)]
                item.x_warehouse_dest_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', False)]).ids)]

    @api.model_create_multi
    def create(self, vals_list):
        _logger.warning('======vals_list====== %s' % vals_list)
        error = False
        try:
            res = super(StockPicking, self).create(vals_list)
        except Exception as ex:
            error = True
        warehouse = self.env['stock.warehouse']
        if not error:
            if res.z_transfer_type_sync == 'erp_ho_to_shop':
                res.x_picking_type_code = 'outgoing'
                res.is_invisible = False
                res.x_warehouse_dest_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', False)]).ids)]
                self.action_send_msg_when_create_picking_success(res.erp_msg_create, res.name)
            elif res.z_transfer_type_sync == 'erp_shop_to_ho':
                res.x_picking_type_code = 'incoming'
                res.is_invisible = True
                res.x_warehouse_dest_id_domain_ids = [(6, 0, warehouse.search([('is_ho_warehouse', '=', True)]).ids)]
                self.action_send_msg_when_create_picking_success(res.erp_msg_create, res.name)
        else:
            pass
        return res

    def action_read_xls_master_data(self):
        import pandas as pd
        import json
        try:
            module_path = get_module_path('z_stock_picking') + '/data/Data ADVL.xls'
            df = pd.read_excel(module_path, sheet_name='INV12_Tonkho_Toan_cuahang')
            data = df.to_dict(orient='records')
            for item in data:
                barcode_value = str(item['Barcode'])[:-2]
                default_code = str(item['Mã sản phẩm'])
                qty = item['HAN.HO - HO - Hà Nội']
                print(barcode_value, default_code, qty)
                try:
                    self.action_init_product_product(default_code, barcode_value, qty)
                except Exception as e:
                    continue
        except:
            raise

    def action_read_xls_master_data_1(self):
        import pandas as pd
        import json
        try:
            module_path = get_module_path('z_stock_picking') + '/data/Data HER (1).xls'
            df = pd.read_excel(module_path, sheet_name='INV12_Tonkho_Toan_cuahang')
            data = df.to_dict(orient='records')
            for item in data:
                barcode_value = str(item['Barcode'])[:-2]
                default_code = str(item['Mã sản phẩm'])
                qty = item['HAN.HO - HO - Hà Nội']
                # Create product_attribute_value

                print(barcode_value, default_code, qty)
                try:
                    self.action_init_product_product(default_code, barcode_value, qty)
                except Exception as e:
                    continue
        except:
            raise

    # Tạo biến thể sản phẩm khi map product_tmpl_id và barcode_id, gắn barcode cho biến thể sản phẩm
    def action_init_product_product(self, default_code, barcode_value, qty):
        erp_barcode = self.env['erp.barcode'].search([('erp_barcode_value', '=', barcode_value)])
        product_template = self.env['product.template'].search([('erp_default_code', '=', default_code)])
        attribute_barcode_id = self.env['product.attribute'].search([('name', '=', 'Barcode')])
        attribute_value_barcode_id = self.env['product.attribute.value'].search([('name', '=', barcode_value)])
        attr_val = []
        attr_val.append(
            (0, 0, {
                'attribute_id': attribute_barcode_id.id,
                'value_ids': [(4, attribute_value_barcode_id.id)],
            })
        )
        attribute_value_ids = []
        for item in erp_barcode.barcode_line_ids:
            if item.product_attribute_id and item.product_attribute_value_id and item.product_attribute_value_id.name != 'NA':
                attribute_value_ids.append(item.product_attribute_value_id.id)
                attribute_line = self.env['product.template.attribute.line'].search(
                    [
                        ('attribute_id', '=', item.product_attribute_id.id),
                        ('product_tmpl_id', '=', product_template.id)
                    ])
                if attribute_line:
                    attribute_line.value_ids = [(4, item.product_attribute_value_id.id)]
                else:
                    attr_val.append(
                        (0, 0, {
                            'attribute_id': item.product_attribute_id.id,
                            'value_ids': [(4, item.product_attribute_value_id.id)],
                        })
                    )
        product_template.write({
            'attribute_line_ids': attr_val
        })
        self._cr.commit()
        attribute_records = self.env['product.template.attribute.value'].search([
            ('product_attribute_value_id', 'in', attribute_value_ids),
            ('product_tmpl_id', '=', product_template.id),
        ]).ids
        product = self.env['product.template'].search(
            [('id', '=', product_template.id)]).product_variant_ids.filtered(
            lambda x: x.product_template_attribute_value_ids.ids == attribute_records)
        if product:
            if product.barcode:
                return 1
            product.barcode = erp_barcode.erp_barcode_value
        else:
            _logger.error(
                '========================= PRODUCT IS NONE ============ WITH default_code = %s , barcode_id = %s' % (
                    default_code, erp_barcode.id))
        self._cr.commit()
        if qty > 0:
            erp_warehouse_id = 1000180
            stock_warehouse = self.env['stock.warehouse'].search([('erp_warehouse_id', '=', erp_warehouse_id)])
            lot_stock_id = stock_warehouse.lot_stock_id
            stock_quant = self.env['stock.quant'].sudo().create({
                'location_id': lot_stock_id.id,
                'product_id': product.id,
                'inventory_quantity': qty,
            })
            self._cr.commit()
            if stock_quant:
                stock_quant._apply_inventory()

    def action_send_msg_when_create_picking_success(self, data, picking_name):
        topic_send = 'wms.to.erp.transfer.response'
        host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
        message_id = self._generate_queue_message_id()
        msg_create = {
            'messageId': message_id,
            'objName': 'wmsToErpTransferResponse',
            'actionType': 'create',
            'objData': {
                'status': 'success',
                'message': 'create successfully',
                'requestId': picking_name,
                'fromSource': {
                    'source': 'WMS',
                    'clientId': 1000001
                },
                'movementInfo': data['objData']['movementInfo'],
                'errorDetails': None
            }
        }
        self.action_producer_to_kafka(host, topic_send, msg_create)
        msg_log = self.env['msg.log'].create({
            'topic_send': topic_send,
            'message_send': msg_create,
            'obj_name': 'wmsToErpTransferResponse'
        })

    def action_send_msg_when_create_picking_error(self, data, ex):
        topic_send = 'wms.to.erp.transfer.response'
        host = self.env['ir.config_parameter'].sudo().get_param('kafka_consumer_host')
        message_id = self._generate_queue_message_id()
        msg_error = {
            'objName': 'wmsToErpTransferResponse',
            'actionType': 'confirm',
            'objData': {
                'status': 'error',
                'message': 'Invalid request data',
                'requestId': data['objData']['requestId'],
                'fromSource': {
                    'source': 'WMS',
                    'clientId': 1000001
                },
                'movementInfo': data['objData']['movementInfo'],
                'errorDetails': {
                    'pathCode': '500',
                    'errorMsg': ex
                }
            }
        }

    def action_producer_to_kafka(self, host, topic, msg):
        conf = {
            'bootstrap.servers': '%s' % host,
        }
        producer = Producer(conf)
        producer.produce(topic, json.dumps(msg).encode('utf-8'))
        producer.flush()
