# -*- coding: utf-8 -*-

from odoo import models, fields, api
from unidecode import unidecode


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    _sql_constraints = [
        ('uniq_barcode', 'unique(barcode)', 'Barcodes on each warehouse must be unique.'),
    ]

    erp_client_id = fields.Integer(string='Client ID')
    erp_org_id = fields.Integer(string='Organization ID')
    erp_location_id = fields.Integer(string='Location ID')
    erp_warehouse_id = fields.Integer(string='Warehouse ID')
    erp_created_at = fields.Datetime(string='Created At')
    erp_updated_at = fields.Datetime(string='Updated At')
    barcode = fields.Char(string='Barcode', compute='_compute_barcode', store=True)
    # Code đồng bộ về lớn hơn 5 ký tự => khai báo lại code
    code = fields.Char('Short Name', required=True, size=15, help="Short name used to identify your warehouse")
    erp_res_company_id = fields.Many2one('erp.res.company', string='Organization')

    @api.depends('code', 'name')
    def _compute_barcode(self):
        for item in self:
            item.barcode = unidecode(item.code or '/' + '-' + item.name.replace(' ', '-')).upper()
