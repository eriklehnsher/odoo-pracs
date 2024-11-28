# -*- coding: utf-8 -*-

from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # product_attribute_id = fields.Many2one('product.attribute', string='Product Attribute')
    # product_attribute_value_id = fields.Many2one('product.attribute.value', string='Product Attribute Value')
    erp_client_id = fields.Integer(string='ERP Client ID')
    erp_org_id = fields.Integer(string='ERP Organization ID')
    erp_barcode_id = fields.Integer(string='ERP Barcode ID')
    erp_barcode_value = fields.Char(string='ERP Barcode Value')
    erp_serial = fields.Char(string='ERP Serial')
    erp_eancode = fields.Char(string='ERP EAN Code')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    active = fields.Boolean(string='Active', default=True)
    date = fields.Date(string='Date')
