from odoo import models, api, fields


class LibraryReturnWizard(models.Model):
    _name = "library.return.wizard"

    book_ids = fields.Many2many("library.book", string="Book", compute="onchange_member")
    borrower_id = fields.Many2one("res.partner", string="Borrower")

    def books_returns(self):
        loanmodal = self.env["library.book.rent"]
        for rec in self:
            loans = loanmodal.search(
                [("state",'=','ongoing'),('book_id','=',rec.book_ids.ids),('borrower_id','=',rec.borrower_id.id)]
            )
            for loan in loans:
                loan.book_return()

    @api.onchange('borrower_id')
    def onchange_member(self):
        rent = self.env["library.book.rent"]
        books_on_rent = rent.search(
            [('state','=','ongoing'),('borrower_id','=',self.borrower_id.id)]
        )
        self.book_ids = books_on_rent.mapped('book_id')



