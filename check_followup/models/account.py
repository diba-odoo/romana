from odoo import fields , models,api,tools,_
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError
# from odoo import amount_to_text


class AccountAccount(models.Model):
    _inherit = 'account.account'

    active = fields.Boolean(string='Active',default='False')
