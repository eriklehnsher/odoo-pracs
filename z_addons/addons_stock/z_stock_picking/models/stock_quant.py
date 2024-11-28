# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    quant_pick_id = fields.Many2one('stock.quant.package.pick', string='Quant Pick')
    x_is_pick = fields.Boolean(string='Is Pick', default=False)
