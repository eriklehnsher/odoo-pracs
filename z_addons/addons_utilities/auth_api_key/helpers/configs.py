# -*- coding: utf-8 -*-

from odoo.http import request


class Configs(object):
    def check_allow_ip(ip):
        pass

    def get_request_ip(self):
        ip = request.httprequest.headers.environ['REMOTE_ADDR']
        if 'HTTP_X_FORWARDED_FOR' in request.httprequest.headers.environ \
                and request.httprequest.headers.environ['HTTP_X_FORWARDED_FOR']:
            forwarded_for = request.httprequest.headers.environ['HTTP_X_FORWARDED_FOR'].split(', ')
            if forwarded_for and forwarded_for[0]:
                ip = forwarded_for[0]
        return ip

    def _set_log_api(self, ip, name, params, code, mess):
        vals = {
            'api_name': name,
            'remote_ip': ip,
            'params': params,
            'response_code': code,
            'response_message': mess,
        }
        request.env['api.logging'].sudo().create(vals)
        return
