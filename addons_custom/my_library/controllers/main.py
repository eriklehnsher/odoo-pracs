from odoo import http
from odoo.http import request

class Main(http.Controller):
    @http.route('/my_library/books', type='http', auth='none')
    def  all_book(self):
        books = request.env['library.boom'].sudo().search([])
        html_result = '<html><body><ul>'
        for book in books:
            html_result += "<li>%s</li>" % book.name
        html_result += '</ul></body></html>'
        return html_result

    @http.route('/my_library/books/json', type='json',
                auth='none')
    def books_json(self):
        records = request.env['library.book'].sudo().search([])
        return records.read(['name'])

    @http.route('/my_library/all-books/mark-mine', type='json', auth='public')
    def all_books_mark_mine(self):
        books = request.env['library.book'].sudo().search([])
        html_result = '<html><body><ul>'
        for book in books:
            if request.env.user.partner_id.id in book.author_ids.ids:
                html_result += "<li> <br>%s</br> </li>" % book.name  # neu user login la author of this book thi ten sach se dc in dam
            else:
                html_result += "<li> %s </li>" % book.name
        html_result += '</ul></body></html>'
        return html_result

    @http.route('/my_library/all-books/mine', type='json', auth='user')
    def all_books_mine(self):
        books = request.env['library.book'].search([
            ('author_ids', 'in', request.env.user.partner_id.ids),
        ])
        html_result = '<html><body><ul>'
        for book in books:
            html_result += "<li> %s </li>" % book.name
        html_result += '</ul></body></html>'
        return html_result

