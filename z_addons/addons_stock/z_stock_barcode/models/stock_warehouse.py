# -*- coding: utf-8 -*-

from odoo import models, fields, _
import base64
from reportlab.graphics.barcode import createBarcodeDrawing


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_ho_warehouse = fields.Boolean(string='Is HO Warehouse', default=False)
