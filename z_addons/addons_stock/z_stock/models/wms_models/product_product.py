# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    erp_product_template_id = fields.Integer(string='Product Template ID',
                                             related='product_tmpl_id.erp_product_template_id', store=True)
