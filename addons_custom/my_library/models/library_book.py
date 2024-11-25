from email.policy import default

from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.tests.common import Form


class LibraryBook(models.Model):
    _name = "library.book"
    _description = "Library Book"

    # to sort the records first-from the newest to the oldest + then by title
    _order = "date_release desc, name"
    # to use the short_name field as the record representation - ở đây là để hiển thị tên ngắn của sách
    _rec_name = "short_name"

    short_name = fields.Char("Short Title", required=True)
    name = fields.Char("Title", required=True)

    # _sql_constraints = [
    #     ('tên_ràng_buộc', 'Câu lệnh SQL', 'Thông báo lỗi nếu vi phạm')
    # ]
    _sql_constraints = [
        ("name_uniq", "UNIQUE (name)", "Book title must be unique."),
        ("positive_page", "CHECK(pages > 0)", "No of pages must be positive"),
    ]
    notes = fields.Text("Internal Notes")
    state = fields.Selection(
        [
            ("draft", "Unavailable"),
            ("available", "Available"),
            ("borrowed", "Borrowed"),
            ("lost", "Lost"),
        ],
        "State",
        default="draft",
    )
    active = fields.Boolean("Active?", default=True)
    description = fields.Html("Description")
    cover = fields.Binary("Book Cover")
    out_of_print = fields.Boolean("Out of Print?")
    date_release = fields.Date("Release Date")
    pages = fields.Integer("Number of Pages")
    cost_price = fields.Float("Book Cost")
    date_updated = fields.Datetime("Last Updated")
    reader_rating = fields.Float(
        "Reader Average Rating", (14, 4)
    )  # trung bình đánh giá của người đọc( 14 digits in total, 4 after the decimal point - số lượng chữ số sau dấu phẩy là 4 chữ số sau dấu phẩy)
    author_ids = fields.Many2many("res.partner", "library_book_res_partner_rel", string="Author")
    currency_id = fields.Many2one("res.currency", string="Currency")
    retail_price = fields.Monetary("Retail Price", currency_field="currency_id")
    publisher_id = fields.Many2one("res.partner", string="Publisher")
    category_id = fields.Many2one("library.book.category", string="Category")
    quantity = fields.Integer("Quantity", default=1, required=True)
    age_days = fields.Float(
        string="Days Since Release",
        compute="_compute_age",
        inverse="_inverse_age",
        search="_search_age",
        store=False,
        compute_sudo=True,
    )
    publisher_city = fields.Char(
        "Publisher City", related="publisher_id.city", related_sudo=True, readonly=True
    )
    ref_doc_id = fields.Reference(
        selection="_referencable_models", string="Reference Document"
    )
    manager_remarks = fields.Text("Manager Remarks")

    genre = fields.Selection(
        [("scifi", "Science Fiction"),
         ("fantasy", "Fantasy"),
         ("drama", "Drama"),
         ("mystery", "Mystery"),
         ("nonfiction", "Non-Fiction"),
         ("other", "Other"), ], "Genre", default="scifi")




    # defs for the library.book model

    def get_fiction_books(self):
        fiction_books = self.env["library.book"].search([("genre", "=", "scifi")])
        return fiction_books

    def return_all_books(self):
        self.ensure_one()
        wizard = self.env["library.return.wizard"]
        with Form(wizard) as return_form:
            return_form.borrower_id = self.env.user.partner_id  # gán giá trị cho borrower_id
            record = return_form.save()
            record.books_returns()
            print("Return all books", record)

    def books_with_multiple_authors(self, all_books):
        all_books = self.env["library.book"].search([])

        def predicate(book):
            if len(book.author_ids) > 1:
                return True
            return False

        return all_books.filtered(predicate)

    print("books_with_multiple_authors", books_with_multiple_authors)

    def book_rent(self):
        self.ensure_one()
        if self.state != "available":
            raise UserError(("Book is not available"))

        if self.quantity <= 0:
            raise UserError(("Book is out of stock"))

        rent_as_superuser = (
            self.env["library.book.rent"]
            .sudo()
            .create(
                {
                    "book_id": self.id,
                    "borrower_id": self.env.user.partner_id.id,
                }
            )
        )
        self.quantity -= 1
        return rent_as_superuser

    def change_date_release(self):
        self.ensure_one()
        self.date_release = fields.Date.today()
        print("Date Release changed")

    # Get the empty recordset of library.book.rent as a superuser:

    def log_all_library_members(self):
        library_member_model = self.env["library.member"]
        all_members = library_member_model.search([])
        print("ALL MEMBERS:", all_members)
        return True

    def is_allowed_transition(self, old_state, new_state):
        allowed = [
            ("draft", "available"),
            ("available", "borrowed"),
            ("borrowed", "available"),
            ("available", "lost"),
            ("borrowed", "lost"),
            ("lost", "available"),
        ]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                continue

    def make_available(self):
        self.change_state("available")

    def make_borrowed(self):
        self.change_state("borrowed")

    def make_lost(self):
        self.ensure_one()
        self.state = "lost"
        if not self.env.context.get('avoid_deactivate'):
            self.active = False

    def restore_all_books(self):
        hidden_books = self.env['library.book'].search([('active', '=', False)])
        hidden_books.write({'active': True})
        return True

    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered("date_release"):
            book.date_release = today - timedelta(days=book.age_days)

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        value_date_str = value_date.strftime("%Y-%m-%d")
        operator_map = {
            ">": "<",
            ">=": "<=",
            "<": ">",
            "<=": ">=",
        }
        new_op = operator_map.get(operator, operator)
        return [("date_release", new_op, value_date_str)]

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

    @api.depends("date_release")
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delte = today - book.date_release
                book.age_days = delte.days
            else:
                book.age_days = 0

    def get_combined_books(self):
        recordset1 = self.search([("category_id.name", "=", "Science")])
        recordset2 = self.search([("category_id.name", "=", "Fiction")])
        result = recordset1 | recordset2
        return result
        print(result, "result")

    @api.model
    def _referencable_models(self):
        models = self.env["ir.model"].search([("field_id.name", "=", "message_ids")])
        return [(x.model, x.name) for x in models]

    def sort_books_by_date(self, books):
        return books.sorted(key="date_release", reverse=True)

    def create(self, values):
        if (
                not self.user_has_groups("my_library.group_librarian_manager")
                and "manager_remarks" in values
        ):
            raise models.ValidationError(
                "You are not allowed to modify manager_remarks"
            )
        return super(LibraryBook, self).create(values)

    def write(self, vals):
        if (
                not self.user_has_groups("my_library.group_librarian_manager")
                and "manager_remarks" in vals
        ):
            raise models.ValidationError(
                "You are not allowed to modify manager_remarks"
            )
        return super(LibraryBook, self).write(vals)

    def _get_average_cost(self):  # Tính giá trung bình theo từng category
        grouped_result = self.read_group(
            [("cost_price", "!=", False)],  # domain
            [("category_id", "cost_price:avg")],  # fields to group by
            ["category_id"],  # group by
        )
        return grouped_result

    def action_get_average_cost(self):
        result = self._get_average_cost()
        print(result, "result of get_average_cost")
        return True


class ResPartner(models.Model):
    _inherit = "res.partner"
    published_book_ids = fields.One2many(
        "library.book", "publisher_id", string="Published Books"
    )
    book_ids = fields.One2many("library.book", "publisher_id", string="Published Books")
    authored_book_ids = fields.Many2many(
        "library.book",
        string="Authored Books",
        # optional
    )
    count_books = fields.Integer(
        "Number of Authored Books", compute="_compute_count_books"
    )
    customer_rank = fields.Integer("Customer Rank", default=0)

    supplier_rank = fields.Integer("Supplier Rank", default=0)

    #def for the res.partner model
    @api.depends("authored_book_ids")
    def _compute_count_books(self):
        for author in self:
            author.count_books = len(author.authored_book_ids)
