from odoo import models, fields, api
from odoo.exceptions import UserError


class PlanSaleOrder(models.Model):
    _name = "plan.sale.order"
    _description = "Sale Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Tiêu đề", required=True)  # tiêu đề của kế hoạch
    approver_ids = fields.Many2many('res.partner', string='Người phê duyệt')  # người phê duyệt
    sale_order_id = fields.Many2one(
        "sale.order", string="Mẫu báo giá", readonly=True
    )  # mẫu báo giá
    plan_sale_order_info = fields.Text(
        string="Thông tin kế hoạch", required=True
    )  # thông tin kế hoạch
    state = fields.Selection(
        [  ("draft", "Nháp"),
            ('pending', 'Chờ xác nhận'),
           
            ("approved", "Duyệt Kế hoạch"),
            ("rejected", "Từ chối"),
        ],
        string="Trạng thái",
        default="draft",
    )
    created_at = fields.Datetime(string="Ngày tạo", default=fields.Datetime.now)
    # ngày tạo
    updated_at = fields.Datetime(string="Ngày cập nhật", default=fields.Datetime.now)
    def action_confirm(self):
        for rec in self:
            rec.state = "approved"
            rec.message_post(body=f"Kế hoạch đã được duyệt", message_type="notification")
            return True
        
    def action_cancel(self):
        for rec in self:
            rec.state = "rejected"
            rec.message_post(body=f"Kế hoạch đã bị từ chối", message_type="notification")
            return True
        
    def action_sent_for_approval(self):
        if not self.approver_ids:
            raise UserError("Vui lòng chọn người phê duyệt")
        self.state = "pending"
  
        for approver in self.approver_ids:
            self.message_post(
                body=f"Kế hoạch đã được gửi phê duyệt",
                message_type="notification",
                partner_ids=[approver.id],
            )
        return True

