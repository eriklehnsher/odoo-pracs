from odoo import models, fields
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_cancel_picking_done(self):
        self.ensure_one()
        self._adjust_product_qty_by_stock_quant()
        self.write({'is_locked': True, 'state': 'cancel'})

    def _adjust_product_qty_by_stock_quant(self):
        '''
            Khi hủy điều chuyển, sử dụng chức năng chỉnh sửa tồn kho của sản phẩm (update quantity on hand)
            để cập nhật lại số lượng tồn kho chuẩn
            Đối với điều chuyển nội bộ: điều chỉnh lại số lượng tồn kho của sản phẩm tại địa điểm đích và
            địa điểm nguồn ( tăng tồn ở địa điểm nguồn và giảm tồn ở địa điểm đích)
        '''
        self.ensure_one()
        for move in self.move_ids_without_package.filtered(lambda m: m.state == 'done'):
            for line in move.move_line_ids.filtered(lambda l: l.state == 'done'):
                if line.location_id.usage == 'internal':
                    quant_val_to_create = {
                        'product_id': line.product_id.id,
                        'location_id': line.location_id.id,
                        'inventory_quantity': line.qty_done,
                        'inventory_date': fields.Date.today()
                    }
                    quant_domain = [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id)]
                    if line.package_id:
                        quant_domain.append(('package_id', '=', line.package_id.id))
                        quant_val_to_create['package_id'] = line.package_id.id
                    if line.lot_id:
                        quant_domain.append(('lot_id', '=', line.lot_id.id))
                        quant_val_to_create['lot_id'] = line.lot_id.id
                    stock_quant = self.env['stock.quant'].search(quant_domain, limit=1)
                    if stock_quant:
                        current_qty = stock_quant.quantity
                        stock_quant.inventory_quantity = current_qty + line.qty_done
                        stock_quant.action_apply_inventory()
                    else:
                        self.env['stock.quant'].create(quant_val_to_create).action_apply_inventory()
                if line.location_dest_id.usage == 'internal':
                    quant_domain = [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_dest_id.id)]
                    if line.result_package_id:
                        quant_domain.append(('package_id', '=', line.result_package_id.id))
                    if line.lot_id:
                        quant_domain.append(('lot_id', '=', line.lot_id.id))
                    stock_quant = self.env['stock.quant'].search(quant_domain, limit=1)
                    if stock_quant:
                        qty_to_update = stock_quant.quantity - line.qty_done
                        if qty_to_update >= 0:
                            stock_quant.inventory_quantity = qty_to_update
                            stock_quant.action_apply_inventory()
                        else:
                            raise UserError('Tồn của sản phẩm: ' + line.product_id.name + ' sau khi trừ đi số lượng đã nhập tại địa điểm: ' + line.location_dest_id.complete_name + ' bị âm. Vui lòng kiểm tra lại!')
                    else:
                        raise UserError('Tồn của sản phẩm: ' + line.product_id.name + ' tại địa điểm: ' + line.location_dest_id.complete_name + ' bằng 0 nên không thể điều chỉnh trừ đi số lượng đã nhập. Vui lòng kiểm tra lại!')
