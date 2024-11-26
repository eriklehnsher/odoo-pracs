from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    reason = fields.Text(string='Lý do nhập kho', required=True)

    @api.model

    def action_done(self):
        for move in self.move_lines:
            if move.quantity_done > move.product_uom_qty:
                raise UserError('Số lượng hoàn thành không được lớn hơn số lượng yêu cầu')
        return super(StockPicking, self).action_done()