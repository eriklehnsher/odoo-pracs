# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_pick_location = fields.Boolean(string='Pick Location', default=False)

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_stock_move_for_pick_location(self):
        if self.ids:
            for move in self:
                move_location_pick = self.env['stock.move.location.pick'].search(
                    [('picking_id', '=', move.picking_id.ids[0])])
                move_line_pick = move_location_pick.move_location_pick_ids.filtered(
                    lambda x: x.move_id.id == move.ids[0])
                if move_line_pick:
                    move_line_pick.product_id = move.product_id.id
                    move_line_pick.quantity = move.product_uom_qty
                    move_line_pick.uom_id = move.product_uom.id
