# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    erp_client_id = fields.Many2one('erp.res.company', string='Client')
    erp_org_id = fields.Integer(string='Organization')
    erp_bpartner_id = fields.Integer(string='Bpartner ID')
    erp_is_customer = fields.Boolean(string='Is Customer')
    erp_is_vendor = fields.Boolean(string='Is Vendor')
    erp_is_employee = fields.Integer(string='Is Employee')
    erp_is_sales_rep = fields.Boolean(string='Is Sales Rep')
    erp_fax = fields.Char(string='Fax')
    erp_bpartner_location_id = fields.Integer(string='Bpartner Location Id')
    erp_location_id = fields.Integer(string='Location Id')
    erp_location_address = fields.Integer(string='Location Address')
    erp_created_at = fields.Datetime(string='Created At')
    erp_updated_at = fields.Datetime(string='Updated At')

    # a = {
    #     "objName": "BPartner",
    #     "objData": {
    #         "clientInfo": {
    #             "clientId": 1000001,
    #             "clientName": "Công ty TNHH Quốc tế Tam Sơn"
    #         },
    #         "bpartnerInfo": {
    #             "orgInfo": {
    #                 "orgId": 0,
    #                 "orgCode": "0",
    #                 "orgName": "All Organizations",
    #                 "orgAddress": null,
    #                 "defaultWarehouseInfo": null,
    #                 "taxCode": null,
    #                 "phone": null,
    #                 "fax": null,
    #                 "email": null,
    #                 "isActive": true
    #             },
    #             "bpartnerId": 1158868,
    #             "bpartnerCode": "KH.WK.60030",
    #             "bpartnerName": "Đậu Xuân Kiên",
    #             "isCustomer": true,
    #             "isVendor": true,
    #             "isEmployee": true,
    #             "isSalesRep": true,
    #             "bpartnerLocationInfo": [
    #                 {
    #                     "bpartnerLocationId": 1324968,
    #                     "bpartnerLocationName": "21 lê văn hưu, Quận Hai Bà Trưng, Thành phố Hà Nội, Viet Nam",
    #                     "isActive": true,
    #                     "phone": null,
    #                     "email": null,
    #                     "locationId": 1225016,
    #                     "locationAddress": "21 lê văn hưu, Quận Hai Bà Trưng, Thành phố Hà Nội",
    #                     "createdAt": 1726716617000,
    #                     "updatedAt": 1726716617000
    #                 }
    #             ],
    #             "createdAt": 1726716617000,
    #             "updatedAt": 1726716617000
    #         }
    #     }
    # }
