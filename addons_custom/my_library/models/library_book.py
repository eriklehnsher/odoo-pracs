from odoo import models, fields, api
from datetime import timedelta


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    # to sort the records first-from the newest to the oldest + then by title
    _order = 'date_release desc, name'
    # to use the short_name field as the record representation - ở đây là để hiển thị tên ngắn của sách
    _rec_name = 'short_name'

    short_name = fields.Char('Short Title', required=True)
    name = fields.Char('Title', required=True)

    notes = fields.Text('Internal Notes')
    state = fields.Selection(
        [
            ('draft', 'Not Available'),
            ('available', 'Available'),
            ('lost', 'Lost')
        ], 'State')
    description = fields.Html('Description')
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print?')
    date_release = fields.Date('Release Date')
    pages = fields.Integer('Number of Pages')
    date_updated = fields.Datetime('Last Updated')
    reader_rating = fields.Float('Reader Average Rating', (14,
                                                           4))  # - trung bình đánh giá của người đọc( 14 digits in total, 4 after the decimal point - số lượng chữ số sau dấu phẩy là 4 chữ số sau dấu phẩy)
    author_ids = fields.Many2many('res.partner', 'library_book_res_partner_rel', string='Author')
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price', currency_field='currency_id')
    publisher_id = fields.Many2one('res.partner', string='Publisher')
    category_id = fields.Many2one('library.book.category', string='Category')
    age_days = fields.Float(string='Days Since Release', compute='_compute_age', inverse='_inverse_age',
                            search='_search_age', store=False, compute_sudo=True)
    publisher_city = fields.Char('Publisher City', related='publisher_id.city', related_sudo=True, readonly=True)
    ref_doc_id = fields.Reference(selection='_referenceable_models', string='Reference Document')
    @api.depends('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delte = today - book.date_release
                book.age_days = delte.days
            else:
                book.age_days = 0

    def inverse(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            book.date_release = today - timedelta(days=book.age_days)

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        value_date_str = value_date.strftime('%Y-%m-%d')
        operator_map = {
            '>': '<',
            '>=': '<=',
            '<': '>',
            '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date_str)]
        # Tính linh hoạt của search:
        # Hàm search cho phép bạn định nghĩa cách tìm kiếm trong các trường tính toán,
        # điều này đặc biệt hữu ích nếu bạn muốn tìm kiếm sách theo số ngày đã phát hành.
        # Trong ví dụ trên, phương thức search_age giúp chuyển đổi tìm kiếm số ngày thành tìm kiếm ngày phát hành thực tế.

    def name_get(self):
        result = []
        for record in self:
            rec_name = "%s (%s)" % (record.name, record.date_release or "N/A")
            result.append((record.id, rec_name))
        return result

    def _referenceable_models(self):
        models = self.env['ir.model'].search([
            ('field_id.name', '=', 'message_ids')
        ])
        return [(x.model, x.name) for x in models]


class ResPartner(models.Model):
    _inherit = 'res.partner'
    published_book_ids = fields.One2many('library.book', 'publisher_id', string='Published Books')
    book_ids = fields.One2many('library.book', 'publisher_id', string='Published Books')
    authored_book_ids = fields.Many2many(
        'library.book',
        string='Authored Books',
        # optional
    )
