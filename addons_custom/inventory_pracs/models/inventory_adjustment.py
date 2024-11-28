from email.policy import default

from odoo import models, fields, api


class InventoryAdjustment(models.Model):
    _name = 'inventory.adjustment'
    _description = 'Inventory Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Tên')
    inventory_adjustment_code = fields.Char(string='Mã Phiếu')
    state_date = fields.Datetime(
        'Ngày bắt đầu', default=fields.Datetime.now, tracking=True)
    end_date = fields.Datetime(
        'Ngày kết thúc',  default=fields.Datetime.now, tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho')
    company_id = fields.Many2one('res.company', string='Công ty')
    stock_take_manager = fields.Many2one('res.users', string='Trưởng ban kiểm kê')
    state = fields.Selection([
        ('draft', 'Bản nháp'),
        ('pending', 'chờ phê duyệt'),
        ('approved', 'đã phê duyệt'),
        ('rejected', 'từ chối phê duyệt'),
    ], string='Trạng thái', default='draft', tracking=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Loại chuyển kho')
    #define all the methods here

    def action_create_inventory_adjustment(self):
        inventory_adj = self.env['inventory.adjustment'].create({
            'name': self.name,
            'inventory_adjustment_code': self.inventory_adjustment_code,
            'state_date': self.state_date,
            'end_date': self.end_date,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'company_id': self.company_id.id if self.company_id else False,
            'stock_take_manager': self.stock_take_manager.id if self.stock_take_manager else False,
        })
        return {
            'name': 'Kiểm kê',
            'view_mode': 'form',
            'res_model': 'inventory.adjustment',
            'res_id': inventory_adj.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
    def action_request_approve(self):
        self.state = 'pending'
        head_of_stock_take = self.stock_take_manager
        self.message_post(
            body='Yêu cầu phê duyệt từ {}'.format(self.env.user.name),
            partner_ids=[head_of_stock_take.partner_id.id],
        )

    def action_approve(self):
        self.state = 'approved'
    def action_reject(self):
        self.state = 'rejected'
    def action_cancel(self):
        self.state = 'pending'