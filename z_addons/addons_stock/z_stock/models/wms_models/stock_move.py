# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID


class StockMove(models.Model):
    _inherit = 'stock.move'

    erp_line_id = fields.Integer(string='Erp Line ID')
    erp_barcode_id = fields.Integer(string='Erp Barcode ID')
    erp_barcode_value = fields.Char(string='Erp Barcode Value')

