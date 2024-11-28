# -*- coding: utf-8 -*-

from odoo import models, fields


class ErpBrandSegment(models.Model):
    _name = 'erp.brand.segment'
    _description = 'Thương hiệu sản phẩm'
    _rec_name = 'name'

    erp_id = fields.Integer(string='ERP ID')
    code = fields.Char(string='Code')
    name = fields.Char(string='Tên')
    active = fields.Boolean(string='Active', default=True)
