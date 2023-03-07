{

    'name': 'Cheque Followup',
    'version': '1.0',
    'author': 'Abdelwhab Alim',
    'data': [
        'security/ir.model.access.csv',
        # 'views/account_view.xml',
        'views/check_followup_view.xml',
        'views/payment_view.xml',
        'views/journal_view.xml',
        'wizard/change_bank_view.xml',
        'report/report.xml',
        'report/report_bank_payment_voucher.xml',
        'report/report_telegraphic_transfer_payment.xml',
        # 'data/data.xml',
        # 'reports/finance_report.xml'
    ],
    'depends': ['account','payment'],

    'installable': True,
    'application': True,
}