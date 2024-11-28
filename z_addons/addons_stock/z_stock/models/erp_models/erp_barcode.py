# -*- coding: utf-8 -*-

from odoo import models, fields


class ERPBarcode(models.Model):
    _name = 'erp.barcode'
    _description = 'ERP Barcode'
    _rec_name = 'erp_barcode_value'

    _sql_constraints = [
        ('uniq_erp_barcode_id', 'unique(erp_barcode_id)', 'ERP barcode ID must be unique.'),
        ('uniq_erp_barcode_value', 'unique(erp_barcode_value)', 'ERP barcode value must be unique.'),
    ]

    erp_client_id = fields.Integer(string='ERP Client ID')
    erp_org_id = fields.Integer(string='ERP Organization ID')
    erp_barcode_id = fields.Integer(string='ERP Barcode ID', index=True)
    erp_barcode_value = fields.Char(string='ERP Barcode Value', index=True)
    erp_serial = fields.Char(string='ERP Serial')
    erp_lot = fields.Char(string='ERP Lot')
    erp_ean_code = fields.Char(string='ERP EAN Code')
    barcode_line_ids = fields.One2many('erp.barcode.line', 'barcode_id', string='Barcode Lines')
    active = fields.Boolean(string='Active', default=True)
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
