# -*- coding: utf-8 -*-

from odoo import models, fields, api
from unidecode import unidecode


class StockLocation(models.Model):
    _inherit = 'stock.location'

    erp_locator_id = fields.Integer(string='Locator ID')
    erp_is_active = fields.Boolean(string='Is Active')
    erp_is_default = fields.Boolean(string='Is Default')
    erp_code = fields.Integer(string='Locator Code')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockLocation, self).create(vals_list)
        res.barcode = unidecode(res.complete_name.replace('/', '-').replace(' ', '-').upper())
        return res

    def write(self, vals):
        res = super(StockLocation, self).write(vals)
        if 'name' in vals and vals['name']:
            self.barcode = unidecode(self.complete_name.replace('/', '-').replace(' ', '-').upper())
        return res
