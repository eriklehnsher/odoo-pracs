from odoo import models, fields, api

from odoo import tools

class LibraryBookRentStatistics(models.Model):
    _name = "library.book.rent.statistics"
    _auto = False

    book_id = fields.Many2one("library.book", string="Book", readly=True)
    rent_count = fields.Integer("Times Borrowed", readonly=True)
    average_occupation = fields.Integer("Average Occupation(DAYS)", readonly=True)
    # các trường này sẽ ánh xạ tới các cột trong PostgreSQL view.

    def init(self):
        # Thực hiện tạo view trong PostgreSQL
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW library_book_rent_statistics AS (
                SELECT
                    min(lbr.id) as id,
                    lbr.book_id as book_id,
                    count(lbr.id) as rent_count,
                    avg((EXTRACT(epoch FROM age(return_date, rent_date)) / 86400))::int AS average_occupation
                FROM
                    library_book_rent AS lbr
                JOIN
                    library_book AS lb ON lb.id = lbr.book_id
                WHERE
                    lbr.state = 'returned'
                GROUP BY
                    lbr.book_id
            );
        """

        self.env.cr.execute(query)
        # Cập nhật lại toàn bộ cache của model này
        # self.env["library.book.rent.statistics"].search([]).invalidate_cache()