# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    _rec_name = 'brand_name'

    erp_product_brand_id = fields.Integer(string='ERP Product Brand ID')
    brand_code = fields.Char(string='Brand Code')
    brand_name = fields.Char(string='Brand Name')
    brand_description = fields.Char(string='Description')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    active = fields.Boolean(string='Active', default=True)
