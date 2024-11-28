# -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def get_warehouse_by_location(self, _ids):
        warehouse = self.env['stock.location'].search([('id', '=', _ids[0])]).warehouse_id
        return warehouse.read(['name', 'code', 'id', 'lot_stock_id', 'barcode'], load=False)[0]
