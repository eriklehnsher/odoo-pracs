# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMoveLocationPickLine(models.Model):
    _name = 'stock.move.location.pick.line'
    _description = 'Stock move pick location line'
    _order = 'id asc'

    move_id = fields.Many2one('stock.move', string='Stock Move', ondelete='cascade')
    is_out_of_package = fields.Boolean(string='Is Out Of Package')
    is_create_new_package = fields.Boolean(string='Is Create New Package')
    default_code = fields.Char(string='Default Code')
    product_id = fields.Many2one('product.product', string='Product')
    barcode = fields.Char(string='Barcode', related='product_id.barcode')
    quantity = fields.Integer(string='Quantity')
    package_ids = fields.Many2many('stock.quant.package', string='Packages', compute='_compute_packages')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    location_id = fields.Many2one('stock.location', string='Location')
    expired_date = fields.Date(string='Expired Date')
    move_location_pick_id = fields.Many2one('stock.move.location.pick', string='Location Pick')
    is_created_package = fields.Boolean(string='Is Created Package', default=False)
    is_pick_package_barcode = fields.Boolean(string='Is Pick Package Barcode', default=False)
    location_out_ids = fields.Many2many('stock.location','location_out_rel', string='Locations', compute='_compute_locations')
    location_in_ids = fields.Many2many('stock.location','location_in_rel', string='Locations', compute='_compute_locations')

    @api.onchange('is_out_of_package')
    def _onchange_is_out_of_package(self):
        for item in self:
            if item.is_out_of_package:
                if item.package_id.quant_ids.filtered(lambda x: x.product_id == item.product_id).quantity > item.quantity:
                    raise UserError(_('Số lượng sản phẩm xuất đi không đủ để có thể xuất cả thùng!'))

    @api.onchange('is_create_new_package')
    def _onchange_is_create_new_package(self):
        for item in self:
            if item.is_create_new_package:
                if not item.product_id.brand_segment_id:
                    raise UserError('Sản phẩm chưa cấu hình thương hiệu. Không thể tạo thùng mới.')
                new_package = self.env['stock.quant.package'].create({
                    'location_id': item.location_id.id,
                    'brand_segment_id': item.product_id.brand_segment_id.id,
                })
                if new_package:
                    item.package_id = new_package.id

    @api.depends('product_id')
    def _compute_locations(self):
        for item in self:
            item.location_out_ids = None
            product_id = item.product_id.id
            warehouse_id = item.move_location_pick_id.picking_id.warehouse_id
            warehouse_dest_id = item.move_location_pick_id.picking_id.warehouse_dest_id
            stock_quant = self.env['stock.quant'].search([('product_id', '=', product_id), ('quantity', '>', 0)])
            if warehouse_id and stock_quant:
                item.location_out_ids = [(6, 0, stock_quant.location_id.filtered(
                    lambda l: l.usage == 'internal' and l.warehouse_id.erp_res_company_id.erp_org_code == warehouse_id.erp_res_company_id.erp_org_code).ids)]
            if warehouse_dest_id and stock_quant:
                item.location_in_ids = [(6, 0, stock_quant.location_id.filtered(
                    lambda l: l.usage == 'internal' and l.warehouse_id.erp_res_company_id.erp_org_code == warehouse_dest_id.erp_res_company_id.erp_org_code).ids)]

    @api.depends('product_id', 'location_id')
    def _compute_packages(self):
        for item in self:
            item.package_ids = None
            if item.product_id:
                # Nếu nhập kho, lấy ra tất cả các thùng ở trạng thái ready, hoặc các thùng ready theo location
                if item.move_location_pick_id.type == 'pick_in':
                    domain_search = [
                        ('state', '=', 'ready'),
                    ]
                    if item.location_id:
                        domain_search.append('|')
                        domain_search.append(('location_id', '=', item.location_id.id))
                        domain_search.append(('location_id', '=', None))
                    packages = self.env['stock.quant.package'].search(domain_search).ids
                    item.package_ids = [(6, 0, packages)]
                # Nếu xuất kho lấy ra tất cả các thùng còn hàng từ stock.quant, hoặc theo location từ stock.quant
                elif item.move_location_pick_id.type == 'pick_out':
                    domain_search = [
                        ('product_id', '=', item.product_id.id),
                    ]
                    if item.location_id:
                        domain_search.append(('location_id', '=', item.location_id.id))
                    packages = self.env['stock.quant'].search(domain_search).package_id.filtered(
                        lambda p: p.state == 'ready')
                    item.package_ids = [(6, 0, packages.ids)] if packages else None

    def _default_location_pick(self):
        # Gợi ý pick vị trí nhập kho
        for item in self:
            if item.move_location_pick_id.type == 'pick_in':
                stock_warehouse = self.env['stock.warehouse'].search([('is_ho_warehouse', '=', True)], order='name asc')
                stock_location = self.env['stock.location'].search(
                    [('warehouse_id', 'in', stock_warehouse.ids), ('usage', 'in', ('internal', 'transit'))])
                location_max_volumn = max(stock_location, key=lambda x: x.volume)
                item.location_id = location_max_volumn.id
            else:
                item.location_id = None

    def _default_package_pick(self):
        for item in self:
            if item.move_location_pick_id.type == 'pick_in':
                if item.location_id:
                    stock_quant_package = self.env['stock.quant.package'].search(
                        [('location_id', '=', item.location_id.id)])
                    if stock_quant_package:
                        max_package_volume = max(stock_quant_package, key=lambda x: x.volume)
                        if max_package_volume:
                            item.package_id = max_package_volume.id

    @api.onchange('location_id')
    def _onchange_location_id(self):
        for item in self:
            if item.move_location_pick_id.type == 'pick_in':
                item.move_location_pick_id.picking_id.pick_location_in = True

            if item.move_location_pick_id.type == 'pick_out':
                if item.location_id:
                    stock_quant = self.env['stock.quant'].search(
                        [('location_id', '=', item.location_id.id), ('product_id', '=', item.product_id.id)])
                    if stock_quant:
                        package_ready = stock_quant.package_id.filtered(lambda p: p.state == 'ready')
                        item.package_id = package_ready[0].id if package_ready else None

    @api.onchange('package_id')
    def _onchange_package_id(self):
        for item in self:
            if item.move_location_pick_id.type == 'pick_in':
                pass

            if item.move_location_pick_id.type == 'pick_out':
                if item.package_id:
                    stock_quant = self.env['stock.quant'].search(
                        [('package_id', '=', item.package_id.id), ('product_id', '=', item.product_id.id)])
                    locations = stock_quant.location_id
                    location_id = sorted(locations, key=lambda l: l.name)[0].id if locations else None
                    if location_id:
                        item.location_id = location_id

