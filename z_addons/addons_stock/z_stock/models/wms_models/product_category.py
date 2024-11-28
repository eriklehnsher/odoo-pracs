# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    erp_categ_id = fields.Integer(string='Erp Category ID')
    erp_code = fields.Char(string='Code')
