# -*- coding: utf-8 -*-
{
    'name': "Stock Inventory",
    'summary': "",
    'description': """""",
    'author': "",
    'website': "",
    'category': 'Inventory/Inventory',
    'version': '0.1',
    'depends': ['stock', 'stock_barcode', 'product'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/data.xml',
        'views/stock_inventory_view.xml',
        'views/stock_inventory_request_view.xml',
        'views/stock_inventory_plan_view.xml',
        'views/stock_inventory_approval_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'z_stock_inventory/static/src/**/*',
            'z_stock_inventory/static/src/*',
        ],
    },
    'license': 'AGPL-3',
}
