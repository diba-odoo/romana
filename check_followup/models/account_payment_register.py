from odoo import fields , models,api,tools,_
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError
# from odoo import amount_to_text


class AccountPayment_register(models.TransientModel):
    _inherit = 'account.payment.register'

    check_followup = fields.Selection([('pdc', 'PDC'),
                                       ('cdc', 'CDC'),
                                       ('direct', 'Direct'),
                                       ('credit_card', 'Credit Card')], required=True, string='Payment Type')
    journal_type = fields.Selection(related='journal_id.type')
    payment_type = fields.Selection([('outbound','Outbound'),
                                     ('inbound','Inbound')],compute='_compute_payment_type')
    partner_type = fields.Selection([('customer','Customer'),
                                     ('supplier','Supplier')],compute='_compute_payment_type')
    check_date = fields.Date(string='Cheque Date', copy=False)
    check_number = fields.Char(string='Cheque Number', copy=False)
    cheque_number = fields.Char(string='Cheque Number', copy=False)
    check_count = fields.Integer(compute='_compute_check')
    advance_count = fields.Integer(compute='_compute_advance')
    # check_id = fields.Many2one('check.followup',string='Check Ref')
    debit_line_id = fields.Many2one('account.move.line')
    credit_line_id = fields.Many2one('account.move.line')
    move_id = fields.Many2one('account.move',string='Move')
    payment_type_line_id = fields.Many2one('account.payment.method.line',string='Method')
    inbound_filter = fields.Boolean(compute='_compute_payment_type')
    outbound_filter = fields.Boolean(compute='_compute_payment_type')

    def _compute_payment_type(self):
        active_id = self.env['account.move'].browse(self._context.get('active_id'))
        if active_id.move_type == 'out_invoice':
            self.payment_type = 'outbound'
            self.outbound_filter = True
            self.partner_type = 'supplier'
        if active_id.move_type == 'in_invoice':
            self.payment_type = 'inbound'
            self.inbound_filter = True
            self.partner_type = 'customer'

    def _compute_check(self):
        payment_count = self.env['check.followup'].sudo().search_count([('payment_id','=',self.id)])
        self.check_count = payment_count

    def _compute_advance(self):
        payment_count = self.env['check.followup'].sudo().search_count([('payment_id','=',self.id)])
        self.advance_count = payment_count

    def in_bound_cheque(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
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
            # 'source_document': self.name,
            'memo': self.communication,
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
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
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
            # 'source_document': self.name,
            'memo': self.communication,
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
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def move_direct_in(self):
        move_obj = self.env['account.move']
        li = []
        debit_val = {
            # 'move_id': self.move_id.id,
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
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
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
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
            'name': self.communication,
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
            'name': self.communication,
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
            'date': self.payment_date,
            'ref': self.communication,
            # 'company_id': ,
            'line_ids': li,
        }
        move_id = move_obj.create(vals)
        return move_id

    def advance_in_cheque(self):
        check_obj = self.env['check.followup']
        check_val = {
            'payment_date': self.payment_date,
            'source_document': self.communication,
            'memo': self.communication,
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
            'payment_date': self.payment_date,
            'source_document': self.communication,
            'memo': self.communication,
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

    @api.model
    def get_currency(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.currency_id.id

    @api.model
    def amount_currency_credit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount * -1

    @api.model
    def amount_currency_debit(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount

    @api.model
    def get_amount(self):
        if self.currency_id != self.env.user.company_id.currency_id:
            return self.amount / self.currency_id.rate
        if self.currency_id == self.env.user.company_id.currency_id:
            return self.amount

    def action_create_payments(self):
        #
        #
        # if self.amount <= 0:
        #     raise ValidationError(_('Please Insert applicable amount !!'))
        # if self.check_followup in ['pdc','cdc'] and self.journal_id.type == 'bank':
        #     if not self.journal_id.out_account and not self.journal_id.in_account:
        #         raise ValidationError(_('Please Insert Outstanding/ Under Collection Accounts in JOURNAL !!'))
        #     if self.journal_id.out_account and self.journal_id.in_account:
        #         if self.payment_type == 'inbound':
        #             move_id = self.in_bound_cheque()
        #             move_id.post()
        #             self.move_id = move_id
        #             check_id = self._create_cheque_inbound()
        #             log_obj = self.env['check.log']
        #             log_obj.create({'move_description': 'Check is Under Collection ',
        #                             'move_id': move_id.id,
        #                             'move_date': self.payment_date,
        #                             'check_id': check_id.id,
        #                             })
        #
        #         if self.payment_type == 'outbound':
        #             move_id = self._create_move_outbound()
        #             move_id.post()
        #             self.move_id = move_id
        #             check_id = self._create_cheque_output()
        #
        #             log_obj = self.env['check.log']
        #             log_obj.create(
        #                 {
        #                     'move_description': 'Out Standing Check',
        #                     'move_id': move_id.id,
        #                     'move_date': self.payment_date,
        #                     'check_id': check_id.id,
        #                     })
        #     self.state = 'posted'
        #
        # if self.check_followup in ['advance']:
        #     if self.payment_type == 'inbound':
        #         if not self.journal_id.advance_acc_id:
        #             raise ValidationError(_('Please Insert Advance Payment Account/Credit card account inside JOURNAL ACCOUNTING TAP !!'))
        #         else:
        #             move_id = self.move_advance_inbound()
        #             move_id.post()
        #             self.move_id = move_id
        #             check_id = self.advance_in_cheque()
        #             log_obj = self.env['check.log']
        #             log_obj.create({
        #                             'move_description': 'Payment In Advance Payment account ',
        #                             'move_id': move_id.id,
        #                             'move_date': self.payment_date,
        #                             'check_id': check_id.id,
        #                             })
        #             self.state = 'posted'
        #     if self.payment_type == 'outbound':
        #         if not self.journal_id.advance_acc_out_id:
        #             raise ValidationError(_('Please Insert Advance Payment Account Out inside JOURNAL ACCOUNTING TAP !!'))
        #         else:
        #             move_id = self.move_advance_out()
        #             move_id.post()
        #             self.move_id = move_id
        #             check_id = self.advance_out_cheque()
        #             log_obj = self.env['check.log']
        #             log_obj.create({
        #                 'move_description': 'Payment Out/ Advance Payment account ',
        #                 'move_id': move_id.id,
        #                 'move_date': self.payment_date,
        #                 'check_id': check_id.id,
        #             })
        #             self.state = 'posted'
        #
        # if self.check_followup in ['direct','credit_card']:
        #     if self.payment_type == 'inbound':
        #         if not self.journal_id.default_account_id:
        #             raise ValidationError(_('Please Insert default account inside JOURNAL ACCOUNTING TAP !!'))
        #         else:
        #             move_id = self.move_direct_in()
        #             move_id.post()
        #             self.move_id = move_id
        #             payment_id = None
        #             log_obj = self.env['check.log']
        #             log_obj.create({
        #                             'move_description': 'Payment In Advance Payment account ',
        #                             'move_id': move_id.id,
        #                             'move_date': self.payment_date,
        #                             })
        #             self.state = 'posted'
        #     if self.payment_type == 'outbound':
        #         if not self.journal_id.default_account_id:
        #             raise ValidationError(_('Please Insert default inside JOURNAL ACCOUNTING TAP !!'))
        #         else:
        #             move_id = self.move_direct_out()
        #             move_id.post()
        #             self.move_id = move_id
        #             payment_id = None
        #             log_obj = self.env['check.log']
        #             log_obj.create({
        #                 'move_description': 'Payment Out/ Advance Payment account ',
        #                 'move_id': move_id.id,
        #                 'move_date': self.payment_date,
        #             })
        #             self.state = 'posted'

        payment_vals = {
            'journal_id': self.journal_id.id,
            'check_followup': self.check_followup,
            'amount': self.amount,
            'date': self.payment_date,
            'ref': self.communication,
            'partner_bank_id': self.partner_bank_id.id,
            'check_date': self.check_date,
            'cheque_number': self.cheque_number,
            'partner_id': self.partner_id.id,
            # 'payment_type_line_id': self.payment_type_line_id,
            'payment_type': self.payment_type,
            'move_id': self.move_id.id,
            # 'inbound_filter': self.inbound_filter,
            # 'outbound_filter': self.outbound_filter,
            'partner_type': self.partner_type,
        }

        payment_obj = self.env['account.payment']
        payment_id = payment_obj.sudo().create(payment_vals)
        payment_id.post_custom()
        # Reconcile

        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []
        if edit_mode:
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        if not self.group_payment:
            new_batches = []
            for batch_result in batches:
                for line in batch_result['lines']:
                    new_batches.append({
                        **batch_result,
                        'payment_values': {
                            **batch_result['payment_values'],
                            'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                        },
                        'lines': line,
                    })
            batches = new_batches

        for batch_result in batches:
            to_process.append({
                'create_vals': self._create_payment_vals_from_batch(batch_result),
                'to_reconcile': batch_result['lines'],
                'batch': batch_result,
            })
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_internal_group', 'in', ('receivable', 'payable')),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment_lines = payment_id.line_ids.filtered_domain(domain)
            lines = vals['to_reconcile']

            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                    .reconcile()

