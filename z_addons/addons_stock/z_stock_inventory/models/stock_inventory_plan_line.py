# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockInventoryPlanLine(models.Model):
    _name = 'stock.inventory.plan.line'
    _description = 'Stock Inventory Plan Line'

    categ_id = fields.Many2one('product.category', string='Category')
    inventory_plan_id = fields.Many2one('stock.inventory.plan', string='Inventory Plan')
    location_id = fields.Many2one('stock.location', string='Location')
    user_host_id = fields.Many2one('res.users', string='User Host')
    user_sup_id = fields.Many2one('res.users', string='User Support')
    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')
    note = fields.Text(string='Note')
