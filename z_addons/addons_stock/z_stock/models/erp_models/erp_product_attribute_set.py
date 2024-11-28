# -*- coding: utf-8 -*-

from odoo import models, fields


class ErpProductAttributeSet(models.Model):
    _name = 'erp.product.attribute.set'
    _description = 'Erp Product Attribute Set'

    _sql_constraints = [
        ('uniq_code', 'unique(name)', 'Name must be unique.'),
    ]

    erp_product_attribute_set_id = fields.Integer(string='Erp Product Attribute Set ID')
    name = fields.Char(string='Name')
    description = fields.Char(string='Description')
    product_attribute_ids = fields.Many2many('product.attribute', string='Product Attributes')
    active = fields.Boolean(string='Active', default=True)
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
