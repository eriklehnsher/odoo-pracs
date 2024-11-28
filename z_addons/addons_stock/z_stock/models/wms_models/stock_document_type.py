# -*- coding: utf-8 -*-

from odoo import models, fields


class StockDocument(models.Model):
    _name = 'stock.document.type'
    _description = 'Stock Document Type'

    name = fields.Char(string='Document Name', required=True)
    active = fields.Boolean(default=True)
    erp_document_type_id = fields.Integer('ERP ID')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    code = fields.Char(string='Document Code')
    description = fields.Char(string='Description')
