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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class product_spare_part(osv.osv):

    _name = "product.spare.part"
    _description = "Product spare parts association table"

    def _get_uom_id(self, cr, uid, *args):
        return self.pool.get('sale.order.line')._get_uom_id(cr, uid, *args)

    def onchange_product_id(self, cr, uid, ids, product_id, product_qty, context=None):
        """ Return some product properties

        """
        if context is None:
            context = {}
        res = {}
        product_obj = self.pool.get('product.product')
        product = product_obj.browse(cr, uid, product_id, context=context)
        res['value'] = {
            'price_unit': product.lst_price,
            'price_total': product.lst_price * product_qty,
        }
        return res

    def onchange_price_unit(self, cr, uid, ids, price_unit, product_qty, context=None):
        """ Return some product properties

        """
        if context is None:
            context = {}
        res = {}
        product_obj = self.pool.get('product.product')
        product = product_obj.browse(cr, uid, product_id, context=context)
        res['value'] = {
            'price_unit': product.lst_price,
            'price_total': product.lst_price * product_qty,
        }
        return res

    _columns = {
        'ref': fields.related(
            'product_id', 'code', string="Internal reference", type="char"),
        'qty_available': fields.related(
            'product_id', 'qty_available', string="Quantity On Hand"),
        'product_cost': fields.related(
            'product_id', 'list_price', string="Price"),
        'product_price': fields.related(
            'product_id', 'standard_price', string="Cost"),
        'product_id': fields.many2one(
            'product.product', string='Product', required=True),
        'product_parent_id': fields.many2one(
            'product.product', string='Parent product', required=True),
        'product_uom_qty': fields.float(
            string='Quantity (UoM)',
            digits_compute=dp.get_precision('Product UoS')),
        'product_uom_id': fields.related(
            'product_id', 'uom_id', type='many2one', obj='product.uom',
            string='Unit of Measure', readonly=True),
        'product_uos_qty': fields.float(
            string='Quantity (UoS)',
            digits_compute=dp.get_precision('Product UoS')),
        'product_uos_id': fields.related(
            'product_id', 'uos_id', type='many2one', obj='product.uom',
            string=_('Product UoS'), readonly=True),
        'price_unit': fields.float(string="Custom price", digits=(16,3)),
        'price_total': fields.float(
            string="Custom price", digits=(16,3), readonly=True),
    }

    _rec_name = 'product_id'

    _defaults = {
        'product_uom_id': _get_uom_id,
        'product_uom_qty': 1.0,
        'product_uos_qty': 1.0,
    }



class product_product(osv.osv):

    _inherit = "product.product"

    def _get_parent_product(self, cr, uid, ids, field_name, arg, context=None):
        """ Returns related parent products

        """
        context = context or {}
        spare_obj = self.pool.get('product.spare.part')
        res = dict([(id_, []) for id_ in ids])
        for product in self.browse(cr, uid, ids, context=context):
            spare_ids = spare_obj.search(cr, uid, (
                ('product_id', '=', product.id),
            ), context=context)
            for spare in spare_obj.browse(cr, uid, spare_ids, context=context):
                res[id_].append(spare.product_parent_id.id)
        return res

    _columns = {
        'description_spare_parts': fields.text(
            string='Spare parts description', readonly=True,
            help="Injected into the sale order line note when creating spare parts into the pîcking"),
        'spare_part_ids': fields.one2many(
            'product.spare.part', 'product_parent_id', string='Spare parts'),
        'product_parent_ids': fields.function(
            _get_parent_product, type="one2many", obj='product.product',
            string='Parent products'),
        'spare_parts_pricing_policy': fields.selection(
            [
                ('dynamic', 'Dynamic package'),
                ('fixed', 'Fixed package'),
                ('normal', 'Standart method'),
            ], string=_("Spare parts pricing policy"),
            attrs={
                'invisible': [
                    '|', ('spare_part_ids', '!=', False),
                    ('product_parent_ids', '=', False),
                ],
            },
            help=_("""\
Spare parts pricing methods :
    * Add price and zeroing: The sum of spare parts will be added to the final price and zeroing.
    * Included and zeroing: The sum of spare parts will not be added to the final price and zeroing.
    * Standart method: Do nothing more than the standard function. The sum of spare parts will not be added to the final price and zeroing.
            """)),
        'ondelete_cascade_ok': fields.boolean(
            string="While unlinking, also unlink spare parts",
            attrs={
                'invisible': [
                    '|', ('spare_part_ids', '!=', False),
                    ('product_parent_ids', '=', False),
                ],
            },
            help="While unlinking, also unlink all associated spare parts."),
        'spare_parts_deletion_ok': fields.boolean(
            string="Allow individual spare part deletion",
            attrs={
                'invisible': [
                    '|', ('spare_part_ids', '!=', False),
                    ('product_parent_ids', '=', False),
                ],
            },
            help="With this option you're allowed to unlink a product line either while being a spare part."),
        'spare_parts_creation_policy': fields.selection([
            ('order', 'While ordering'),
            ('picking', 'While delivering'),
        ], string=_("Spare parts creation policy"),
        help="Allow you to choose the place where spare parts will be created  :"\
                "\n* While ordering: Spare parts will be created at sale order line creation (Only if relied to a sale order)." \
                "\n* While delivering: Spare parts will be created at stock move creation (Only if relied to a picking)."),
    }

    _defaults = {
        'ondelete_cascade_ok': False,
        'spare_parts_deletion_ok': True,
        'spare_parts_creation_policy': 'order',
        'spare_parts_pricing_policy': 'normal',
    }

    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        try:
            ids[0]
        except IndexError:
            ids = [ids]

        spare_part_obj = self.pool.get('product.spare.part')
        for product in self.browse(cr, uid, ids, context=context):
            spare_part_list = []  # Used for spare parts description construction
            # Product spare parts has been changed
            #=============================================================
