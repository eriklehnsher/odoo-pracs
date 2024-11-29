# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPickingConfirmation(models.TransientModel):
    _name = 'stock.picking.confirm'

    picking_id = fields.Many2one('stock.picking')
    text = fields.Char(string='Text',
                       default='Bạn đang nhập số lượng xuất/nhập lớn hơn số lượng nhu cầu. Bạn có chắc chắn muốn tiếp tục?')

    def action_save(self):
        self.picking_id.action_confirm_popup()
