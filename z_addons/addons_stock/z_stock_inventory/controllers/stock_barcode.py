# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController
from odoo.http import request


class StockBarcodeControllerInherit(StockBarcodeController):
    @http.route('/stock_barcode/get_barcode_data', type='json', auth='user')
    # Inherit /stock_barcode/controllers/stock_barcode.py
    # route: /stock_barcode/get_barcode_data
    def get_barcode_data(self, model, res_id, stock_inventory_id=None):
        if not res_id:
            target_record = request.env[model].with_context(allowed_company_ids=self._get_allowed_company_ids())
        else:
            target_record = request.env[model].browse(res_id).with_context(
                allowed_company_ids=self._get_allowed_company_ids())
        if stock_inventory_id:
            target_record.write({'stock_inventory_id': stock_inventory_id})
        data = target_record._get_stock_barcode_data()
        data['records'].update(self._get_barcode_nomenclature())
        data['precision'] = request.env['decimal.precision'].precision_get('Product Unit of Measure')
        mute_sound = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.mute_sound_notifications')
        config = {'play_sound': bool(not mute_sound or mute_sound == "False")}
        return {
            'data': data,
            'groups': self._get_groups_data(),
            'config': config,
        }
