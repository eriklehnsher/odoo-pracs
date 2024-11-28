# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    erp_client_id = fields.Many2one('erp.res.company', string='Erp Company')
    erp_org_id = fields.Integer(string='Erp Org Id')
    erp_user_id = fields.Integer(string='Erp User Id', index=True)
    erp_created_at = fields.Datetime(string='Erp Created At')
    erp_updated_at = fields.Datetime(string='Erp Updated At')
    erp_user_code = fields.Char(string='Erp User Code')
