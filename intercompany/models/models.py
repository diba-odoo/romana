# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class intercompany(models.Model):
    _name = 'inter.company'
    _description = 'Inter-Company Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'resource.mixin']

    def _default_company(self):
        return self.env.user.company_id.id

    def _default_curr(self):
        return self.env.user.company_id.currency_id.id

    def _default_user(self):
        return self.env.user.id

    def _default_company_from(self):
        return self.env.user.company_id.id

    name = fields.Char(readonly=True, track_visibility='onchange')
    date = fields.Date('Date',copy=True, track_visibility='onchange',required=True)
    journal_id_from = fields.Many2one('account.journal', string='Journal',required=True,)
    journal_id_to = fields.Many2one('account.journal', string='Journal',)
    ref = fields.Char('Reference',track_visibility='onchange',required=True)
    state = fields.Selection([('draft','Draft'),('transfer','Transfer'),('cancel','Canceled')],default='draft', track_visibility='onchange')
    inter_company_from_ids = fields.One2many('inter.company.from.line','inter_company_from_id',string='Transaction From Lines',copy=False,)
    inter_company_to_ids = fields.One2many('inter.company.to.line','inter_company_to_id',string='Transaction To Lines',copy=False,)

    company_id_from = fields.Many2one('res.company', string='From Company',default=_default_company_from,readonly=True)
    company_id_to = fields.Many2one('res.company', string='To Company',readonly=True)
    purpose = fields.Text('Descriptions',copy=False)
    move_from_id = fields.Many2one('account.move',string='JV From',copy=False)
    move_to_id = fields.Many2one('account.move',string='JV To',copy=False)
    move_from_count = fields.Integer(compute='_compute_from_move')
    move_to_count = fields.Integer(compute='_compute_to_move')
    ict_type = fields.Selection([('fund','Funds'),('payment_bill','Bills Payment')],default='fund',string='Inter-Company Type',required=True)
    bills_id = fields.Many2one('account.move',string="Receiver Bills",
                               domain="[('move_type','=','in_invoice')]",copy=True)
    currency_id = fields.Many2one('res.currency',default=_default_curr,string='Currency',required=True)
    # Related field
    total_amount = fields.Monetary(string='Remaining amount',)
    # Related field
    partner_id = fields.Many2one('res.partner',string='Vendor')
    user_id = fields.Many2one('res.users',default=lambda self: self.env['res.users'].search([('id', '=', self.env.uid)], limit=1),readonly=True)
    total_amount_send = fields.Float(string='Total Sender',compute='_compute_total_sen')
    total_amount_received = fields.Float(string='Total Sender',compute='_compute_total_rec')
    payment_type = fields.Selection([('receive','Receive Money'),
                                     ('send','Send Money')],required=True)
    amount = fields.Monetary(string='Amount',required=True)

    @api.depends('inter_company_from_ids','inter_company_to_ids')
    def _compute_total_sen(self):
        send_total = 0
        for i in self:
            for rec in i.inter_company_from_ids:
                send_total+=rec.debit
            i.total_amount_send = send_total

    @api.depends('inter_company_to_ids')
    def _compute_total_rec(self):
        received_total = 0
        for i in self:
            for rec in i.inter_company_to_ids:
                received_total += rec.credit
            i.total_amount_received = received_total

    @api.depends('company_id_from')
    @api.onchange('company_id_from')
    def onchange_journal_id_from(self):
        myjornalfrom = []
        ins_obj = self.env['account.journal'].search(
            [("company_id", "=", self.company_id_from.id),('is_intercompany','=',True)])
        if ins_obj:
            for ins in ins_obj:
                myjornalfrom.append(ins.id)
        return {'domain': {'journal_id_from': [('id', 'in', myjornalfrom)]}}

    @api.depends('company_id_to')
    @api.onchange('company_id_to')
    def onchange_journal_id_to(self):
        myjornalto = []
        ins_obj = self.env['account.journal'].search(
            [("company_id", "=", self.company_id_to.id),('is_intercompany','=',True)])
        if ins_obj:
            for ins in ins_obj:
                myjornalto.append(ins.id)
        return {'domain': {'journal_id_to': [('id', 'in', myjornalto)]}}

    @api.depends('move_from_id')
    def _compute_from_move(self):
        if self.move_from_id:
            self.move_from_count = 1
        else:
            self.move_from_count = 0

    @api.depends('move_from_id')
    def _compute_to_move(self):
        if self.move_to_id:
            self.move_to_count = 1
        else:
            self.move_to_count = 0

    def action_from_move(self):
        lis = []
        lis.append(self.move_from_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Journal Entry',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'ref_id': self.env.ref('account.view_move_form'),
            'domain': [('id', '=', lis)],
        }

    def action_to_move(self):
        lis = []
        lis.append(self.move_to_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Journal Entry',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'ref_id': self.env.ref('account.view_move_form'),
            'domain': [('id', '=', lis)],
        }

    @api.model
    def create(self, vals):

        vals['name'] = self.env['ir.sequence'].next_by_code('inter.company.code')
        return super(intercompany, self).create(vals)

    # @api.onchange('payment_type','amount')
    def generate_entries(self):
        if self.payment_type == 'receive' and self.amount > 0:
            # JV / Received
            # First From Company JV / Received
            self.company_id_from = self.journal_id_from.company_id.id
            debit_receive_1 = {
                'account_id': self.journal_id_from.default_account_id.id,
                'label':'ICT from '+ str(self.journal_id_from.default_account_id.name) + str(' To ')+ str(self.journal_id_from.inter_company_current_asset_id.name) ,
                'debit': self.amount,
                'inter_company_from_id': self.id,
            }
            credit_receive_1 = {
                'account_id': self.journal_id_from.our_payable_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.default_account_id.name) + str(' To ') + str(
                    self.journal_id_from.inter_company_current_asset_id.name),
                'credit': self.amount,
                'inter_company_from_id': self.id,
            }
            for rec in self.inter_company_from_ids:
                rec.create(debit_receive_1)
                rec.create(credit_receive_1)
            self.env['inter.company.from.line'].create(debit_receive_1)
            self.env['inter.company.from.line'].create(credit_receive_1)

            # Second To Company JV / Received
            self.company_id_to = self.journal_id_from.intercompany_company_id.id
            self.journal_id_to = self.journal_id_from.intercompany_journal_id.id
            debit_receive_2 = {
                'account_id': self.journal_id_from.inter_company_receivable_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.inter_company_current_asset_id.name) + str(' To ') + str(self.journal_id_from.default_account_id.name),
                'debit': self.amount,
                'inter_company_to_id': self.id,

            }
            credit_receive_2 = {
                'account_id': self.journal_id_from.inter_company_current_asset_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.inter_company_current_asset_id.name) + str(' To ') + str(self.journal_id_from.default_account_id.name),
                'credit': self.amount,
                'inter_company_to_id': self.id,

            }
            self.env['inter.company.to.line'].create(debit_receive_2)
            self.env['inter.company.to.line'].create(credit_receive_2)

        if self.payment_type == 'send' and self.amount > 0:
            # JV / Send
            # First From Company JV / Send
            self.company_id_from = self.journal_id_from.company_id.id
            debit_send_1 = {
                'account_id': self.journal_id_from.our_receivable_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.our_receivable_id.name) + str(' To ') + str(
                    self.journal_id_from.default_account_id.name),
                'debit': self.amount,
                'inter_company_from_id': self.id,
            }
            credit_send_1 = {
                'account_id': self.journal_id_from.default_account_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.default_account_id.name) + str(' To ') + str(
                    self.journal_id_from.inter_company_current_asset_id.name),
                'credit': self.amount,
                'inter_company_from_id': self.id,
            }
            for rec in self.inter_company_from_ids:
                rec.create(debit_send_1)
                rec.create(credit_send_1)
            self.env['inter.company.from.line'].create(debit_send_1)
            self.env['inter.company.from.line'].create(credit_send_1)

            # Second To Company JV / Send
            self.company_id_to = self.journal_id_from.intercompany_company_id.id
            self.journal_id_to = self.journal_id_from.intercompany_journal_id.id
            debit_send_2 = {
                'account_id': self.journal_id_from.inter_company_current_asset_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.inter_company_current_asset_id.name) + str(
                    ' To ') + str(self.journal_id_from.default_account_id.name),
                'debit': self.amount,
                'inter_company_to_id': self.id,

            }
            credit_send_2 = {
                'account_id': self.journal_id_from.inter_company_payable_id.id,
                'label': 'ICT from ' + str(self.journal_id_from.inter_company_current_asset_id.name) + str(
                    ' To ') + str(self.journal_id_from.default_account_id.name),
                'credit': self.amount,
                'inter_company_to_id': self.id,

            }
            self.env['inter.company.to.line'].create(debit_send_2)
            self.env['inter.company.to.line'].create(credit_send_2)

    # @api.one
    def post_entry(self):
        li =[]
        li_to = []
        account_move_object = self.env['account.move']
        # Create From Journal Entry
        if self.total_amount_send != self.total_amount_received:
            raise ValidationError('Please be sure amount foe Sender company equal to amount receiving company!!')
        if not self.inter_company_to_ids:
            raise ValidationError('Please filling Receiver Company JV !!')
        if not self.inter_company_from_ids:
            raise ValidationError('Please filling Sender Company JV !!')
        if not self.inter_company_from_ids and not self.inter_company_to_ids:
            raise ValidationError('Please Press Generate Entries first to make JV !!')
        # Post Sender JV
        for d in self.inter_company_from_ids:
            if self.company_id_from != self.journal_id_from.company_id:
                raise ValidationError('Please select Same company for the Journal ' + str(self.journal_id_from.name))

            if d.account_id.company_id != self.journal_id_from.company_id:
                raise ValidationError(
                    'Please select account code for the same company ' + str(self.company_id_from.name) + ' ' +
                    str(d.account_id.name) + ' ' + str(d.account_id.code))

            if d.debit > 0:
                debit_val = {
                    'move_id': self.move_from_id.id,
                    'name': str(d.label)+str(' / ') + str(self.ref),
                    'account_id': d.account_id.id,
                    'debit': d.get_inter_company_send_amount_debit() or False,
                    'analytic_account_id': d.analytic_account_id.id or False,
                    'currency_id': d.currency_id.id or False,
                    'partner_id': d.partner_id.id,
                    'amount_currency': d.amount_inter_company_currency_send_debit() or False,
                    'company_id': self.company_id_from.id or False,

                }
                li.append((0, 0, debit_val))
            if d.credit > 0:
                credit_val = {

                    'move_id': self.move_from_id.id,
                    'name': str(d.label)+str(' / ') + str(self.ref),
                    'account_id': d.account_id.id,
                    'credit': d.get_inter_company_send_amount_credit() or False,
                    'currency_id': d.currency_id.id or False,
                    'partner_id': d.partner_id.id,
                    'amount_currency': d.amount_inter_company_currency_send_credit() or False,
                    'analytic_account_id': d.analytic_account_id.id or False,
                    'company_id': self.company_id_from.id or False,

                }
                li.append((0, 0, credit_val))

        move = {
            'journal_id': self.journal_id_from.id,
            'date': self.date,
            'ref': str(self.name) + str('/ ') + str(self.ref),
            'company_id': self.company_id_from.id,
            'inter_comp_id': self.id,
            'is_ict': True,
            'line_ids': li,
        }
        # raise ValidationError(debit_val.values())
        self.move_from_id = account_move_object.create(move)
        self.move_from_id.action_post()

        # Post Receiver JV
        for d in self.inter_company_to_ids:

            if self.company_id_to != self.journal_id_to.company_id:
                raise ValidationError('Please select Same company for the Journal ' + str(self.journal_id_to.name))

            if d.account_id.company_id != self.journal_id_to.company_id:
                raise ValidationError(
                    'Please select account code for the same company '+str(self.company_id_to.name)+' ' +
                    str(d.account_id.name)+' '+str(d.account_id.code))

            if d.debit > 0:
                debit_val_to = {
                    'move_id': self.move_to_id.id,
                    'name': str(d.label)+str(' / ') + str(self.ref),
                    'account_id': d.account_id.id,
                    'debit': d.get_inter_company_received_amount_debit(),
                    'analytic_account_id': d.analytic_account_id.id or False,
                    'currency_id': d.currency_id.id or False,
                    'partner_id': d.partner_id.id,
                    'amount_currency': d.amount_inter_company_currency_received_debit() or False,
                    'company_id': self.company_id_to.id or False,

                }
                li_to.append((0, 0, debit_val_to))
            if d.credit > 0:
                credit_val_to = {

                    'move_id': self.move_to_id.id,
                    'name': str(d.label)+str(' / ') + str(self.ref),
                    'account_id': d.account_id.id,
                    'credit': d.get_inter_company_received_amount_credit(),
                    'currency_id': d.currency_id.id or False,
                    'partner_id': d.partner_id.id,
                    'amount_currency': d.amount_inter_company_currency_received_credit() or False,
                    'analytic_account_id': d.analytic_account_id.id or False,
                    'company_id': self.company_id_to.id or False,

                }
                li_to.append((0, 0, credit_val_to))

        move_to = {
            'journal_id': self.journal_id_to.id,
            'date': self.date,
            'ref': str(self.name) + str('/ ') + str(self.ref),
            'company_id': self.company_id_to.id,
            'inter_comp_id': self.id,
            'is_ict': True,
            'line_ids': li_to,
        }
        self.move_to_id = account_move_object.create(move_to)
        self.move_to_id.sudo().action_post()
        self.state = 'transfer'

    # @api.one
    def cancel_entry(self):
        # From Cases
        if self.move_from_id and self.move_from_id.state == 'posted':
            self.move_from_id.button_cancel()
            self.move_from_id.unlink()
        if self.move_from_id and self.move_from_id.state != 'posted':
            self.move_from_id.unlink()
        if not self.move_from_id:
            self.state = 'cancel'

        # To cases
        if self.move_to_id and self.move_to_id.state == 'posted':
            self.move_to_id.button_cancel()
            self.move_to_id.unlink()
        if self.move_to_id and self.move_to_id.state != 'posted':
            self.move_to_id.unlink()
        if not self.move_to_id:
            self.state = 'cancel'
        self.state = 'cancel'


