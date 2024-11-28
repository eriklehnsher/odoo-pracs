# -*- coding: utf-8 -*-

from odoo import models, fields, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True, index=True, readonly=True)

    def _get_stock_barcode_data(self):
        data = super(StockQuant, self)._get_stock_barcode_data()
        warehouses = self.env['stock.warehouse'].search([])
        data['records']['stock.warehouse'] = warehouses.read(['name', 'code', 'id', 'lot_stock_id', 'barcode'], load=False)
        return data
