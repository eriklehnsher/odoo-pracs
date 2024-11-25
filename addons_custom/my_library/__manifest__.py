{
    'name':'My Library',
    'summary':'Manage books easily',
    'category': 'Library',
    'description': """
    Manage Library
    ==============
    Description related to library
    """,
    'author':'Erik.',
    'version':'1.0.0',
    'depend':['base','mail'],
    'data':[
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/my_library_views.xml",
        "views/res_partner_inherit_view.xml",
        "views/library_members_views.xml",
        "views/library_book_catg_views.xml",
        "views/library_book_rent_view.xml",
        "wizard/library_rent_wizard_view.xml",
        "wizard/library_return_wizard_view.xml",
        ],
    'demo': [

    ],
}