class IntercompanyFromLine(models.Model):
    _name = 'inter.company.from.line'
    _description = 'Inter-Company From Line'

    # journal_id = fields.Many2one('account.journal', string='Journal')

    # company_id_related = fields.Char()
    account_id = fields.Many2one('account.account',copy=True,required=True)
    partner_id = fields.Many2one('res.partner',)
    label = fields.Char('Label')
    analytic_account_id = fields.Many2one('account.analytic.account',string='Analytic Account')
    journal_id = fields.Many2one('account.journal',string='Sender Journal',related='inter_company_from_id.journal_id_from')
    currency_id = fields.Many2one('res.currency',related='inter_company_from_id.currency_id',string='Currency')
    debit = fields.Monetary('Debit')
    credit = fields.Monetary('Credit')
    inter_company_from_id = fields.Many2one('inter.company',string="Inter Company")

    @api.onchange('account_id')
    def onchange_account(self):
        myaccount = []
        ins_obj = self.env['account.account'].search(
            [("company_id", "=", self.inter_company_from_id.company_id_from.id)])
        if ins_obj:
            for ins in ins_obj:
                myaccount.append(ins.id)
        return {'domain': {'account_id': [('id', 'in', myaccount)]}}

    # Send
    @api.model
    def get_inter_company_send_currency(self):
        if self.currency_id != self.inter_company_from_id.company_id.currency_id:
            return self.currency_id.id

    @api.model
    def amount_inter_company_currency_send_credit(self):
        if self.currency_id != self.inter_company_from_id.company_id_from.currency_id:
            return self.credit * -1

    @api.model
    def amount_inter_company_currency_send_debit(self):
        if self.currency_id != self.inter_company_from_id.company_id_from.currency_id:
            return self.debit

    @api.model
    def get_inter_company_send_amount_debit(self):
        if self.currency_id != self.inter_company_from_id.company_id_from.currency_id:
            return self.debit / self.currency_id.rate
        else:
            return self.debit

    @api.model
    def get_inter_company_send_amount_credit(self):
        if self.currency_id != self.inter_company_from_id.company_id_from.currency_id:
            return self.credit / self.currency_id.rate
        else:
            return self.credit

    @api.onchange('partner_id')
    def onchange_partner(self):
        mypartner = []
        ins_obj = self.env['res.partner'].search(
            [("company_id", "=", self.inter_company_from_id.company_id_from.id)])
        if ins_obj:
            for ins in ins_obj:
                mypartner.append(ins.id)
        return {'domain': {'partner_id': [('id', 'in', mypartner)]}}

    @api.onchange('analytic_account_id')
    def onchange_analytic(self):
        myanalytic = []
        ins_obj = self.env['account.analytic.account'].search(
            [("company_id", "=", self.inter_company_from_id.company_id_from.id)])
        if ins_obj:
            for ins in ins_obj:
                myanalytic.append(ins.id)
        return {'domain': {'analytic_account_id': [('id', 'in', myanalytic)]}}


