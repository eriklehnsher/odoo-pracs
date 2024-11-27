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
    
    
    