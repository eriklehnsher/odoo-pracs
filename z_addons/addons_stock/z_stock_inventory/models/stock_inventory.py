# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
from confluent_kafka import Producer, KafkaException
import json
import logging

_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _name = 'stock.inventory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock Inventory'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code', tracking=True, index=True)
    date = fields.Date(string='Date', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True)
    location_ids = fields.Many2many('stock.location', string='Locations', tracking=True)
    reason = fields.Text(string='Reason', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    inventory_plan_id = fields.Many2one('stock.inventory.plan', string='Inventory Plan')
    warehouse_domain_ids = fields.Many2many('stock.warehouse', string='Warehouses Domain')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'Progress'),
        ('done', 'Done'),
    ], default='draft', string='State', tracking=True)
    state_approval = fields.Selection([
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('reject', 'Reject'),
    ], string='State Approval', tracking=True)
    is_approval = fields.Boolean(string='Is Approval', default=False)
    inventory_line_ids = fields.One2many('stock.quant', 'stock_inventory_id', string='Inventory Lines')
    approval_line_ids = fields.One2many('stock.inventory.approval.config', 'stock_inventory_id', string='Approval Lines')
    erp_message_receive = fields.Text(string='ERP Message Receive')
    erp_message_create = fields.Text(string='ERP Message Create')
    erp_message_error = fields.Text(string='ERP Message Error')
    erp_res_company_id = fields.Many2one('erp.res.company', string='ERP Res Company')
    erp_document_no = fields.Char(string='ERP Document No')
    erp_document_id = fields.Integer(string='ERP Document ID')
    erp_document_type_id = fields.Integer(string='ERP Document Type ID')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    erp_client_id = fields.Integer(string='ERP Client ID')
    erp_org_id = fields.Integer(string='ERP Organization ID')
    erp_document_state = fields.Char(string='ERP Document State')
    erp_created_uid = fields.Integer(string='ERP Created UID')

    @api.model
    def create(self, vals):
        try:
            seq = self.env['ir.sequence'].next_by_code('tracking.stock.inventory')
            vals['code'] = 'KKK/' + datetime.today().strftime('%d%m%Y') + '/' + seq
            return super(StockInventory, self).create(vals)
        except Exception as e:
            raise ValidationError(e)

    @api.model
    def open_new_stock_inventory(self):
        new_stock_inventory = self.env['stock.inventory'].create({
            'date': datetime.now(),
            'name': _('Inventory Adjustment')
        })
        return new_stock_inventory.action_client_action()

    def start_inventory(self):
        list_stock_quant = self.env['stock.quant'].search([('location_id', 'in', self.location_ids.ids)])
        for item in list_stock_quant:
            item.stock_inventory_id = self.id
        self.state = 'progress'

    def action_confirm(self):
        # Confirm stock inventory
        quants = self.inventory_line_ids.filtered('inventory_quantity_set')
        quants.with_context(inventory_mode=True).action_apply_inventory()
        self.state = 'done'
        # After confirm stock inventory, send message to kafka
        try:
            for i, item in enumerate(self.inventory_line_ids):
                barcode = self.env['erp.barcode'].search([('erp_barcode_value', '=', item.erp_barcode_value)])
                msg = {
                    'messageId': self.env['stock.picking']._generate_queue_message_id(),
                    'objName': 'wmsToErpPhysicalInventoryRequest',
                    'actionType': 'create',
                    'objData': {
                        'metaData': {
                            'sequenceId': i + 1,
                            'totalLines': len(self.inventory_line_ids),
                        },
                        'requestId': self.code,
                        'fromSource': {
                            'source': 'WMS',
                            'clientId': self.erp_res_company_id.erp_client_id,
                        },
                        'sourceWarehouse': {
                            'orgId': self.warehouse_id.erp_org_id,
                            'warehouseId': self.warehouse_id.id,
                            'warehouseCode': self.warehouse_id.code,
                            'warehouseName': self.warehouse_id.name,
                        },
                        'requestDate': int(self.date.timestamp()),
                        'requestedBy': {
                            'userId': self.create_uid.erp_user_id,
                            'userCode': self.create_uid.ref,
                            'userName': self.create_uid.login,
                        },
                        'items': {
                            'lineId': item.id,
                            'productId': item.product_id.product_tmpl_id.erp_product_template_id,
                            'productCode': item.product_id.product_tmpl_id.erp_default_code,
                            'productName': item.product_id.product_tmpl_id.name,
                            'barcodeId': barcode.id if barcode else None,
                            'barcodeValue': item.product_id.barcode,
                            'systemQuantity': item.quantity,
                            'actualQuantity': item.inventory_quantity,
                            'difference': item.inventory_diff_quantity,
                            'uomId': item.product_id.uom_id.erp_uom_id,
                        },
                        'remarks': self.name,
                        'status': self.state,
                    }
                }
                conf = {
                    'bootstrap.servers': '160.30.44.54:9092',
                }
                producer = Producer(conf)
                producer.produce('wms.to.erp.physicalinv.request', json.dumps(msg).encode('utf-8'))
                producer.flush()
        except KafkaException as ex:
            _logger.error('Error producer to kafka for stock inventory: %s' % ex)

    def action_confirm_for_approval(self):
        self.is_approval = True
        vals = []
        for item in self.env['stock.inventory.approval'].search([]):
            vals.append(
                (0, 0, {
                    'level': item.level,
                    'user_ids': [(6, 0, item.user_ids.ids)]
                })
            )
        self.write({
            'approval_line_ids': vals
        })

    def action_require_approval(self):
        self.state_approval = 'waiting_approval'

    def action_approval(self):

        self.state_approval = 'approved'

    def action_reject(self):
        self.state_approval = 'reject'

    def action_scan_barcode(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'stock_barcode_client_action',
            'res_model': 'stock.inventory',
            'context': {
                'active_id': self.id,
                'target': 'fullscreen'
            }
        }

    def _get_stock_barcode_data(self):
        inv_data = {}
        inv_data = self.inventory_line_ids._get_stock_barcode_data()
        inv_data['records'].update({
            self._name: self.read([
                'inventory_line_ids',
                'name',
                'location_ids',
                'state',
                'date',
                'reason',
                'id',
            ], load=False)
        })
        inv_data['records']['stock.location'] = self.env['stock.location'].search([]).read(
            self.env['stock.location']._get_fields_stock_barcode(), load=False)
        for inv in inv_data['records'][self._name]:
            inv['inventory_line_ids'] = self.browse(inv['id']).inventory_line_ids.sorted(key=lambda p: p.id).ids

        inv_data['line_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode').id
        inv_data['form_view_id'] = self.env.ref(
            'z_stock_inventory.stock_inventory_barcode_view_info').id
        return inv_data

    def get_stock_barcode_data_records(self):
        data = {
            "records": {
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "user_id": self.env.user.id,
        }
        return data

    @api.model
    def barcode_search(self, last_code, inv_id):
        _logger.error('%s =========== %s' % (last_code, inv_id))
        product = self.env['product.product'].search([('barcode', '=', last_code)])
        if not product:
            return True
        else:
            stock_inventory = self.browse(inv_id)
            if stock_inventory.inventory_line_ids:
                for rec in stock_inventory.inventory_line_ids:
                    if rec.product_id == product:
                        rec.inventory_quantity += 1
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'reload',
                        }
            stock_inventory.inventory_line_ids.create({
                'stock_inventory_id': stock_inventory.id,
                'product_id': product.id,
                'inventory_quantity': 1,
                'location_id': None,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def action_client_action(self):
        action = self.env['ir.actions.actions']._for_xml_id('z_stock_inventory.stock_inventory_client_action')
        return dict(action, context={'active_id': self.id}, target='fullscreen')

    @api.model
    def barcode_write(self, vals):
        Quant = self.env['stock.quant'].with_context(inventory_mode=True)
        return Quant.barcode_write(vals)

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if self.warehouse_id:
            location_ids = self.env['stock.location'].search([('warehouse_id', '=', self.warehouse_id.id)])
            self.location_ids = [(6, 0, location_ids.ids)]
        else:
            self.location_ids = None


class StockInventoryApprovalConfig(models.Model):
    _name = 'stock.inventory.approval.config'
    _description = 'Stock Inventory Approval Config'

    level = fields.Integer(string='Level')
    user_ids = fields.Many2many('res.users', string='Users')
    is_approved = fields.Boolean(string='Approved', default=False)
    stock_inventory_id = fields.Many2one('stock.inventory', string='Stock Inventory')
