from odoo import models, fields, api


class BookCategory(models.Model):
    _name = 'library.book.category'
    name = fields.Char('Category')
    description = fields.Text('Description')
    parent_id = fields.Many2one('library.book.category', string='Parent Category', ondelete='restrict')
    child_ids = fields.One2many('library.book.category', 'parent_id', string='Child Categories')
    _parent_store = True
    _parent_id = 'parent_id'
    parent_path = fields.Char(index=True)

    @api.constrains
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise models.ValidationError('Error! You cannot create recursive categories.')


    def create_categories(self):
        cate1 = {
            'name': 'Child 1',
            'description': 'This is a child category',
        }
        cate2 = {
            'name': 'Child 2',
            'description': 'This is a child category',
        }
        parent_category_val = {
            'name': 'parent category',
            'description': 'This is a parent category',
            'child_ids': [(0, 0, cate1), (0, 0, cate2)]
        }
        record = self.env['library.book.category'].create(parent_category_val)
        return record