# -*- coding: utf-8 -*-

from odoo import models, fields


class ApiLogging(models.Model):
    _name = 'api.logging'
    _description = 'Api Logging'
    _order = 'id desc'

    api_name = fields.Char(string='Api Name')
    remote_ip = fields.Char(string='Remote IP')
    params = fields.Text(string='Params')
    response_code = fields.Integer(string='Response Code')
    response_message = fields.Text(string='Response Message')
