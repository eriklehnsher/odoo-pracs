from email.policy import default

from odoo import models, fields, api


class PlanSaleOrder(models.Model):
    _name = 'plan.sale.order'
    _description = 'Plan Sale Order'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Tên Phương Án', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Mẫu Báo Giá', readonly=True)
    plan_sale_order_info = fields.Text(string='Thông tin phương án kinh doanh', required=True)
    approver_ids = fields.Many2many('res.partner', string='Danh sách người phê duyệt')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending','Chờ phê duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái phê duyệt', default='draft')

    #create relation to save approvers approved
    approved_by_ids = fields.Many2many('res.partner', 'plan_sale_order_approved_by_rel', 'plan_sale_order_id', 'partner_id', string='Đã phê duyệt', readonly=True)

    #create relation to save approvers rejected
    rejected_by_ids = fields.Many2many('res.partner', 'plan_sale_order_rejected_by_rel', 'plan_sale_order_id', 'partner_id', string='Từ chối', readonly=True)

    created_at = fields.Char(string='Ngày tạo', default=fields.Datetime.now)
    updated_at = fields.Char(string='Ngày cập nhật', default=fields.Datetime.now)
    creator_id = fields.Many2one('res.partner', string='Người tạo', default=lambda self: self.env.user.partner_id)

    # all defined methods here

    def action_approve_plan_sale_order(self):
       pass

    def action_reject_plan_sale_order(self):
        pass

