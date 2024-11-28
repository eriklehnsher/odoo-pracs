# -*- coding: utf-8 -*-

from odoo import models, fields


class StockCustomsDeclaration(models.Model):
    _name = 'stock.customs.declaration'
    _description = 'Stock Customs Declaration'

    _sql_constraints = [
        ('uniq_number_declaration', 'unique(number_declaration)', 'Stock accounting type code must be unique.'),
    ]

    erp_id = fields.Integer(string='ERP ID')
    number_declaration = fields.Char(string='Customs Declaration Number', required=True)
    name = fields.Char(string='Customs Declaration Name', required=True)
    description = fields.Char(string='Customs Declaration Description')
    date = fields.Datetime(string='Ngày làm tờ khai hải quan')
    product_brand_ids = fields.Many2many('product.brand', string='Product Brands', required=True)
