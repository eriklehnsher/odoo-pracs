# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    value = fields.Char(string='Value')
    erp_product_attribute_value_id = fields.Integer(string='ERP Product Attribute Value ID')
    erp_created_at = fields.Datetime(string='Created At')
    erp_updated_at = fields.Datetime(string='Updated At')
    message_id = fields.Char(string='Message Id')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (erp_product_attribute_value_id)', ''), # Huỷ _sql_constraints của core
        ('unique_erp_product_attribute_value_id', 'unique(erp_product_attribute_value_id)', '')
    ]
