{
    'name': 'Plan Sales',
    'version': '1.0',
    'category': 'Sales',
    'description': "Kế Hoạch kinh doanh",
    'depends': ['sale'],
    'data': [
        'security/plan_sale_order_security.xml',
        'security/ir.model.access.csv',
        'views/plan_sale_order_views.xml',
        'views/sale_order_inherit_views.xml',
    ]
}
