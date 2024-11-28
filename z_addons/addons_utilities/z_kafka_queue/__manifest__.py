# -*- coding: utf-8 -*-
{
    'name': "Kafka Queue",
    'summary': "",
    'description': """""",
    'author': "",
    'website': "",
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['base'],
    'license': 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'views/kafka_queue_consumer_view.xml',
        'views/kafka_queue_producer_view.xml',
    ],
}

