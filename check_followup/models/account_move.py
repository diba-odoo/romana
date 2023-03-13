from odoo import fields , models,api,tools,_
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError
# from odoo import amount_to_text


class AccountMove(models.Model):
    _inherit = 'account.move'

    # is_reversed = fields.Boolean(string='Is Reversed',default='False')

    def button_draft(self):

        # if self.state == 'cancel':
        #     raise ValidationError('You can not change state for this entry because it is on canceled state !!')
        # else:
        super(AccountMove,self).button_draft()