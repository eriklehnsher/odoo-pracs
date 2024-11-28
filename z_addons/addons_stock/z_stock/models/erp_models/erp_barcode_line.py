# -*- coding: utf-8 -*-

from odoo import models, fields


class ERPBarcodeLine(models.Model):
    _name = 'erp.barcode.line'
    _description = 'ERP Barcode Line'

    barcode_id = fields.Many2one('erp.barcode', string='ERP Barcode')
    erp_product_attribute_id = fields.Integer(string='ERP Product Attribute ID')
    erp_product_attribute_value_id = fields.Integer(string='ERP Product Attribute Value ID')
    product_attribute_id = fields.Many2one('product.attribute', string='Product Attribute')
    product_attribute_value_id = fields.Many2one('product.attribute.value', string='ERP Attribute Value')