#            if vals.has_key('spare_part_ids') and vals['spare_part_ids']:
#
#                # So we recalculate the price and weight of the parent product
#                vals.update({
#                    'cost_price_supplier': 'cost_price_supplier' in vals\
#                            and vals['cost_price_supplier'] or .0,
#                    'list_price': 'list_price' in vals and vals['list_price'] or .0,
#                    'weight': 'weight' in vals and vals['weight'] or .0,
#                    })
#                spare_part_ids = [p.id for p in product.spare_part_ids]
#                for p_assoc in spare_part_obj.browse(cr, uid, spare_part_ids,
#                        context=context):
#                    vals['cost_price_supplier'] += \
#                            p_assoc.product_id.cost_price_supplier * int(p_assoc.product_uom_qty)
#                    vals['list_price']          += \
#                            p_assoc.product_id.list_price * int(p_assoc.product_uom_qty)
#                    vals['weight']              += \
#                            p_assoc.product_id.weight * int(p_assoc.product_uom_qty)
#
#                # La liste des produits associés a été précédemment traitée,
#                # on l'enlève pour éviter les doublons
#                del vals['spare_part_ids']
#
#                # Eviter la remise à zero d'un prix
#                for attr in copy.copy(vals).keys():
#                    if not vals[attr]:
#                        del vals[attr]

            # Constructing spare parts description
            parts_string = self.fields_get(
                cr, uid, ['description_spare_parts'],
                context=context)['description_spare_parts']['string']
            if len(product.spare_part_ids):
                spare_part_list.append('%s :\n' % parts_string)
                for part in product.spare_part_ids:
                    title = "\t- %s x %s\n" % (
                        part.product_uom_qty, part.product_id.name)
                    spare_part_list.append(title)
                #parts_list.append('\n') # Unuseful for a text format

            vals['description_spare_parts'] = ''.join(spare_part_list)
            super(product_product, self).write(
                cr, uid, [product.id], vals, context)

            # Modifying product if a spare part has changed
            spare_part_ids = spare_part_obj.search(cr, uid, [
                ('product_id', '=', product.id), ], context=context)
            if not spare_part_ids:
                continue
            spare_parts = spare_part_obj.browse(
                cr, uid, spare_part_ids, context=context)

            # Filter parent which is not in ids conducting to recursive exception
            parents = [p.product_parent_id for p in spare_parts]
            to_update_parents = [p.id for p in parents if p.id not in ids]
            self.check_recursive_spare_part(cr, uid, product.id, context=context)
            self.write(cr, uid, to_update_parents, {}, context=context)

        return True

    def check_recursive_spare_part(self, cr, uid, id, context=None):
        """ Get all parent hierarchy to check for recursive association

        """
        context = context or {}
        product = self.browse(cr, uid, id, context=context)

        ctx = context
        if not ctx.get('__from_product'):
            ctx = {'__from_product': id}
        elif id == context.get('__from_product'):
            raise osv.except_osv(
                _("Error !"),
                _("You try to create a recursive spare part, which is not possible !")
            )

        for parent_product in product.product_parent_ids:
            self.check_recursive_spare_part(
                cr, uid, parent_product.id, context=ctx)
        return
