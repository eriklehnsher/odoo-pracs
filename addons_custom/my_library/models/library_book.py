from odoo import models, fields, api


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    #to sort the records first-from the newest to the oldest + then by title
    _order = 'date_release desc, name'
    #to use the short_name field as the record representation - ở đây là để hiển thị tên ngắn của sách
    _rec_name = 'short_name'
    
    short_name = fields.Char('Short Title', required=True)
    name = fields.Char('Title', required=True)
    date_release = fields.Date('Release Date')
    author_ids = fields.Many2many('res.partner', string='Author')

