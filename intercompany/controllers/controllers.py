# -*- coding: utf-8 -*-
from odoo import http

# class Intercompany(http.Controller):
#     @http.route('/intercompany/intercompany/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/intercompany/intercompany/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('intercompany.listing', {
#             'root': '/intercompany/intercompany',
#             'objects': http.request.env['intercompany.intercompany'].search([]),
#         })

#     @http.route('/intercompany/intercompany/objects/<model("intercompany.intercompany"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('intercompany.object', {
#             'object': obj
#         })