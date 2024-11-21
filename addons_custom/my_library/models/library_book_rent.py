from Tools.scripts.dutree import store

from odoo import models, api, fields
from odoo.exceptions import UserError


class LibraryBookRent(models.Model):
    _name = "library.book.rent"
    _description = "Library Book Rent"

    book_id = fields.Many2one("library.book", string="Book")
    author_ids = fields.Many2many(
        "res.partner", string="Authors",   compute="_compute_author_ids",
        store=False,
    )
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



    @api.depends("book_id")
    def _compute_author_ids(self):
        for rec in self:
            rec.author_ids = rec.book_id.author_ids

    def book_lost(self):
        self.sudo().state = "lost"
        self.book_id.make_lost()

    def book_return(self):
        self.state = "returned"
        self.return_date = fields.Date.today()