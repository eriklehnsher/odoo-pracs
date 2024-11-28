# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class StockQuantPackage(models.Model):
    _name = 'stock.quant.package'
    _inherit = ['stock.quant.package', 'mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('stock_quant_package_name_uniq', 'UNIQUE(name)', _('The package code must be unique in the system.')),
        ('stock_quant_package_barcode_uniq', 'UNIQUE(barcode)', _('The package barcode must be unique in the system.')),
    ]

    name = fields.Char('Package Reference', copy=False, index='trigram', required=True, default=_('New'))
    barcode = fields.Char(string='Barcode', store=True, related='name', index=True)
    location_id = fields.Many2one('stock.location', string='Location', index=True, readonly=False)
    state = fields.Selection([
        ('draft', _('Draft')),
        ('ready', _('Ready')),
        ('full', _('Full')),
        ('done', _('Done')),
        ('deactive', _('Deactive')),
        ('cancel', _('Cancel')),
    ], string=_('State'), default='draft')
    brand_segment_id = fields.Many2one('erp.brand.segment', string='Thương hiệu sản phẩm')
    partner_id = fields.Many2one('res.partner', _('Partner'))
    active = fields.Boolean(string=_('Active'), default=True)
    length = fields.Float(string='Length', digits=(12, 2), default=0)
    width = fields.Float(string='Width', digits=(12, 2), default=0)
    height = fields.Float(string='Height', digits=(12, 2), default=0)
    uom_id = fields.Many2one('uom.uom', string=_('Uom Volume'))
    volume = fields.Float(string='Volume', digits=(12, 3), compute='_compute_volume', store=True)
    actual_volume = fields.Float(string='Actual Volume', digits=(12, 3))

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for item in self:
            item.volume = item.length * item.width * item.height

    def action_ready(self):
        if self.state == 'draft':
            self.state = 'ready'
            if self.location_id.actual_volume < self.volume:
                raise UserError('Thể tích còn lại của vị trí không đủ để chứa thùng này!')
            else:
                self.location_id.actual_volume -= self.volume

    def action_deactivate(self):
        self.state = 'deactive'

    @api.model_create_multi
    def create(self, vals_list):
        for item in vals_list:
            product_brand = self.env['erp.brand.segment'].sudo().search([('id', '=', item['brand_segment_id'])])
            sequence_code = f"tracking.stock.quant.package.{product_brand.code}"
            sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)
            if not sequence:
                self.env['ir.sequence'].sudo().create({
                    'name': f"Sequence for {product_brand.code}",
                    'code': sequence_code,
                    'prefix': f"T.{product_brand.code}",
                    'padding': 4,
                    'implementation': 'no_gap',
                })
            seq = self.env['ir.sequence'].next_by_code(sequence_code=sequence_code)
            item['name'] = seq
        res = super(StockQuantPackage, self).create(vals_list)
        for item in res:
            item.actual_volume = item.height * item.width * item.length
        return res

    def write(self, vals):
        if 'brand_segment_id' in vals and vals['brand_segment_id']:
            product_brand = self.env['erp.brand.segment'].sudo().search([('id', '=', vals['brand_segment_id'])])
            sequence_code = f"tracking.stock.quant.package.{product_brand.code}"
            sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)

            if not sequence:
                self.env['ir.sequence'].sudo().create({
                    'name': f"Sequence for {product_brand.code}",
                    'code': sequence_code,
                    'prefix': f"T.{product_brand.code}",
                    'padding': 4,
                    'implementation': 'no_gap',
                })
            seq = self.env['ir.sequence'].next_by_code(sequence_code=sequence_code)
            vals['name'] = seq

        if self.state == 'draft':
            height = self.height
            width = self.width
            length = self.length
            if 'height' in vals and vals['height']:
                height = vals['height']
            elif 'width' in vals and vals['width']:
                width = vals['width']
            elif 'length' in vals and vals['length']:
                length = vals['length']
            vals['actual_volume'] = length * width * height
        if self.state != 'draft' and 'actual_volume' in vals and vals['actual_volume']:
            if vals['actual_volume'] >= self.volume:
                vals['state'] = 'full'
        return super(StockQuantPackage, self).write(vals)
