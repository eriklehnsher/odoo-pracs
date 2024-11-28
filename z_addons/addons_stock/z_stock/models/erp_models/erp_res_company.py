# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _name = 'erp.res.company'
    _description = 'Erp Company'
    _rec_name = 'erp_org_name'

    erp_client_id = fields.Integer(string='Client ID')
    erp_client_name = fields.Char(string='Name')
    erp_org_id = fields.Integer(string='Organization ID')
    erp_org_code = fields.Char(string='Organization Code')
    erp_org_name = fields.Char(string='Organization Name')
    erp_org_address = fields.Char(string='Organization Address')
    erp_tax_code = fields.Char(string='Tax Code')
    erp_phone = fields.Char(string='Phone Number')
    erp_fax = fields.Char(string='Fax Number')
    erp_email = fields.Char(string='Email Address')
    erp_is_active = fields.Boolean(string='Active')
    erp_created_at = fields.Datetime(string='Created At')
    erp_updated_at = fields.Datetime(string='Updated At')
