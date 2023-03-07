from odoo import fields , models,api,tools,_
from odoo.exceptions import ValidationError


class ChangeBankWizard(models.TransientModel):
    _name = 'change.bank'

    def _default_bank(self):
        active_id = self.env['check.followup'].browse(self._context.get('active_id'))
        return active_id.bank_id

    def _default_type(self):
        active_id = self.env['check.followup'].browse(self._context.get('active_id'))
        return active_id.check_type

    def _default_deposit_date(self):
        active_id = self.env['check.followup'].browse(self._context.get('active_id'))
        return active_id.check_date

    def _default_withdraw_date(self):
        active_id = self.env['check.followup'].browse(self._context.get('active_id'))
        return active_id.check_date

    journal_id = fields.Many2one('account.journal',string='Change Bank To',required=True,domain=[('type','=','bank')],
                                 default=_default_bank)
    deposit_date = fields.Date(string='Deposit Date', required=True,default=_default_deposit_date)
    withdraw_date = fields.Date(string='Withdraw Date', required=True,default=_default_withdraw_date)
    check_type = fields.Char(default=_default_type)

    def wizard_submit(self):
        active_id = self.env['check.followup'].browse(self._context.get('active_id'))
        if active_id.check_type == 'in':
            active_id.deposit_in_bank(self.journal_id,self.deposit_date)
        if active_id.check_type == 'out':
            active_id.withdraw_check(self.withdraw_date)
