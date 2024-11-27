from odoo import models, fields, api


class InventoryAdjustment(models.Model):
    _name = 'inventory.adjustment'
    _description = 'Inventory Adjustment'
    
    
    name = fields.Char(string='Tên', required=True)
    inventory_adjustment_code = fields.Char(string='Mã Phiếu', required=True)
    state_date = fields.Date(string='Ngày bắt đầu', required=True)
    end_date = fields.Date(string='Ngày kết thúc', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True)
    stock_inventory_id = fields.Many2one('stock.inventory', string='Kiểm kê', required=True)
    company_id = fields.Many2one('res.company', string='Công ty', required=True)
    stock_take_manager = fields.Many2one('res.users', string='Trưởng ban kiểm kê', required=True)
    
    
    #define all the methods here

    def action_create_inventory_adjustment(self):

        inventory_adj = self.env['inventory.adjustment'].create({
            'name': self.name,
            'inventory_adjustment_code': self.inventory_adjustment_code,
            'state_date': self.state_date,
            'end_date': self.end_date,
            'warehouse_id': self.warehouse_id.id,
            'stock_inventory_id': self.stock_inventory_id.id,
            'company_id': self.company_id.id,
            'stock_take_manager': self.stock_take_manager.id,
        })

        return {
            'name': 'Kiểm kê',
            'view_mode': 'form',
            'res_model': 'inventory.adjustment',
            'res_id': inventory_adj.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_start(self):
        pass

    def action_validate(self):
        pass

    def action_cancel(self):
        pass