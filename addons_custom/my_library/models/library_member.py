from odoo import models, fields, api
from odoo.api import ondelete


class LibraryMember(models.Model):
    _inherits = {'res.partner':'partner_id'} # partner_id is the field name of the res.partner model - is foreign key.   cos the thay the bằng cách thêm trực tiếp "delegate=True" vào partner_id
    _name = 'library.member'
    _description = 'Library Member'

    partner_id = fields.Many2one('res.partner', ondelete='cascade') # ondelete('cascade') - delete the record in the res.partner model when the record in the library.member model is deleted
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of Birth')
