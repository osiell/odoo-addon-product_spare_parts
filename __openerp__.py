# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2009-Today OSIELL SARL. (http://osiell.com).
#                       Stéphane Mangin <contact@osiell.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# $Id$
# $Revision$


{
    "name": "Product spare parts",
    "version": "1.1",
    "author": "ABF Osiell SARL",
    "website": "http://www.osiell.com",
    "category": "Specific Modules/Customs",
    'complexity': "easy",
    "depends": ["base", "account", "sale", "stock", ],
    "description": """ Add spare parts to products """,
    "init_xml": [],
    "update_xml": [
        "security/ir.model.access.csv",
        "product_view.xml",
        "sale_view.xml",
        "stock_view.xml",
    ],
    'demo_xml': [
    ],
    'test': [
    ],
    'css': [
    ],
    'images': [
    ],
    'installable': True,
    'active': False,
    'application': True,
    'web': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
