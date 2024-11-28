# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID, _
from confluent_kafka import Producer, KafkaError, KafkaException
import json
import uuid
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    _sql_constraints = [
        ('erp_document_id', 'UNIQUE(erp_document_id)', _('erp_document_id must be unique')),
    ]

    erp_document_id = fields.Integer(string='Erp Document ID', copy=False, index=True)
    erp_document_no = fields.Char(string='Erp Document Name', copy=False)
    erp_org_id = fields.Integer(string='Erp Organization ID', copy=False)
    erp_client_id = fields.Integer(string='Erp Client ID', default=1000001, copy=False)
    erp_user_id = fields.Integer(string='Erp User ID', copy=False)
    erp_document_status = fields.Char(string='Erp Status Document', copy=False)
    erp_created_at = fields.Datetime(string='Erp Created At', copy=False)
    erp_updated_at = fields.Datetime(string='Erp Updated At', copy=False)
    erp_document_confirm_id = fields.Integer(string='Erp Document Confirm ID', copy=False)
    erp_document_confirm_no = fields.Char(string='Erp Document Confirm Name', copy=False)
    erp_source_warehouse_id = fields.Integer(string='Erp Source Warehouse ID', copy=False)
    erp_dest_warehouse_id = fields.Integer(string='Erp Dest Warehouse ID', copy=False)
    erp_document_type_id = fields.Integer(string='Erp Document Type ID', copy=False)
    erp_msg_create = fields.Json(string='Erp Msg Create', copy=False)
    department_id = fields.Many2one('erp.hr.department', string='Department', copy=False)

