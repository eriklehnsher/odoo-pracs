# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class StockInventoryPlan(models.Model):
    _name = 'stock.inventory.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock Inventory Plan'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    inventory_request_id = fields.Many2one('stock.inventory.request', string='Stock Inventory Request')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='User')
    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')
    warehouse_domain_ids = fields.Many2many('stock.warehouse', 'stock_inv_plan_warehouse_rel')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    inventory_plan_line_ids = fields.One2many('stock.inventory.plan.line', 'inventory_plan_id', string='Lines')
    inventory_ids = fields.One2many('stock.inventory', 'inventory_plan_id', string='Inventories')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='State', default='draft', tracking=True)

    def action_view_stock_inventory(self):
        action = self.env['ir.actions.actions']._for_xml_id('z_stock_inventory.stock_inventory_action')
        action['domain'] = [('id', 'in', self.inventory_ids.ids)]
        return action

    @api.model
    def create(self, vals):
        try:
            seq = self.env['ir.sequence'].next_by_code('tracking.stock.inventory.plan')
            vals['code'] = 'KHKK/' + datetime.today().strftime('%d%m%Y') + '/' + seq
            return super(StockInventoryPlan, self).create(vals)
        except Exception as e:
            raise ValidationError(e)

    def action_confirm(self):
        if self.state == 'draft':
            self.state = 'confirmed'

    def action_done(self):
        if self.state == 'confirmed':
            self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_create_stock_inventory(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory',
            'view_id': self.env.ref('z_stock_inventory.stock_inventory_form_view').id,
            'views': [[False, 'form']],
            'context': {
                'default_inventory_plan_id': self.id,
                'default_warehouse_domain_ids': self.warehouse_ids.ids,
            }
        }

    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        for item in self:
            if item.warehouse_ids:
                locations = self.env['stock.location'].search([('warehouse_id', 'in', item.warehouse_ids.ids)])
                if locations:
                    item.inventory_plan_line_ids = [(5, 0, 0)]
                    for lc in locations:
                        categ_ids = lc.mapped('quant_ids.product_id.categ_id')
                        if not categ_ids:
                            continue
                        for c in categ_ids:
                            val = {
                                'inventory_plan_id': item.id,
                                'categ_id': c.id,
                                'location_id': lc.id,
                            }
                            item.inventory_plan_line_ids = [(0, 0, val)]
            else:
                item.inventory_plan_line_ids = None
