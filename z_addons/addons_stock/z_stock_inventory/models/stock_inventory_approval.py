# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockInventoryApproval(models.Model):
    _name = 'stock.inventory.approval'
    _description = 'Stock Inventory Approval Config'

    level = fields.Integer(string='Level', required=True)
    user_ids = fields.Many2many('res.users', string='Users', required=True)
