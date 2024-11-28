# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from io import BytesIO
from xlsxwriter.workbook import Workbook
from datetime import datetime
import base64
import xlrd


class StockMoveLocationPick(models.Model):
    _name = 'stock.move.location.pick'
    _description = 'Stock move pick location'

    picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    can_edit = fields.Boolean(string='Can Edit', default=True)
    type = fields.Selection([
        ('pick_in', 'Pick In'),
        ('pick_out', 'Pick Out'),
    ], string='Pick Type')
    move_location_pick_ids = fields.One2many('stock.move.location.pick.line', 'move_location_pick_id', string='Lines')
    file_binary = fields.Binary(string="Upload File")
    file_binary_name = fields.Char()

    def action_pick_location(self):
        if self.move_location_pick_ids.filtered(lambda x: not x.location_id):
            raise ValidationError(
                _('Not enough locations have been declared for the product. Please declare enough import/export warehouse locations for the product!'))
        for item in self.move_location_pick_ids:
            stock_move = item.move_id
            if stock_move:
                stock_move._do_unreserve()
            if item.package_id and item.package_id.state == 'draft':
                raise ValidationError(_('Package cannot be draft!'))

    def action_return_default(self):
        for item in self.move_location_pick_ids:
            item._default_location_pick()
            item._default_package_pick()
            return {
                'name': _('Location Pick Out'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.move.location.pick',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': self.env.ref('z_stock_picking.stock_move_location_pick_view').id,
                'target': 'new',
            }

    def action_download(self):
        data_file = self.generate_xlsx_location_pick()
        vals = {
            'datas': data_file,
            'name': _('Import location') + '.xlsx',
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
        }
        file_xls = self.env['ir.attachment'].create(vals)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(file_xls.id) + '?download=true',
            'target': 'new',
        }

    def generate_xlsx_location_pick(self):
        buf = BytesIO()
        wb = Workbook(buf)
        ws = wb.add_worksheet('Pick Location')
        wb.formats[0].font_name = 'Times New Roman'
        wb.formats[0].font_size = 11
        ws.set_paper(9)
        ws.center_horizontally()
        ws.set_margins(left=0.28, right=0.28, top=0.5, bottom=0.5)
        ws.fit_to_pages(1, 0)
        ws.set_landscape()
        table_row_right = wb.add_format({
            'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'font_name': 'Times New Roman',
        })
        table_header = wb.add_format({
            'bold': 1, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_name': 'Times New Roman', 'fg_color': '#e0e0e0'
        })
        row_date_default = wb.add_format({
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Times New Roman',
            'font_size': 11,
            'num_format': 'dd-mm-yyyy'
        })
        ws.set_column(0, 0, 20)
        ws.set_column(1, 1, 30)
        ws.set_column(2, 2, 20)
        ws.set_column(3, 3, 20)
        ws.set_column(4, 4, 20)
        ws.set_column(5, 5, 20)
        ws.set_column(6, 6, 20)
        ws.set_column(7, 7, 20)
        ws.set_column(8, 8, 20)
        ws.set_column(9, 9, 20)
        ws.write("A1", _('Product Code'), table_header)
        ws.write("B1", _('Product'), table_header)
        if self.type == 'pick_in':
            ws.write("C1", _('Is Created New Package (Input True/False)'), table_header)
        else:
            ws.write("C1", _('Is Out Of Package (Input True/False)'), table_header)
        ws.write("D1", _('Barcode'), table_header)
        ws.write("E1", _('Quantity'), table_header)
        ws.write("F1", _('Package (Input barcode package)'), table_header)
        ws.write("G1", _('Uom'), table_header)
        ws.write("H1", _('Location (Input barcode location)'), table_header)
        ws.write("I1", _('Expired Date'), table_header)
        ws.write("J1", _('Line ID'), table_header)

        row = 2
        for item in self.move_location_pick_ids:
            ws.write("A{row}".format(row=row), item.default_code or '', table_row_right)
            ws.write("B{row}".format(row=row), item.product_id.display_name or '', table_row_right)
            if self.type == 'pick_in':
                ws.write("C{row}".format(row=row), 1 if item.is_create_new_package else 0, table_row_right)
            else:
                ws.write("C{row}".format(row=row), 1 if item.is_out_of_package else 0, table_row_right)
            ws.write("D{row}".format(row=row), item.barcode or '', table_row_right)
            ws.write("E{row}".format(row=row), item.quantity or '', table_row_right)
            ws.write("F{row}".format(row=row), item.package_id.name or '', table_row_right)
            ws.write("G{row}".format(row=row), item.uom_id.name or '', table_row_right)
            ws.write("H{row}".format(row=row), item.location_id.barcode or '', table_row_right)
            ws.write("I{row}".format(row=row), item.expired_date.strftime('%d/%m/%Y') if item.expired_date else '',
                     row_date_default)
            ws.write("J{row}".format(row=row), item.id, table_row_right)
            row += 1
        wb.close()
        buf.seek(0)
        xlsx_data = buf.getvalue()
        data = base64.encodebytes(xlsx_data)
        return data

    def action_import_location_pick(self):
        try:
            if not self._check_format_excel(self.file_binary_name):
                raise UserError(_('File import is not valid.'))
            data = base64.decodebytes(self.file_binary)
            excel = xlrd.open_workbook(file_contents=data)
            sheet = excel.sheet_by_index(0)
            index = 1
            vals = []
            while index < sheet.nrows:
                default_code = sheet.cell(index, 0).value
                is_create_new_package = True if int(sheet.cell(index, 2).value) == 1 else False
                is_out_of_package = True if int(sheet.cell(index, 2).value) == 1 else False
                barcode = sheet.cell(index, 3).value
                qty = int(sheet.cell(index, 4).value)
                barcode_package = sheet.cell(index, 5).value
                uom_name = sheet.cell(index, 6).value
                barcode_location = sheet.cell(index, 7).value
                expired_date = datetime.strptime(sheet.cell(index, 8).value, '%d-%m-%Y') if sheet.cell(index,
                                                                                                       8).value else False
                product_id = self.env['product.product'].search([('default_code', '=', default_code)]).id
                line_id = int(sheet.cell(index, 9).value)
                val = {
                    'default_code': default_code,
                    'product_id': product_id,
                    'barcode': barcode,
                    'quantity': qty,
                    'package_id': self.env['stock.quant.package'].search([('barcode', '=', barcode_package)]).id,
                    'uom_id': self.env['uom.uom'].search([('name', '=', uom_name)]).id,
                    'location_id': self.env['stock.location'].search([('barcode', '=', barcode_location)]).id,
                    'expired_date': expired_date,
                }
                if self.type == 'pick_in':
                    val['is_create_new_package'] = is_create_new_package
                else:
                    val['is_out_of_package'] = is_out_of_package
                if line_id:
                    line_pick = self.move_location_pick_ids.filtered(lambda x: x.id == line_id)
                    if line_pick.move_location_pick_id.id == self.id:
                        line_pick.write(val)
                    else:
                        raise UserError(_('Line ID is invalid'))
                index += 1
            return {
                'name': _('Location Pick In'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.move.location.pick',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': self.env.ref('z_stock_picking.stock_move_location_pick_view').id,
                'target': 'new',
            }
        except Exception as ex:
            raise UserError(ex)

    def _check_format_excel(self, file_name):
        if file_name == False:
            return False
        if file_name.endswith('.xls') or file_name.endswith('.xlsx'):
            return True
        return False
