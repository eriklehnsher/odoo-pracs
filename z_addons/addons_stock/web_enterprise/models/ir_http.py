# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _post_logout(cls):
        request.future_response.set_cookie('color_scheme', max_age=0)

    def webclient_rendering_context(self):
        """ Overrides community to prevent unnecessary load_menus request """
        return {
            'session_info': self.session_info(),
        }

    def session_info(self):
        result = super(Http, self).session_info()
        result['support_url'] = "https://www.odoo.com/help"
        return result
