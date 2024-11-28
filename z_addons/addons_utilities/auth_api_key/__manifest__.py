# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Auth Api Key",
    "summary": """
        Authenticate http requests from an API key""",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/server-auth",
    "development_status": "Beta",
    "data": [
        'data/delete_expire_api_key_cron.xml',
        "security/ir.model.access.csv",
        "views/auth_api_key.xml",
        'views/api_logging_view.xml',
    ],
    "depends": [
        'partner_autocomplete',
    ]
}
