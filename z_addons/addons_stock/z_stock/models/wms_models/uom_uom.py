# -*- coding: utf-8 -*-

from odoo import models, fields


class Uom(models.Model):
    _inherit = 'uom.uom'

    erp_uom_id = fields.Integer(string='Erp Uom Id')
    erp_uom_symbol = fields.Char(string='Erp Uom Symbol')
    description = fields.Char(string='Description')
    erp_uom_trl_info = fields.Json(string='Erp Uom Trl Info')

    _sql_constraints = [
        ('uniq_erp_uom_id', 'unique(erp_uom_id)', 'Erp Uom Id must be unique.'),
    ]