class IntercompanyToLine(models.Model):
    _name = 'inter.company.to.line'
    _description = 'Inter-Company To Line'

    # journal_id = fields.Many2one('account.journal', string='Journal')
    account_id = fields.Many2one('account.account', copy=True,required=True)
    partner_id = fields.Many2one('res.partner', )
    label = fields.Char('Label')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    journal_id = fields.Many2one('account.journal',string='Resever Journal',related='inter_company_to_id.journal_id_to')
    currency_id = fields.Many2one('res.currency',related='inter_company_to_id.currency_id',string='Currency')
    debit = fields.Monetary('Debit')
    credit = fields.Monetary('Credit')
    inter_company_to_id = fields.Many2one('inter.company', string="Inter Company")

    # Received
    @api.model
    def get_inter_company_received_currency(self):
        if self.currency_id != self.inter_company_to_id.company_id_to.currency_id:
            return self.currency_id.id

    @api.model
    def amount_inter_company_currency_received_credit(self):
        if self.currency_id != self.inter_company_to_id.company_id_to.currency_id:
            return self.credit * -1

    @api.model
    def amount_inter_company_currency_received_debit(self):
        if self.currency_id != self.inter_company_to_id.company_id_to.currency_id:
            return self.debit

    @api.model
    def get_inter_company_received_amount_credit(self):
        if self.currency_id != self.inter_company_to_id.company_id_to.currency_id:
            return self.credit / self.currency_id.rate
        else:
            return self.credit

    @api.model
    def get_inter_company_received_amount_debit(self):
        if self.currency_id != self.inter_company_to_id.company_id_to.currency_id:
            return self.debit / self.currency_id.rate
        else:
            return self.debit

    # @api.onchange('account_id')
    # def onchange_account(self):
    #     myaccount = []
    #     ins_obj = self.env['account.account'].search(
    #         [("company_id", "=", self.inter_company_to_id.company_id_to.id)])
    #     if ins_obj:
    #         for ins in ins_obj:
    #             myaccount.append(ins.id)
    #     return {'domain': {'account_id': [('id', 'in', myaccount)]}}
    #
    # @api.onchange('partner_id')
    # def onchange_partner(self):
    #     mypartner = []
    #     ins_obj = self.env['res.partner'].search(
    #         [("company_id", "=", self.inter_company_to_id.company_id_to.id)])
    #     if ins_obj:
    #         for ins in ins_obj:
    #             mypartner.append(ins.id)
    #     return {'domain': {'partner_id': [('id', 'in', mypartner)]}}
    #
    # @api.onchange('analytic_account_id')
    # def onchange_analytic(self):
    #     myanalytic = []
    #     ins_obj = self.env['account.analytic.account'].search(
    #         [("company_id", "=", self.inter_company_to_id.company_id_to.id)])
    #     if ins_obj:
    #         for ins in ins_obj:
    #             myanalytic.append(ins.id)
    #     return {'domain': {'analytic_account_id': [('id', 'in', myanalytic)]}}


