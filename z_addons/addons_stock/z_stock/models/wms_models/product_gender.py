# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductGender(models.Model):
    _name = 'product.gender'
    _description = 'Product Gender'
    _rec_name = 'name'

    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'Gender code must be unique.'),
    ]

    code = fields.Char(string='Gender code')
    name = fields.Char(string='Gender name')
    description = fields.Char(string='Gender description')
    erp_product_gender_id = fields.Integer(string='ERP Product Gender ID')
