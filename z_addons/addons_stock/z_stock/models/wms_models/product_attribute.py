# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    _sql_constraints = [
        ('uniq_code', 'unique(name)', 'Name must be unique.'),
    ]

    name = fields.Char(string='Name')
    erp_product_attribute_id = fields.Integer(string='ERP Product Attribute ID', index=True)
    description = fields.Char(string='Description')
    erp_is_active = fields.Boolean(string='ERP Is Active')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
