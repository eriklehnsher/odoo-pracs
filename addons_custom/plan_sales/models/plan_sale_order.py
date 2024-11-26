from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import UserError

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
        current_user = self.env.user.partner_id
        if current_user in self.approver_ids and current_user not in self.approved_by_ids:
            self.approved_by_ids = [(4, current_user.id)]
            remaining_approvers = self.approver_ids - self.approved_by_ids
            self.message_post(
                body=f" Người Phê Duyệt {current_user.name} đã phê duyệt phương án kinh doanh",
                message_type='notification',
                partner_ids = [current_user.id]
            )
            if len(self.approved_by_ids) == len(self.approver_ids):
                self.state = 'approved'
                self.message_post(
                    body=f"Phương Án Kinh Doanh đã được tất cả phê duyệt",
                    message_type='notification',
                    partner_ids = [self.creator_id.partner_id.id]
                )
            else:
                self.state = 'pending'
                remaining_name = ', '.join([approver.name for approver in remaining_approvers])
                self.message_post(
                    body=f"Chờ phê duyệt từ {remaining_name}",
                    message_type='notification',
                    partner_ids = [remaining_approvers.ids]
                )
        else:
            raise UserError('Bạn không có quyền phê duyệt phương án này')





    def action_reject_plan_sale_order(self):
        current_user = self.env.user.partner_id
        if current_user in self.approver_ids and current_user not in self.rejected_by_ids:
            self.rejected_by_ids = [(4, current_user.id)]
            remaining_rejectors = self.approver_ids - self.rejected_by_ids
            self.state = "rejected"
            self.message_post(
                body=f"Người phê duyệt {current_user.name} đã từ chối kế hoạch.",
                message_type="notification",
                partner_ids=[current_user.id]
            )
            if len(self.rejected_by_ids) == len(self.approver_ids):
                self.state = "rejected"
                self.message_post(
                    body="Kế hoạch đã được tất cả người phê duyệt từ chối.",
                    message_type="notification",
                    partner_ids=[self.creater_id.partner_id.id]
                )
            else:
                self.state = "pending"
                remaining_names = ", ".join(
                    [rejector.name for rejector in remaining_rejectors])
                self.message_post(
                    body=f"Kế hoạch đã bị từ chối bởi {current_user.name}. Đang chờ {remaining_names} .",
                    message_type="notification",
                    partner_ids=[self.creater_id.partner_id.id]
                )
        else:
            raise UserError("Người phê duyệt không hợp lệ hoặc đã từ chối.")

    def action_sent_for_approval(self):
        if not self.approver_ids:
            raise UserError("Vui lòng chọn người phê duyệt")
        self.state = "pending"

        for approver in self.approver_ids:
            self.message_post(
                body="Kế hoạch đã được gửi phê duyệt.",
                message_type="notification",
                partner_ids=[approver.id],
            )
        return True