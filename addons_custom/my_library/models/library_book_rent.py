from odoo import models, api, fields
from odoo.exceptions import UserError


class LibraryBookRent(models.Model):
    _name = "library.book.rent"
    _description = "Library Book Rent"

    book_id = fields.Many2one("library.book", string="Book")
    borrower_id = fields.Many2one("res.partner", string="Borrower")
    state = fields.Selection(
        [
            ("ongoing", "Ongoing"),
            ("returned", "returned"),
            ("lost", "lost"),
        ],
        "state",
        default="ongoing",
        required=True,
    )
    rent_date = fields.Date("Rent Date", default=fields.Date.today)
    return_date = fields.Date("Return Date")

    def book_lost(self):
        self.sudo().state = "lost"
        self.book_id.make_lost()
