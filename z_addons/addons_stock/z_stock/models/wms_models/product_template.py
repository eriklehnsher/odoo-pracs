# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    erp_product_attribute_set_id = fields.Many2one('erp.product.attribute.set', string='Product Attribute Set')
    erp_product_template_id = fields.Integer(string='ERP Product Template ID', index=True)
    erp_client_id = fields.Integer(string='ERP Client ID')
    erp_tax_id = fields.Many2one('erp.account.tax', string='Tax')
    erp_org_id = fields.Integer(string='ERP Organization ID')
    erp_default_code = fields.Char(string='ERP Default Code')
    erp_is_stocked = fields.Boolean(string='ERP IsStocked')
    erp_is_discontinued = fields.Boolean(string='ERP IsDiscontinued')
    product_brand_id = fields.Many2one('product.brand', string='Product Brand')
    brand_segment_id = fields.Many2one('erp.brand.segment', string='Thương hiệu sản phẩm')
    product_gender_id = fields.Many2one('product.gender', string='Product Gender')
    product_line_id = fields.Many2one('product.line', string='Product Line')
    erp_product_fullname = fields.Char(string='Tên đầy đủ (ERP)')
    erp_product_name_eng = fields.Char(string='Tên tiếng anh (ERP)')
    erp_created_at = fields.Datetime(string='ERP Created At')
    erp_updated_at = fields.Datetime(string='ERP Updated At')
    erp_verdor_product_no = fields.Char(string='ERP Verdor Product No')
    erp_vendor_code = fields.Char(string='ERP Vendor Code')
    erp_verdor_cate1 = fields.Char(string='ERP Vendor Cate1')
    erp_vendor_cate2 = fields.Char(string='ERP Vendor Cate2')
    erp_vendor_cate3 = fields.Char(string='ERP Vendor Cate3')
    erp_dcs_code = fields.Char(string='ERP DCS Code')
    sub_categ_id = fields.Many2one('product.category', 'Nhóm phụ')

    _sql_constraints = [
        ('uniq_erp_default_code', 'unique(erp_default_code)', 'ERP default code must be unique.'),
        ('uniq_erp_product_template_id', 'unique(erp_product_template_id)', 'ERP Product Template ID must be unique.'),
    ]

    # Tạo biến thể sản phẩm khi map product_tmpl_id và barcode_id, gắn barcode cho biến thể sản phẩm
    @api.model
    def action_init_product_product(self, default_code, barcode_id):
        erp_barcode = self.env['erp.barcode'].search([('erp_barcode_id', '=', int(barcode_id))])
        product_template = self.env['product.template'].search([('default_code', '=', default_code)])
        attr_val = []
        attribute_value_ids = []
        for item in erp_barcode.barcode_line_ids:
            if item.product_attribute_id and item.product_attribute_value_id and item.product_attribute_value_id.name != 'NA':
                attribute_value_ids.append(item.product_attribute_value_id.id)
                attribute_line = self.env['product.template.attribute.line'].search(
                    [
                        ('attribute_id', '=', item.product_attribute_id.id),
                        ('product_tmpl_id', '=', product_template.id)
                    ])
                if attribute_line:
                    attribute_line.value_ids = [(4, item.product_attribute_value_id.id)]
                else:
                    attr_val.append(
                        (0, 0, {
                            'attribute_id': item.product_attribute_id.id,
                            'value_ids': [(4, item.product_attribute_value_id.id)],
                        })
                    )
        product_template.write({
            'attribute_line_ids': attr_val
        })
        attribute_records = self.env['product.template.attribute.value'].search([
            ('product_attribute_value_id', 'in', attribute_value_ids),
            ('product_tmpl_id', '=', product_template.id),
        ]).ids
        product = self.env['product.template'].search([('id', '=', product_template.id)]).product_variant_ids.filtered(
            lambda x: x.product_template_attribute_value_ids.ids == attribute_records)
        if product:
            product.barcode = erp_barcode.erp_barcode_value
