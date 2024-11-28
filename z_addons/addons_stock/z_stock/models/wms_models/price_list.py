# -*- coding: utf-8 -*-

from odoo import models, fields


class PriceList(models.Model):
    _name = 'price.list'
    _description = 'Price List'

    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description')
    # currency_id = fields.Many2one('erp.res.currency', string='Currency', required=True)
    rounding_factor = fields.Float(string='Rounding Factor', default=0.01, required=True)
    erp_price_list_id = fields.Integer(string='Erp Price List ID')
