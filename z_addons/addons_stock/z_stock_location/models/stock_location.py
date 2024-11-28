# -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    length = fields.Float(string='Length', digits=(12, 2), default=0)
    width = fields.Float(string='Width', digits=(12, 2), default=0)
    height = fields.Float(string='Height', digits=(12, 2), default=0)
    uom_id = fields.Many2one('uom.uom', string='UOM')
    volume = fields.Float(string='Volume', digits=(12, 3), compute='_compute_volume')
    actual_volume = fields.Float(string='Actual Volume', digits=(12, 3))

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for item in self:
            item.volume = item.length * item.width * item.height

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockLocation, self).create(vals_list)
        for item in res:
            item.actual_volume = item.height * item.width * item.length
        return res

    def write(self, vals):
        for item in self:
            if item.usage == 'internal':
                height = item.height
                width = item.width
                length = item.length
                flag = False
                if 'height' in vals and vals['height']:
                    flag = True
                    height = vals['height']
                elif 'width' in vals and vals['width']:
                    flag = True
                    width = vals['width']
                elif 'length' in vals and vals['length']:
                    flag = True
                    length = vals['length']
                if flag:
                    vals['actual_volume'] = length * width * height
        return super(StockLocation, self).write(vals)

    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        for location in self:
            if location.location_id:
                location.complete_name = '%s/%s' % (location.location_id.complete_name, location.name)
            else:
                location.complete_name = location.name
