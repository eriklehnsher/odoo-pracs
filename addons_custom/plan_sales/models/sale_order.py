from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    plan_sale_order_id = fields.Many2one('plan.sale.order', string='Phương Án Kinh Doanh')


    def action_create_plan_sale_order(self):
        self.ensure_one()
        plan_sale_order = self.env['plan.sale.order'].create({
            'name': 'Kế Hoạch bán hàng cho đơn hàng' + self.name,
            'sale_order_id': self.id,
            'plan_sale_order_info': 'Nội dung chi tiết ...',
        })
        self.plan_sale_order_id = plan_sale_order.id
        return {
            'name': 'Plan Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'plan.sale.order',
            'res_id': plan_sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }