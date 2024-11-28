# -*- coding: utf-8 -*-

from odoo import models, fields


class KafkaQueueErrorLogging(models.Model):
    _name = 'kafka.queue.error.logging'
    _description = 'Kafka queue error logging'

    message = fields.Json(string='Message')
    error = fields.Text(string='Error')
    topic = fields.Char(string='Topic')
    offset = fields.Integer(string='Offset')
    partition = fields.Integer(string='Partition')


class MsgLogging(models.Model):
    _name = 'msg.log'

    topic_receive = fields.Char(string='Topic Receive')
    topic_send = fields.Char(string='Topic Send')
    action_type = fields.Char(string='Action Type')
    obj_name = fields.Char(string='Object Name')
    message_send = fields.Json(string='Message Send')
    message_receive = fields.Json(string='Message Receive')
