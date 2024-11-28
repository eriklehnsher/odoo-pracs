# -*- coding: utf-8 -*-

from odoo import models, fields


class ErpHrDepartment(models.Model):
    _name = 'erp.hr.department'
    _description = 'Bộ phận/Phòng ban'

    name = fields.Char(string='Tên', required=True)
    active = fields.Boolean(default=True)
    erp_hr_department_id = fields.Integer('ERP ID')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    code = fields.Char(string='Document Code', required=True)
    description = fields.Char(string='Diễn giải')
