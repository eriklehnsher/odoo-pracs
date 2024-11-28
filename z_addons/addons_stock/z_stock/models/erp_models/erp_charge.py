# -*- coding: utf-8 -*-

from odoo import models, fields


class ErpCharge(models.Model):
    _name = 'erp.charge'
    _description = 'Khoản phí'

    name = fields.Char(string='Tên', required=True)
    active = fields.Boolean(default=True)
    erp_charge_id = fields.Integer('ERP ID')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
