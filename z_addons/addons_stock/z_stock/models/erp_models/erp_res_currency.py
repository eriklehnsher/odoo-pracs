# -*- coding: utf-8 -*-

from odoo import models, fields


class XResCurrency(models.Model):
    _name = 'erp.res.currency'
    _description = 'Currency'
    _rec_name = 'code'

    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'Currency code must be unique.'),
    ]

    code = fields.Char(string='Currency Code', required=True)
    symbol = fields.Char(string='Symbol')
    description = fields.Char(string='Description', required=True)
    erp_currency_id = fields.Integer(string='Erp Currency ID')
    active = fields.Boolean(string='Active', default=True)
