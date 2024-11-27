from odoo import models, fields, api
    
    
class Warehouse(models.Model):
        _inherit = 'stock.warehouse'
        inventory_adjustment_ids = fields.One2many('inventory.adjustment', 'warehouse_id', string='Kiểm kê')
