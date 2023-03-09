from odoo import fields , models,api,tools,_
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError,UserError
# from odoo import amount_to_text


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    check_type = fields.Selection(selection=[('direct', 'Direct'), ('PDC', 'PDC')])

class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    check_followup = fields.Selection([('pdc','PDC'),
                                       ('direct','Direct')],string='Payment Type',compute='_get_check_type',readonly=True)
    journal_type = fields.Selection(related='journal_id.type')
    check_date = fields.Date(string='Cheque Date',copy=False)
    check_number = fields.Char(string='Cheque Number',copy=False)
    cheque_number = fields.Char(string='Cheque Number',copy=False)
    check_count = fields.Integer(compute='_compute_check')
    advance_count = fields.Integer(compute='_compute_advance')
    # check_id = fields.Many2one('check.followup',string='Check Ref')
    debit_line_id = fields.Many2one('account.move.line')
    credit_line_id = fields.Many2one('account.move.line')


    @api.depends('payment_method_id')
    def _get_check_type(self):
        for r in self:
            if r.payment_method_id:
                if r.payment_method_id.check_type == 'PDC':
                    r.check_followup = 'pdc'
                else:
                    r.check_followup = 'direct'


    def action_draft2(self):
        check_search = self.env['check.followup'].search([('payment_id.id', '=', self.id)])
        if check_search:
            for x in check_search:
                if x.state !='reject':
                    raise ValidationError('You can not change state for this Payment because it is There are pay-related checks !!')
        else:
            self.move_id.button_draft()

    def _compute_check(self):
        payment_count = self.env['check.followup'].sudo().search_count([('payment_id','=',self.id)])
        self.check_count = payment_count

    def _compute_advance(self):
        payment_count = self.env['check.followup'].sudo().search_count([('payment_id','=',self.id)])
        self.advance_count = payment_count

    # @api.one
    def action_check_view(self):
        if self.payment_type == 'inbound':
            tree_view_in = self.env.ref('check_followup.view_tree_check_followup_in')
            form_view_in = self.env.ref('check_followup.view_form_check_followup_in')
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Customer Cheques',
                'res_model': 'check.followup',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'views': [(tree_view_in.id, 'tree'), (form_view_in.id, 'form')],
                'domain': [('payment_id', '=', self.id)],

            }
        if self.payment_type == 'outbound':
            tree_view_in = self.env.ref('check_followup.view_tree_check_followup_in')
            form_view_in = self.env.ref('check_followup.view_form_check_followup_in')
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Vendor cheques',
                'res_model': 'check.followup',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'views': [(tree_view_in.id, 'tree'), (form_view_in.id, 'form')],
                'domain': [('payment_id', '=', self.id)],

            }

    def action_advance_view(self):
        if self.payment_type == 'inbound':
            tree_view_in = self.env.ref('check_followup.view_tree_check_followup_in')
            form_view_in = self.env.ref('check_followup.view_form_check_followup_in')
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Customer Advance payment',
                'res_model': 'check.followup',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'views': [(tree_view_in.id, 'tree'), (form_view_in.id, 'form')],
                'domain': [('payment_id', '=', self.id)],

            }
        if self.payment_type == 'outbound':
            tree_view_out = self.env.ref('check_followup.view_tree_check_followup_out')
            form_view_out = self.env.ref('check_followup.view_form_check_followup_out')
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Vendor cheques',
                'res_model': 'check.followup',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'views': [(tree_view_out.id, 'tree'), (form_view_out.id, 'form')],
                'domain': [('payment_id', '=', self.id)],

            }


    def print_telegraphic_transfer(self):
        return self.env.ref('check_followup.report_telegraphic_transfer_payment_print').report_action(self)


    def print_bank_payment_voucher(self):
        return self.env.ref('check_followup.report_bank_payment_voucher_print').report_action(self)


    @api.model
    def get_currency(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.currency_id.id
        else:
            return self.currency_id.id

    @api.model
    def amount_currency_credit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount * -1
        else:
            return self.amount * -1

    @api.model
    def amount_currency_debit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount
        else:
            return self.amount

    @api.model
    def get_amount(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount / self.currency_id.rate
        if self.currency_id == self.env.user.company_id.currency_id:
            return self.amount


    def in_bound_cheque(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.in_account.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def _create_cheque_inbound(self):
        check_obj = self.env['check.followup']
        check_val = {
            'check_date': self.check_date,
            'cheque_number': self.cheque_number,
            'source_document': self.name,
            'memo': self.ref,
            'beneficiary': self.company_id.name,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'state': 'under_collection',
            'check_type': 'in',
            'partner_id': self.partner_id.id,
            # 'check_move_id': a.id,
            'bank_id': self.journal_id.id,
            'payment_id': self.id,
        }
        check_id = check_obj.create(check_val)
        return check_id
        ###########LOG#############################

    def _create_move_outbound(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.partner_id.property_account_payable_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.out_account.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def _create_cheque_output(self):
        check_obj = self.env['check.followup']
        check_val = {
            'check_date': self.check_date,
            'cheque_number': self.cheque_number,
            'source_document': self.name,
            'memo': self.ref,
            'beneficiary': self.partner_id.name,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'state': 'out_standing',
            'check_type': 'out',
            'partner_id': self.partner_id.id,
            # 'check_move_id': a.id,
            'bank_id': self.journal_id.id,
            'payment_id': self.id,
        }
        check_id = check_obj.create(check_val)
        return check_id

    def move_advance_inbound(self):

        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.advance_acc_id.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def action_cancel(self):

        if self.is_inter_company == True:
            self.move_intercompany_id.button_cancel()
        super(AccountPaymentInherit,self).action_cancel()

    def action_draft(self):
        if self.state == 'cancel':
            raise ValidationError('You can not change state for this Payment because it is on canceled state !!')
        else:
            super(AccountPaymentInherit, self).action_draft()

    def move_direct_in(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.partner_id.property_account_receivable_id.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def move_advance_out(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.advance_acc_out_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def move_direct_out(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.partner_id.property_account_payable_id.id,
            'partner_id': self.partner_id.id,
            'debit': self.get_amount(),
            # 'analytic_account_id': approval_object.analytic_account.id or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_debit() or False,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.default_account_id.id,
            'partner_id': self.partner_id.id,
            'credit': self.get_amount() or False,
            'currency_id': self.get_currency() or False,
            'amount_currency': self.amount_currency_credit() or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.ref,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def advance_in_cheque(self):
        check_obj = self.env['check.followup']
        check_val = {
            'payment_date': self.date,
            'source_document': self.ref,
            'memo': self.ref,
            'beneficiary': self.company_id.name,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'state': 'in_advance',
            'check_type': 'advance_in',
            'partner_id': self.partner_id.id,
            'payment_id': self.id,
        }
        payment_id = check_obj.create(check_val)
        return payment_id


    def advance_out_cheque(self):
        check_obj = self.env['check.followup']
        check_val = {
            'payment_date': self.date,
            'source_document': self.ref,
            'memo': self.ref,
            'beneficiary': self.company_id.name,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'state': 'out_advance',
            'check_type': 'advance_out',
            'partner_id': self.partner_id.id,
            'payment_id': self.id,
        }
        payment_id = check_obj.create(check_val)
        return payment_id

    def inter_company_inbound(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.inter_company_current_asset_id.id,
            # 'partner_id': self.partner_id.id,
            'debit': self.amount,
            'currency_id': self.currency_id.id or False,
            # 'amount_currency': self.amount_inter_company_currency_debit() or False,
            # 'company_id': self.journal_id.intercompany_company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.inter_company_payable_id.id,
            # 'partner_id': self.partner_id.id,
            'credit': self.amount or False,
            'currency_id': self.currency_id.id or False,
            # 'amount_currency': self.amount_inter_company_currency_credit() or False,
            # 'company_id': self.journal_id.intercompany_company_id.id or False,
            # 'analytic_account_id': ,
            # 'company_id': approval_object.company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)


        vals = {
            'journal_id': self.journal_id.intercompany_journal_id.id,
            'date': self.date,
            'ref': self.ref,
            'company_id': self.journal_id.intercompany_company_id.id or False,
            'line_ids': li,
            'intercompany_id': self.id,

        }

        move_id = move_obj.sudo().create(vals)
        move_id.sudo().action_post()
        self.move_intercompany_id = move_id


        return move_id

    def inter_company_outbound(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.inter_company_receivable_id.id,
            # 'partner_id': self.partner_id.id,
            'debit': self.amount,
            'currency_id': self.currency_id.id or False,
            # 'amount_currency': self.amount_inter_company_currency_debit() or False,
            'company_id': self.journal_id.intercompany_company_id.id or False,

        }
        li.append((0, 0, debit_val))
        credit_val = {

            # 'move_id': approval_object.move_id.id,
            'name': self.ref,
            'account_id': self.journal_id.inter_company_current_asset_id.id,
            # 'partner_id': self.partner_id.id,
            'credit': self.amount or False,
            'currency_id': self.currency_id.id or False,
            # 'amount_currency': self.amount_inter_company_currency_credit() or False,
            'company_id': self.journal_id.intercompany_company_id.id or False,
            # 'analytic_account_id': ,
            # 'company_id': self.journal_id.intercompany_company_id.id or False,

        }
        li.append((0, 0, credit_val))
        print("List", li)
        vals = {
            'journal_id': self.journal_id.intercompany_journal_id.id,
            'date': self.date,
            'ref': self.ref,
            'company_id': self.journal_id.intercompany_company_id.id or False,
            'line_ids': li,
            'intercompany_id': self.id,

        }
        move_id = move_obj.sudo().create(vals)
        move_id.sudo().action_post()
        self.move_intercompany_id = move_id
        return move_id

    def post_custom(self):
        if self.amount <= 0:
            raise ValidationError(_('Please Insert applicable amount !!'))
        if self.check_followup in ['pdc','cdc'] and self.journal_id.type == 'bank':
            if not self.journal_id.out_account and not self.journal_id.in_account:
                raise ValidationError(_('Please Insert Outstanding/ Under Collection Accounts in JOURNAL !!'))
            if self.journal_id.out_account and self.journal_id.in_account:
                if self.payment_type == 'inbound':
                    move_id = self.in_bound_cheque()
                    move_id.action_post()
                    self.move_id = move_id
                    check_id = self._create_cheque_inbound()
                    log_obj = self.env['check.log']
                    log_obj.create({'move_description': 'Cheque is Under Collection ',
                                    'move_id': move_id.id,
                                    'move_date': self.date,
                                    'check_id': check_id.id,
                                    })

                if self.payment_type == 'outbound':
                    move_id = self._create_move_outbound()
                    move_id.action_post()
                    self.move_id = move_id
                    check_id = self._create_cheque_output()

                    log_obj = self.env['check.log']
                    log_obj.create(
                        {
                            'move_description': 'Out Standing Check',
                            'move_id': move_id.id,
                            'move_date': self.date,
                            'check_id': check_id.id,
                            })
            self.state = 'posted'
        if self.check_followup in ['pdc','cdc'] and self.journal_id.type != 'bank':
            raise ValidationError('Please select Journal as a bank type!!')
        if self.check_followup in ['advance']:
            if self.payment_type == 'inbound':
                if not self.journal_id.advance_acc_id:
                    raise ValidationError(_('Please Insert Advance Payment Account/Credit card account inside JOURNAL ACCOUNTING TAP !!'))
                else:
                    move_id = self.move_advance_inbound()
                    move_id.action_post()
                    self.move_id = move_id
                    check_id = self.advance_in_cheque()
                    log_obj = self.env['check.log']
                    log_obj.create({
                                    'move_description': 'Payment In Advance Payment account ',
                                    'move_id': move_id.id,
                                    'move_date': self.date,
                                    'check_id': check_id.id,
                                    })
                    self.state = 'posted'
            if self.payment_type == 'outbound':
                if not self.journal_id.advance_acc_out_id:
                    raise ValidationError(_('Please Insert Advance Payment Account Out inside JOURNAL ACCOUNTING TAP !!'))
                else:
                    move_id = self.move_advance_out()
                    move_id.action_post()
                    self.move_id = move_id
                    check_id = self.advance_out_cheque()
                    log_obj = self.env['check.log']
                    log_obj.create({
                        'move_description': 'Payment Out/ Advance Payment account ',
                        'move_id': move_id.id,
                        'move_date': self.date,
                        'check_id': check_id.id,
                    })
                    self.state = 'posted'

        if self.check_followup in ['direct','credit_card']:
            if self.payment_type == 'inbound':
                if not self.journal_id.default_account_id:
                    raise ValidationError(_('Please Insert default account inside JOURNAL ACCOUNTING TAP !!'))
                else:
                    move_id = self.move_direct_in()
                    move_id.action_post()
                    self.move_id = move_id
                    payment_id = None
                    log_obj = self.env['check.log']
                    log_obj.create({
                                    'move_description': 'Payment In Advance Payment account ',
                                    'move_id': move_id.id,
                                    'move_date': self.date,
                                    })
                    self.state = 'posted'
            if self.payment_type == 'outbound':
                if not self.journal_id.default_account_id:
                    raise ValidationError(_('Please Insert default inside JOURNAL ACCOUNTING TAP !!'))
                else:
                    move_id = self.move_direct_out()
                    move_id.action_post()
                    self.move_id = move_id
                    payment_id = None
                    log_obj = self.env['check.log']
                    log_obj.create({
                        'move_description': 'Payment Out/ Advance Payment account ',
                        'move_id': move_id.id,
                        'move_date': self.date,
                    })
                    self.state = 'posted'

        # if self.partial_payment:
        #     self.action_create_payments()

        if self.is_inter_company == True and self.payment_type == 'inbound':
            if not self.journal_id.inter_company_current_asset_id and not self.journal_id.inter_company_payable_id:
                raise ValidationError(_('Please Insert Inter company Accounts Current A/C/Payable  JOURNAL !!'))
            else:
                # inter-company additional Inbound JV
                self.inter_company_inbound()
                # move_id2.sudo().action_post()
                # self.move_intercompany_id = move_id2

        if self.is_inter_company == True and self.payment_type == 'outbound':
            if not self.journal_id.inter_company_receivable_id and not self.journal_id.inter_company_current_asset_id:
                raise ValidationError(_('Please Insert Inter company Accounts Receivable/Current A/C  JOURNAL !!'))
            else:
                # inter-company additional Outbound JV
                self.inter_company_outbound()
                # move_id2.sudo().action_post()
                # self.move_intercompany_id = move_id2

    # @api.model
    # def get_inter_company_currency(self):
    #     if self.currency_id != self.journal_id.intercompany_company_id.currency_id:
    #         return self.currency_id.id

    # @api.model
    # def amount_inter_company_currency_credit(self):
    #     if self.currency_id != self.journal_id.intercompany_company_id.currency_id:
    #         return self.amount * -1
    #
    # @api.model
    # def amount_inter_company_currency_debit(self):
    #     if self.currency_id != self.journal_id.intercompany_company_id.currency_id:
    #         return self.amount
    #
    # @api.model
    # def get_inter_company_amount(self):
    #     if self.currency_id != self.journal_id.intercompany_company_id.currency_id:
    #         return self.amount / self.currency_id.rate
    #     if self.currency_id == self.journal_id.intercompany_company_id.currency_id:
    #         return self.amount



    def _get_liquidity_move_line_vals(self, amount):
        name = self.ref
        if self.payment_type == 'transfer':
            name = _('Transfer to %s') % self.destination_journal_id.name
        if self.payment_type == 'outbound' and self.check_followup == 'pdc':
            vals = {
                'ref': name,
                'account_id': self.journal_id.out_account.id,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
                'name': self.ref,
            }
        if self.payment_type == 'inbound' and self.check_followup == 'pdc':
            vals = {
                'ref': name,
                'account_id': self.journal_id.in_account.id,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
                'name': self.ref,
            }
        if self.check_followup == 'pdc':
            vals = {
            'name': name,
            'account_id': self.payment_type in ('outbound','transfer') and self.journal_id.default_account_id.id or self.journal_id.default_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        # If the journal has a currency specified, the journal item need to be expressed in this currency
        if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
            amount = self.currency_id._convert(amount, self.journal_id.currency_id, self.company_id, self.payment_date or fields.Date.today())
            debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(date=self.payment_date)._compute_amount_fields(amount, self.journal_id.currency_id, self.company_id.currency_id)
            vals.update({
                'amount_currency': amount_currency,
                'currency_id': self.journal_id.currency_id.id,
            })
        return vals


