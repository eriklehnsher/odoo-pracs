from odoo import http
import json
from odoo.tools import date_utils
import werkzeug.datastructures


class Request(http.Request):
    def make_json_response(self, data, headers=None, cookies=None, status=200):
        data = json.dumps(data, ensure_ascii=False, default=date_utils.json_default)

        headers = werkzeug.datastructures.Headers(headers)
        headers['Content-Length'] = len(data)
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json; charset=utf-8'

            headers['Access-Control-Allow-Origin'] = '*'
            # headers['Access-Control-Allow-Headers'] = 'origin, x-csrftoken, content-type, accept, x-openerp-session-id, authorization'
            # 'Origin, X-Requested-With, Content-Type, Accept, Authorization'
            # headers['Access-Control-Allow-Credentials'] = 'true'
            headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'

        return self.make_response(data, headers.to_wsgi_list(), cookies, status)

    http.Request.make_json_response = make_json_response

    def _inject_future_response(self, response):
        new_header = []
        for header2 in self.future_response.headers:
            exist = False
            for header in response.headers:
                if header[0] == header2[0]:
                    exist = True
            if not exist:
                new_header.append(header2)
            # response.headers.append(header)
        response.headers.extend(new_header)
        return response

    http.Request._inject_future_response = _inject_future_response

from . import controller
from . import models
