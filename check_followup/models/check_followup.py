from odoo import fields , models,api,tools,_
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError
# from odoo import amount_to_text


class CheckFollowup(models.Model):
    _name = 'check.followup'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cheque Followups'
    _rec_name = 'cheque_number'
    _order = "cheque_number"

    def currency_default(self):
        return self.env.user.company_id.currency_id

    name_in = fields.Char(readonly=True,string='Ref')
    name_out = fields.Char(readonly=True,string='Ref' )

    advance_in = fields.Char(readonly=True,string='Ref' )
    advance_out = fields.Char(readonly=True, string='Ref')

    check_type = fields.Selection([('in','Customer Cheque'),
                                   ('out','Vendor Cheque'),
                                   ('advance_in','Advance In'),
                                   ('advance_out','Advance Out'),
                                   ],string='Type',readonly=True, track_visibility='onchange')
    state = fields.Selection([
                              ('out_standing','Out Standing Cheque'),
                              ('under_collection','Under Collection Cheque'),
                              ('deposit_check', 'Cheque Deposit'),
                              ('withdraw_check', 'Withdrawal Cheque'),
                              ('in_advance','In Advance A/C'),
                              ('out_advance','Out Advance A/C'),
                              ('advance_cleared','Advance Cleared form A/C'),
                              ('reject','Rejected/Bounced'),], track_visibility='onchange')
    check_date = fields.Date('Cheque Date', track_visibility='onchange')
    payment_date = fields.Date('Payment Date', track_visibility='onchange')
    check_number = fields.Char('Cheque Number', track_visibility='onchange')
    cheque_number = fields.Char('Cheque Number', track_visibility='onchange')
    log_ids = fields.One2many('check.log','check_id',readonly=True)
    bank_template = fields.Many2one('res.bank',string='Bank Template')
    source_document = fields.Char('Source Document',readonly=True, track_visibility='onchange')
    beneficiary = fields.Char('Beneficiary',readonly=True, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency',default=currency_default,readonly=True, track_visibility='onchange')
    amount = fields.Monetary('Amount',readonly=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner',string='Partner',readonly=True, track_visibility='onchange')
    # finance_id = fields.Many2one('finance.approval')
    check_move_id = fields.Many2one('account.move',string='Cheque JE')
    bank_id = fields.Many2one('account.journal', track_visibility='onchange', readonly=True)
    payment_id = fields.Many2one('account.payment',string='Payment')
    memo = fields.Char(string='Receipt Number',readonly=True)

    @api.model
    def create(self, vals):

        if vals['check_type'] == 'in':
            code = 'check.followup.in.code'
            message = 'Cheque/Received' + self.env['ir.sequence'].next_by_code(code)
            vals['name_in'] = message
        if vals['check_type'] == 'out':
            code = 'check.followup.out.code'
            message = 'Cheque/Delivered' + self.env['ir.sequence'].next_by_code(code)
            vals['name_out'] = message
        if vals['check_type'] == 'advance_in':
            code = 'check.followup.out.code'
            message = 'Advance/Received' + self.env['ir.sequence'].next_by_code(code)
            vals['advance_in'] = message
        if vals['check_type'] == 'advance_out':
            code = 'check.followup.out.code'
            message = 'Advance/Delivered' + self.env['ir.sequence'].next_by_code(code)
            vals['advance_out'] = message
        return super(CheckFollowup, self).create(vals)

    def bill_arrived(self):
        payment_search = self.env['account.payment'].search([('id', '=', self.payment_id.id)])
        if payment_search:
            move_obj = self.env['account.move']
            li = []
            debit_val = {
                # 'move_id': self.move_id.id,
                'name': self.memo,
                'account_id': payment_search.partner_id.property_account_payable_id.id,
                'partner_id': payment_search.partner_id.id,
                'debit': self.get_amount(),
                # 'analytic_account_id': approval_object.analytic_account.id or False,
                'currency_id': self.get_currency() or False,
                'amount_currency': self.amount_currency_debit() or False,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, debit_val))
            credit_val = {

                # 'move_id': approval_object.move_id.id,
                'name': self.memo,
                'account_id': payment_search.journal_id.advance_acc_out_id.id,
                'partner_id': payment_search.partner_id.id,
                'credit': self.get_amount(),
                'currency_id': self.get_currency() or False,
                'amount_currency': self.amount_currency_credit() or False,
                # 'analytic_account_id': ,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, credit_val))
            vals = {
                'journal_id': payment_search.journal_id.id,
                'date': datetime.today(),
                'ref': self.memo,
                # 'company_id': ,
                'line_ids': li,
            }
            a = move_obj.create(vals)
            a.action_post()
            log_obj = self.env['check.log']
            log_obj.create({'move_description': 'Clearance Advance payment ' + str(payment_search.journal_id.name),
                            'move_id': a.id,
                            'move_date': datetime.today(),
                            'check_id': self.id,
                            })
            self.state = 'advance_cleared'

    def invoice_arrived(self):
        payment_search = self.env['account.payment'].search([('id', '=', self.payment_id.id)])
        if payment_search:
            move_obj = self.env['account.move']
            li = []
            debit_val = {
                # 'move_id': self.move_id.id,
                'name': self.memo,
                'account_id': payment_search.journal_id.advance_acc_id.id,
                'partner_id': payment_search.partner_id.id,
                'debit': self.get_amount(),
                # 'analytic_account_id': approval_object.analytic_account.id or False,
                'currency_id': self.get_currency() or False,
                'amount_currency': self.amount_currency_debit() or False,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, debit_val))
            credit_val = {

                # 'move_id': approval_object.move_id.id,
                'name': self.memo,
                'account_id': payment_search.partner_id.property_account_receivable_id.id,
                'partner_id': payment_search.partner_id.id,
                'credit': self.get_amount(),
                'currency_id': self.get_currency() or False,
                'amount_currency': self.amount_currency_credit() or False,
                # 'analytic_account_id': ,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, credit_val))
            vals = {
                'journal_id': payment_search.journal_id.id,
                'date': datetime.today(),
                'ref': self.memo,
                # 'company_id': ,
                'line_ids': li,
            }
            a = move_obj.create(vals)
            a.action_post()
            log_obj = self.env['check.log']
            log_obj.create({'move_description': 'Clearance Advance payment ' + str(payment_search.journal_id.name),
                            'move_id': a.id,
                            'move_date': datetime.today(),
                            'check_id': self.id,
                            })
            self.state = 'advance_cleared'


    @api.model
    def get_amount(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount / self.currency_id.rate
        if self.currency_id == self.env.user.company_id.currency_id:
            return self.amount

    @api.model
    def get_currency(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.currency_id.id
        else:
            return self.currency_id.id

    @api.model
    def amount_currency_debit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount
        else:
            return self.amount

    @api.model
    def amount_currency_credit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount * -1
        else:
            return self.amount * -1

    def create_move(self,approval_object,date):
        move_obj = self.env['account.move']
        li = []
        self.check_date = date
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.memo,
            'account_id': approval_object.journal_id.out_account.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.memo,
            'account_id': approval_object.journal_id.default_account_id.id,
            'credit': self.get_amount(),
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': approval_object.journal_id.id,
            'date': date,
            'ref': self.memo,
            # 'company_id': ,
            'line_ids': li,
        }
        a = move_obj.create(vals)
        a.action_post()
        return a

    def create_move_in(self,payment,journal_id,date):
        move_obj = self.env['account.move']
        li = []
        self.check_date = date
        self.bank_id = journal_id.id
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.memo,
            'account_id': journal_id.default_account_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.memo,
            'account_id': payment.journal_id.in_account.id,
            'credit': self.get_amount(),
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': journal_id.id,
            'date': date,
            'ref': self.memo,
            # 'company_id': ,
            'line_ids': li,
        }
        a = move_obj.create(vals)
        a.action_post()
        return a

    def copy(self):
        raise ValidationError("You Can't Duplicate cheque !!")

    def withdraw_check(self,date):
        payment_search = self.env['account.payment'].search([('id','=', self.payment_id.id)])
        # pettycash_search = self.env['custody.request'].search([('id','=',self.petty_cash_id.id)])
        if payment_search:
            create_move = self.create_move(payment_search,date)
            log_obj = self.env['check.log']
            log_obj.create({'move_description': 'Withdraw Cheque From '+ str(payment_search.journal_id.name),
                            'move_id': create_move.id,
                            'move_date': datetime.today(),
                            'check_id': self.id,
                            })
            self.state = 'withdraw_check'

            channel_group_obj = self.env['mail.message']
            dic = {
                'subject': 'Payment Withdraw Check',
                'email_from': self.env.user.name,
                # 'model': self.name,
                'body': 'Payment Cheque Number ' + self.cheque_number + ' Withdraw',
                # 'partner_ids': [(4, self.env.ref('finance_approval.group_finance_approval_fm').id)],
                # 'channel_ids': [(4, self.env.ref('mail.channel_all_employees').id)],
            }
            channel_group_obj.create(dic)
        # if pettycash_search:
        #
        #     create_move = self.create_move(pettycash_search, date)
        #     log_obj = self.env['check.log']
        #     log_obj.create({'move_description': 'Withdraw Cheque From ' + str(pettycash_search.journal_id.name),
        #                     'move_id': create_move.id,
        #                     'move_date': datetime.today(),
        #                     'check_id': self.id,
        #                     })
        #     self.state = 'withdraw_check'

            channel_group_obj = self.env['mail.message']
            dic = {
                'subject': 'Payment Withdraw Check',
                'email_from': self.env.user.name,
                # 'model': self.name,
                'body': 'Payment Cheque Number ' + self.cheque_number + ' Withdraw',
                # 'partner_ids': [(4, self.env.ref('finance_approval.group_finance_approval_fm').id)],
                # 'channel_ids': [(4, self.env.ref('mail.channel_all_employees').id)],
            }
            channel_group_obj.create(dic)

    def check_reject(self):

        if self.payment_id and self.check_type == 'in' and self.state == 'under_collection':
            move_obj = self.env['account.move']
            li = []
            credit_val = {
                # 'move_id': self.move_id.id,
                'name': str('reverse: ')+str(self.payment_id.name),
                'account_id': self.payment_id.journal_id.in_account.id,
                'credit': self.payment_id.get_amount(),
                'partner_id': self.payment_id.partner_id.id,
                # 'analytic_account_id': approval_object.analytic_account.id or False,
                'currency_id': self.payment_id.get_currency() or False,
                'amount_currency': self.payment_id.amount_currency_credit() or False,
                # 'company_id': approval_object.company_id.id or False,

            }

            li.append((0, 0, credit_val))
            debit_val = {

                # 'move_id': approval_object.move_id.id,
                'name': str('reverse: ')+str(self.payment_id.name),
                'account_id': self.payment_id.partner_id.property_account_receivable_id.id,
                'debit': self.payment_id.get_amount(),
                'partner_id': self.payment_id.partner_id.id,
                'currency_id': self.payment_id.get_currency() or False,
                'amount_currency': self.payment_id.amount_currency_debit() or False,
                # 'analytic_account_id': ,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, debit_val))
            print("List", li)
            vals = {
                'journal_id': self.payment_id.journal_id.id,
                'date': datetime.today(),
                'ref': str('Reverse Check: ')+str(self.payment_id.cheque_number),
                # 'company_id': ,
                'line_ids': li,
            }
            a = move_obj.sudo().create(vals)
            a.action_post()
            vals = {
                'move_description': 'Reverse Check',
                'check_id': self.id,
                'move_date': datetime.today(),
                'move_id': a.id,

            }
            check_log = self.env['check.log']
            check_log.create(vals)
            self.payment_id.state = 'cancel'
            self.state = 'reject'
        if self.payment_id and self.check_type == 'out' and self.state == 'out_standing':
            move_obj = self.env['account.move']
            li = []
            credit_val = {
                # 'move_id': self.move_id.id,
                'name': str('reverse: ')+str(self.payment_id.name),
                'account_id': self.payment_id.partner_id.property_account_payable_id.id,
                'credit': self.payment_id.get_amount(),
                'partner_id': self.payment_id.partner_id.id,
                # 'analytic_account_id': approval_object.analytic_account.id or False,
                'currency_id': self.payment_id.get_currency() or False,
                'amount_currency': self.payment_id.amount_currency_credit() or False,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, credit_val))
            debit_val = {

                # 'move_id': approval_object.move_id.id,
                'name': str('reverse: ')+str(self.payment_id.name),
                'account_id': self.payment_id.journal_id.out_account.id,
                'debit': self.payment_id.get_amount(),
                'partner_id': self.payment_id.partner_id.id,
                'currency_id': self.payment_id.get_currency() or False,
                'amount_currency': self.payment_id.amount_currency_debit() or False,
                # 'analytic_account_id': ,
                # 'company_id': approval_object.company_id.id or False,

            }
            li.append((0, 0, debit_val))
            print("List", li)
            vals = {
                'journal_id': self.payment_id.journal_id.id,
                'date': datetime.today(),
                'ref': str('Reverse Check: ')+str(self.payment_id.cheque_number),
                # 'company_id': ,
                'line_ids': li,
            }
            a = move_obj.create(vals)
            a.action_post()
            vals = {
                'move_description': 'Reverse Check',
                'check_id': self.id,
                'move_date': datetime.today(),
                'move_id': a.id,

            }
            check_log = self.env['check.log']
            check_log.sudo().create(vals)
            self.state = 'reject'
        self.payment_id.action_draft()
        self.payment_id.action_cancel()

    def change_bank(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Change Bank Wizard',
            'res_model': 'change.bank',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def change_date(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Change Date Wizard',
            'res_model': 'change.bank',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def deposit_in_bank(self,journal_id,date):

        payment_search = self.env['account.payment'].search([('name', '=', self.source_document),
                                                             ])

        if payment_search:
            create_move = self.create_move_in(payment_search,journal_id,date)
            log_obj = self.env['check.log']
            log_obj.create({'move_description': 'Deposit Cheque in '+ str(journal_id.name),
                            'move_id': create_move.id,
                            'move_date': datetime.today(),
                            'check_id': self.id,
                            })
            self.state = 'deposit_check'
            channel_group_obj = self.env['mail.message']
            dic = {
                'subject': 'Payment Cheque Reject',
                'email_from': self.env.user.name,
                # 'model': self.name,
                'body': 'Approval Cheque Number ' + self.cheque_number + ' Deposit In Bank ',
                # 'partner_ids': [(4, self.env.ref('finance_approval.group_finance_approval_fm').id)],
                # 'channel_ids': [(4, self.env.ref('mail.channel_all_employees').id)],
            }
            channel_group_obj.create(dic)


class CheckLog(models.Model):
    _name = 'check.log'
    _description = 'Cheque Logs'

    move_id = fields.Many2one('account.move','Journal Entry')
    move_description = fields.Char('Description',)
    check_id = fields.Many2one('check.followup',string='Reference')
    move_date = fields.Date('Journal Entry Date')
    # finance_id = fields.Many2one('finance.approval',string='Finance Reference')


class JournalObject(models.Model):
    _inherit = 'account.journal'

    out_account = fields.Many2one('account.account', string='Out Standing Account')
    in_account = fields.Many2one('account.account', string='Under Collection Account')
    advance_acc_id = fields.Many2one('account.account', string= 'Advance/Payment in Account')
    advance_acc_out_id = fields.Many2one('account.account', string= 'Advance/Payment out Account')
    credit_card_acc_id = fields.Many2one('account.account', string='Credit Card/ in Account')
    credit_card_acc_out_id = fields.Many2one('account.account', string='Credit Card/ out Account')



