# -*- coding: utf-8 -*-
{
    'name': "Z Stock Barcode",
    'summary': "",
    'description': """Barcode For Warehouse""",
    'author': "",
    'website': "",
    'category': 'Inventory/Inventory',
    'version': '0.1',
    'depends': ['stock_barcode', 'z_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_quant_view.xml',
        'views/stock_warehouse_view.xml',
        'report/template/report_stock_barcode_warehouse.xml',
        'report/stock_warehouse_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'z_stock_barcode/static/src/**/*.js',
        ],
    },
    'license': 'LGPL-3',
}
