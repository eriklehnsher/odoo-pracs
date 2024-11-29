# -*- coding: utf-8 -*-
{
    'name': "Z Stock Picking",
    'summary': "Transfer Product Between Warehouse",
    'description': """""",
    'author': "",
    'website': "",
    'category': 'Inventory/Inventory',
    'version': '0.1',
    'depends': ['stock', 'product', 'z_stock', 'z_stock_location'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'views/stock_move_location_pick_view.xml',
        'views/stock_quant_package_pick_view.xml',
        'views/stock_picking_confirm_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'z_stock_picking/static/src/**/*'
        ]
    },
    'license': 'AGPL-3',
}
