# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import consteq
import uuid
from datetime import datetime, timedelta


class AuthApiKey(models.Model):
    _name = "auth.api.key"
    _description = "API Key"

    name = fields.Char(required=True)
    key = fields.Char(
        help="""The API key. Enter a dummy value in this field if it is
        obtained from the server environment configuration.""",
        compute='get_user_access_token', store=True
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        help="""The user used to process the requests authenticated by
        the api key""",
    )

    # _sql_constraints = [("name_uniq", "unique(name)", "Api Key name must be unique.")]

    @api.depends('user_id')  # dump depend to trigger
    def get_user_access_token(self):
        for r in self:
            if r.user_id:
                r.key = uuid.uuid4().hex

    def automation_delete_expire_key(self):
        expired_date = datetime.now() - timedelta(hours=1)
        token_expire = self.search([('create_date', '<', expired_date)])
        if token_expire:
            token_expire.sudo().unlink()

    @api.model
    def _retrieve_api_key(self, key):
        return self.browse(self._retrieve_api_key_id(key))

    @api.model
    @tools.ormcache("key")
    def _retrieve_api_key_id(self, key):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("User is not allowed"))
        for api_key in self.search([]):
            if api_key.key and consteq(key, api_key.key):
                return api_key.id
        raise ValidationError(_("The key %s is not allowed") % key)

    @api.model
    @tools.ormcache("key")
    def _retrieve_uid_from_api_key(self, key):
        return self._retrieve_api_key(key).user_id.id

    # def _clear_key_cache(self):
    #     self._retrieve_api_key_id.clear_cache(self.env[self._name])
    #     self._retrieve_uid_from_api_key.clear_cache(self.env[self._name])

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AuthApiKey, self).create(vals_list)
        if any(["key" in vals or "user_id" in vals for vals in vals_list]):
            self.env.registry.clear_cache()
        return records

    def write(self, vals):
        super(AuthApiKey, self).write(vals)
        if "key" in vals or "user_id" in vals:
            self.env.registry.clear_cache()
        return True

    def get_api_key(self, user):
        api_key = self.search([('user_id', '=', user.id)], limit=1)
        if not api_key:
            api_key = self.create({
                'name': user.login,
                'user_id': user.id,
            })
        return api_key.key if api_key else ''
