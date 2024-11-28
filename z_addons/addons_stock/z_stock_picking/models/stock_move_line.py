# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        if 'state' in vals and vals['state'] == 'done':
            package_id = self.package_id
            result_package_id = self.result_package_id
            if package_id:
                pkg_actual_volume = (package_id.length * package_id.width * package_id.height) - self.product_id.volume
                package_id.actual_volume = pkg_actual_volume
            if result_package_id:
                pkg_res_actual_volume = (result_package_id.length * result_package_id.width * result_package_id.height) + self.product_id.volume
                result_package_id.actual_volume = pkg_res_actual_volume

            location_id = self.location_id
            location_dest_id = self.location_dest_id

            if location_id and location_id.usage in ('internal', 'transit'):
                location_actual_volume = (location_id.length * location_id.width * location_id.height) - self.package_id.volume
                location_id.actual_volume = location_actual_volume

            if location_dest_id and location_dest_id.usage in ('internal', 'transit'):
                location_actual_volume = (location_dest_id.length * location_dest_id.width * location_dest_id.height) + self.result_package_id.volume
                location_dest_id.actual_volume = location_actual_volume
        return res
