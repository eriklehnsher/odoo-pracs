# -*- coding: utf-8 -*-

from odoo.http import request, Response as OdooResponse
import json


class Response(object):
    SUCCESS = 200
    ERROR = 400
    __CODE = ''
    __MESSAGE = ''
    __DATA = {}
    __DEFAULT_ERROR_MESSAGE = 'An error occurred, please try again later.'

    @staticmethod
    def success(message, data):
        Response.__CODE = Response.SUCCESS
        Response.__MESSAGE = message
        Response.__DATA = data
        return Response

    @staticmethod
    def error(message=False, data={}, code=False):
        Response.__CODE = code or Response.ERROR
        Response.__MESSAGE = message or Response.__DEFAULT_ERROR_MESSAGE
        Response.__DATA = data
        return Response

    @staticmethod
    def to_json():
        if request.dispatcher.routing_type == 'http':
            return OdooResponse(
                json.dumps(Response.__generate_template()),
                content_type='application/json',
                status=200,
            )
        return Response.__generate_template()

    @staticmethod
    def __generate_template():
        return {
            'code': Response.__CODE,
            'message': Response.__MESSAGE,
            'data': Response.__DATA,
        }