class AccountJournalInherit(models.Model):
    _inherit = 'account.journal'

    is_intercompany = fields.Boolean('Inter-Company',default=False)
    inter_company_receivable_id = fields.Many2one('account.account',string='Inter Company Receivable',copy=True)
    inter_company_current_asset_id = fields.Many2one('account.account',string='Inter Company Current Asset A/C',copy=True)
    inter_company_payable_id = fields.Many2one('account.account',string='Inter Company Payable A/C',copy=True)
    intercompany_company_id = fields.Many2one('res.company',string='Inter-company Entity')
    intercompany_journal_id = fields.Many2one('account.journal',string='Inter-company Journal')

    our_payable_id = fields.Many2one('account.account',string='Our Inter Company Payable A/C',copy=True)
    our_receivable_id = fields.Many2one('account.account',string='Our Inter Company Receivable',copy=True)

    @api.onchange('intercompany_company_id')
    def onchange_journal(self):
        myaccount = []
        ins_obj = self.env['account.journal'].search([("company_id", "=", self.intercompany_company_id.id)])
        if ins_obj:
            for ins in ins_obj:
                myaccount.append(ins.id)
        return {
            'domain': {'intercompany_journal_id': [('id', 'in', myaccount)]}
        }

    @api.onchange('intercompany_company_id')
    def onchange_current_asset(self):
        myaccount = []
        ins_obj = self.env['account.account'].search(
            [("company_id", "=", self.intercompany_company_id.id)])
        if ins_obj:
            for ins in ins_obj:
                myaccount.append(ins.id)
        return {
            'domain': {'inter_company_current_asset_id': [('id', 'in', myaccount)]}
        }

    @api.onchange('intercompany_company_id')
    def onchange_payable(self):
        myaccount = []
        ins_obj = self.env['account.account'].search(
            [("company_id", "=", self.intercompany_company_id.id)])
        if ins_obj:
            for ins in ins_obj:
                myaccount.append(ins.id)
        return {
            'domain': {'inter_company_payable_id': [('id', 'in', myaccount)]}
        }

    @api.onchange('intercompany_company_id')
    def onchange_receivable(self):
        myaccount = []
        ins_obj = self.env['account.account'].search(
            [("company_id", "=", self.intercompany_company_id.id)])
        if ins_obj:
            for ins in ins_obj:
                myaccount.append(ins.id)
        return {
            'domain': {'inter_company_receivable_id': [('id', 'in', myaccount)]}
        }


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    inter_comp_id = fields.Many2one('inter.company',string='Inter Company Transaction')
    is_ict = fields.Boolean()
    intercompany_id = fields.Many2one('account.payment',string='Inter company Payment')
    state = fields.Selection([('draft','Draft'),
                              ('submitted','Submitted'),
                              ('posted','Posted'),
                              ('cancel','Cancelled')],default='draft')
    is_reversed = fields.Boolean(string='Is Reversed?',)

    def submit_entry(self):
        if self.move_type == 'entry':
            self.state = 'submitted'


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        active_id = self.env['account.move'].browse(self._context.get('active_id'))

        if active_id.is_reversed == True:
            raise ValidationError('Please be informed this entry is revered before !!')

        super(AccountMoveReversal, self).reverse_moves()
        for rec in self.new_move_ids:
            rec.is_reversed = True
        active_id = self.env['account.move'].browse(self._context.get('active_id'))
        if active_id:
            active_id.is_reversed = True


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_inter_company = fields.Boolean(string='Inter company',compute='_compute_flag')
    move_intercompany_id = fields.Many2one('account.move')

    @api.depends('journal_id')
    def _compute_flag(self):
        self.is_inter_company = False
        if self.journal_id.is_intercompany == True:
            self.is_inter_company = True

    def action_intercompany_view(self):

        # if self.is_inter_company == True:
        tree_view_in = self.env.ref('account.view_move_tree')
        form_view_in = self.env.ref('account.view_move_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Inter-Company JV',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(tree_view_in.id, 'tree'), (form_view_in.id, 'form')],
            'domain': [('id', '=', self.move_intercompany_id.id)],

        }

    #
    # def inter_company_inbound(self):
    #     move_obj = self.env['account.move']
    #     li = []
    #     debit_val = {
    #         # 'move_id': self.move_id.id,
    #         'name': self.ref,
    #         'account_id': self.journal_id.inter_company_current_asset_id.id,
    #         # 'partner_id': self.partner_id.id,
    #         'debit': self.get_inter_company_amount(),
    #         'currency_id': self.get_inter_company_currency or False,
    #         'amount_currency': self.amount_inter_company_currency_debit() or False,
    #
    #     }
    #     li.append((0, 0, debit_val))
    #     credit_val = {
    #
    #         # 'move_id': approval_object.move_id.id,
    #         'name': self.ref,
    #         'account_id': self.journal_id.inter_company_payable_id.id,
    #         # 'partner_id': self.partner_id.id,
    #         'credit': self.get_inter_company_amount() or False,
    #         'currency_id': self.get_inter_company_currency() or False,
    #         'amount_currency': self.amount_inter_company_currency_credit() or False,
    #         # 'analytic_account_id': ,
    #         # 'company_id': approval_object.company_id.id or False,
    #
    #     }
    #     li.append((0, 0, credit_val))
    #     print("List", li)
    #     vals = {
    #         'journal_id': self.intercompany_journal_id.id,
    #         'date': self.date,
    #         'ref': self.ref,
    #         'company_id': self.journal_id.intercompany_company_id.id or False,
    #         'line_ids': li,
    #         'intercompany_id': self.id,
    #
    #     }
    #     move_id = move_obj.create(vals)
    #     return move_id
    #
    #
    # def inter_company_outbound(self):
    #     move_obj = self.env['account.move']
    #     li = []
    #     debit_val = {
    #         # 'move_id': self.move_id.id,
    #         'name': self.ref,
    #         'account_id': self.journal_id.inter_company_receivable_id.id,
    #         # 'partner_id': self.partner_id.id,
    #         'debit': self.get_inter_company_amount(),
    #         'currency_id': self.get_inter_company_currency() or False,
    #         'amount_currency': self.amount_inter_company_currency_debit() or False,
    #
    #     }
    #     li.append((0, 0, debit_val))
    #     credit_val = {
    #
    #         # 'move_id': approval_object.move_id.id,
    #         'name': self.ref,
    #         'account_id': self.journal_id.inter_company_current_asset_id.id,
    #         # 'partner_id': self.partner_id.id,
    #         'credit': self.get_inter_company_amount() or False,
    #         'currency_id': self.get_inter_company_currency() or False,
    #         'amount_currency': self.amount_inter_company_currency_credit() or False,
    #         # 'analytic_account_id': ,
    #         # 'company_id': self.journal_id.intercompany_company_id.id or False,
    #
    #     }
    #     li.append((0, 0, credit_val))
    #     print("List", li)
    #     vals = {
    #         'journal_id': self.intercompany_journal_id.id,
    #         'date': self.date,
    #         'ref': self.ref,
    #         'company_id': self.journal_id.intercompany_company_id.id or False,
    #         'line_ids': li,
    #         'intercompany_id': self.id,
    #
    #     }
    #     move_id = move_obj.create(vals)
    #     return move_id

