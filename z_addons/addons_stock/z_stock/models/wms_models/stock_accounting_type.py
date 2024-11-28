# -*- coding: utf-8 -*-

from odoo import models, fields


class XAccountMove(models.Model):
    _name = 'stock.accounting.type'
    _description = 'Stock Accounting Type'

    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'Stock accounting type code must be unique.'),
    ]

    name = fields.Char(string='Accounting Name', required=True)
    code = fields.Char(string='Accounting Code', required=True)
    description = fields.Char(string='Description')
