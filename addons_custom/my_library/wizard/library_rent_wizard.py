from odoo import models, api, fields


class LibraryRentWizard(models.TransientModel):
    _name = "library.rent.wizard"
    borrower_id = fields.Many2one("res.partner", string="Borrower")
    book_ids = fields.Many2many("library.book", string="Books")

    def add_book_rents(self):
        rent = self.env["library.book.rent"]
        for wiz in self:
            for book in wiz.book_ids:
                rent.create({
                    "borrower_id": wiz.borrower_id.id,
                    "book_id": book.id,
                })
