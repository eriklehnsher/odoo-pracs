# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class StockInventoryRequest(models.Model):
    _name = 'stock.inventory.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock Inventory Request'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    date = fields.Date(string='Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    plan_ids = fields.One2many('stock.inventory.plan', 'inventory_request_id', string='Plans')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='State', default='draft', tracking=True)

    def action_view_stock_inventory_plan(self):
        action = self.env['ir.actions.actions']._for_xml_id('z_stock_inventory.stock_inventory_plan_action')
        action['domain'] = [('id', 'in', self.plan_ids.ids)]
        return action

    @api.model
    def create(self, vals):
        try:
            seq = self.env['ir.sequence'].next_by_code('tracking.stock.inventory.request')
            vals['code'] = 'YCKK/' + datetime.today().strftime('%d%m%Y') + '/' + seq
            return super(StockInventoryRequest, self).create(vals)
        except Exception as e:
            raise ValidationError(e)

    def action_create_plan(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.plan',
            'view_id': self.env.ref('z_stock_inventory.stock_inventory_plan_form_view').id,
            'views': [[False, 'form']],
            'context': {
                'default_company_id': self.company_id.id,
                'default_inventory_request_id': self.id,
                'default_warehouse_domain_ids': self.warehouse_ids.ids,
            },
        }

    def action_confirm(self):
        if self.state == 'draft':
            self.state = 'confirmed'
