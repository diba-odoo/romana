# -*- coding: utf-8 -*-

{
	'name': "Print Dynamic Cheque",
	"author": "Edge Technologies",
	'version': "15.0.1.0",
	"live_test_url":'https://youtu.be/IIJ-Lu1S0_0',
	"images":['static/description/main_screenshot.png'],
	'summary': "Print Dynamic Cheque Print Dynamic Cheque Print Dynamic Bank Check Print Bank Check Print Cheque Bank Cheque Account Cheque Generate Dynamic Cheque Check Writing Print Check Dynamically Cheque Format Check Print Bank Print PDC Check Printing Cheque Printing",
	'description': """
						Dynamic Cheque Cheque Print Dynamic Cheque Print Odoo Dynamic Cheque Odoo Dynamic Cheque Print
     dynamic check
dynamic bank check
bank check print
print bank check
bank cheque print
print bank cheque
odoo cheque
odoo bank cheque
cheque print
account cheque
generate Dynamic cheque
Odoo Dynamic Bank Cheque Print
Dynamic Print Cheque - Check writing
print cheque/check dynamically
Cheque format
Odoo 12 Dynamic Cheque Print
cheque different bank
odoo Dynamic Bank Check Print
print check
print cheque
print bank cheque
print bank check




					""",
    "license" : "OPL-1",
    'depends': ['base','account','account_check_printing'],
	'data': [
			'security/ir.model.access.csv',
			'data/cheque_format_data.xml',
			'reports/dynamic_cheque_report_templete.xml',
			'wizard/print_dynamic_cheque_wizard_view.xml',
			'views/dynamic_cheque_view.xml',
			],
	'installable': True,
	'auto_install': False,
	'application': False,
	"price": 22,
	"currency": 'EUR',
	'category': "Accounting",
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
