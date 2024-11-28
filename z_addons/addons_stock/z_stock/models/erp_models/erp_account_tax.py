# -*- coding: utf-8 -*-

from odoo import models, fields


class ErpAccountTax(models.Model):
    _name = 'erp.account.tax'
    _description = 'Account Tax'
    _rec_name = 'tax_name'

    _sql_constraints = [
        ('uniq_tax_name', 'unique(tax_name)', 'Tax name must be unique.'),
    ]

    erp_tax_id = fields.Integer(string='ERP Tax ID')
    tax_name = fields.Char(string='Tax Name', required=True)
    tax_amount = fields.Float(string='Tax Rate', required=True)
    tax_description = fields.Char(string='Tax Description')
    active = fields.Boolean(string='Active', default=True)
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
