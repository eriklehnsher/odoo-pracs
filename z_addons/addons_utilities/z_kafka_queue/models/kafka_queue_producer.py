# -*- coding: utf-8 -*-

from odoo import models, fields
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.error import KafkaException, KafkaError
import logging
import json

_logger = logging.getLogger(__name__)


class KafkaQueueProducer(models.Model):
    _name = 'kafka.queue.producer'
    _description = 'Kafka Queue Producer'
    _rec_name = 'topic'

    topic = fields.Char(string='Topic', copy=False)
    active = fields.Boolean(string='Active', default=True)
    client_id = fields.Char(string='Client ID')
    host = fields.Char(string='Host')
    port = fields.Char(string='Port')
    partition = fields.Integer(string='Partition', default=1,
                               help='Number of partitions you want to create for the topic.')
    replication = fields.Integer(string='Replication', default=1, help='Replication factor of partitions.')
    message = fields.Text(string='Message')

    def create_topic(self):
        try:
            conf = {
                'bootstrap.servers': '%s:%s' % (self.host, self.port),
            }
            admin_client = AdminClient(conf)
            res = admin_client.create_topics(
                [NewTopic(self.topic, num_partitions=self.partition, replication_factor=self.replication)])
        except Exception as ex:
            if ex.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                _logger.error('KafkaError.TOPIC_ALREADY_EXISTS: %s' % self.topic)
            else:
                _logger.error('Error create topic kafka: %s' % ex)

    def delete_topic(self):
        try:
            conf = self.conf.copy() if self.conf else {
                'bootstrap.servers': '%s:%s' % (self.host, self.port),
                'client.id': self.client_id,
            }
            admin_client = AdminClient(conf)
            admin_client.delete_topics([self.topic])
        except Exception as ex:
            _logger.error('Error delete topic kafka: %s' % ex)

    def publish(self, msg=None):
        msg = json.loads(self.message)
        conf = {
            'bootstrap.servers': '%s:%s' % (self.host, self.port),
        }
        producer = Producer(conf)
        producer.produce(self.topic, json.dumps(msg).encode('utf-8'))
        producer.flush()
