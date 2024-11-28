import json
import xmlrpc.client as xmlrpclib
import odoo
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.dataset import DataSet
from ..helpers.api_exception import ApiException
from ..helpers.configs import Configs
from ..helpers.response import Response
from ..helpers.authenticate import Authenticate
from odoo.exceptions import AccessError, ValidationError, MissingError, UserError, AccessDenied
from psycopg2 import OperationalError


class Main(DataSet):

    @http.route(['/web/dataset/call_kw_api', '/web/dataset/call_kw_api/<path:path>'], type='json', auth="api_key",
                cors='*')
    def call_kw_api(self, model, method, args, kwargs, path=None):
        return self._call_kw(model, method, args, kwargs)

    @http.route(['/web/login_get_key'], methods=['POST'], type='json', auth="none", cors='*')
    def login_get_key(self, **kwargs):
        try:
            ip = Configs.get_request_ip(request)
            request.session.authenticate(kwargs.get('db', ''), kwargs.get('login', ''), kwargs.get('password', ''))
            request.session.db = kwargs.get('db', '')
            registry = odoo.modules.registry.Registry(kwargs.get('db', ''))
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, request.session.uid, request.session.context)
                api_key = env['auth.api.key'].sudo().get_api_key(env.user)
                Configs._set_log_api(request, ip, request.httprequest.path, str(kwargs), ApiException.OK[0], 'SUCCESS')
                return Response.success(message='SUCCESS', data={
                    'api_key': api_key,
                }).to_json()
        except AccessError as e:
            Configs._set_log_api(request, ip, request.httprequest.path, str(kwargs), ApiException.BAD_REQUEST[0], e)
            return ApiException(e, ApiException.BAD_REQUEST).to_json()
        except AccessDenied as e:
            Configs._set_log_api(request, ip, request.httprequest.path, str(kwargs), ApiException.UNAUTHORIZED[0], e)
            return ApiException(e, ApiException.UNAUTHORIZED).to_json()
        except OperationalError as e:
            Configs._set_log_api(request, ip, request.httprequest.path, str(kwargs), ApiException.BAD_REQUEST[0], e)
            return ApiException('Database does not exist', ApiException.BAD_REQUEST).to_json()
        except Exception as e:
            Configs._set_log_api(request, ip, request.httprequest.path, str(kwargs), ApiException.INTERNAL_SERVER_ERROR[0], e)
            return ApiException(e, ApiException.INTERNAL_SERVER_ERROR).to_json()
