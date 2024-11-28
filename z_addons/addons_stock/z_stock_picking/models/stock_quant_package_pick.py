# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuantPackagePick(models.Model):
    _name = 'stock.quant.package.pick'
    _description = 'Stock Quant Package Pick'

    quant_ids = fields.One2many('stock.quant', 'quant_pick_id', string='Lines')
    pick_location_id = fields.Many2one('stock.move.location.pick', 'Pick Location')
    product_id = fields.Many2one('product.product', 'Product')

    def action_select_package(self):
        list_line_pick = self.quant_ids.filtered(lambda x: x.x_is_pick)
        if len(list_line_pick) > 1:
            raise UserError(_('You can only pick a single line.'))
        if list_line_pick:
            stock_move_location_pick_line = self.env['stock.move.location.pick.line'].search(
                [
                    ('move_location_pick_id', '=', self.pick_location_id.id),
                    ('product_id', '=', list_line_pick.product_id.id),
                    ('is_pick_package_barcode', '=', False)
                ], order='id asc', limit=1)
            if stock_move_location_pick_line:
                list_line_pick.quant_pick_id = None
                stock_move_location_pick_line.package_id = list_line_pick.package_id.id
                stock_move_location_pick_line.is_pick_package_barcode = True
            else:
                list_line_pick.x_is_pick = False

        return {
            'name': _('Location Pick'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.location.pick',
            'res_id': self.pick_location_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('z_stock_picking.stock_move_location_pick_view').id,
            'target': 'new',
        }
