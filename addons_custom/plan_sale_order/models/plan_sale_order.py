from odoo import models, fields, api


class PlanSaleOrder(models.Model):
    _name = 'plan.sale.order'
    _description = 'Plan Sale Order'

    name = fields.Char(string='Tên Phương Án', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Mẫu Báo Giá', readonly=True)
    plan_sale_order_info = fields.Text(string='Plan Information', required=True)
    approver_ids = fields.Many2many('res.partner', string='Người Phê Duyệt')
