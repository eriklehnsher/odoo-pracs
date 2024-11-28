# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductLine(models.Model):
    _name = 'product.line'
    _description = 'Product Line'
    _rec_name = 'line_name'

    _sql_constraints = [
        ('uniq_code', 'unique(line_code)', 'Product line code must be unique.'),
    ]

    line_code = fields.Char(string='Product Line Code')
    line_name = fields.Char(string='Product Line Name')
    line_description = fields.Char(string='Product Line Description')
    erp_product_line_id = fields.Integer(string='ERP Product Line ID')
