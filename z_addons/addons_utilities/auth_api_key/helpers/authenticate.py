# -*- coding: utf-8 -*-

from odoo import _, registry, tools
from .api_exception import ApiException
from hashlib import sha3_256
import jwt
from datetime import datetime


class Authenticate(object):

    __SECRET_KEY = tools.config.options.get('secret_key')

    @staticmethod
    def generate_access_token(api_key):
        payload = {
            'api_key': api_key,
            'ts': datetime.now().timestamp(),
        }
        return jwt.encode(payload, Authenticate._Authenticate__SECRET_KEY, algorithm='HS256')

    @staticmethod
    def verify_access_token(env, access_token):
        try:
            jwt.decode(access_token, Authenticate._Authenticate__SECRET_KEY, algorithms=['HS256'])
            header, payload, sign = access_token.split('.')
            is_sign_in = env['auth.api.key'].search([('key', '=', payload['api_key'])])
            if not is_sign_in:
                raise Exception()
            return {
                'login': is_sign_in.user_id.login,
                'api_key': is_sign_in.key,
                'user_id': is_sign_in.user_id.id,
            }
        except Exception as e:
            raise ApiException('Access token is not valid', ApiException.INVALID_ACCESS_TOKEN).to_json()
