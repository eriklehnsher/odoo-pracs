# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    stock_inventory_id = fields.Many2one('stock.inventory', string='Stock Inventory')

    def action_validate(self):
        quants = self.with_context(inventory_mode=True).filtered(lambda q: q.inventory_quantity_set)
        quants._compute_inventory_diff_quantity()
        res = quants.action_apply_inventory()
        self.stock_inventory_id.state = 'done'
        if res:
            return res
        return True
