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

from osv import fields, osv
from tools.translate import _


class sale_order(osv.osv):

    _inherit = 'sale.order'

    def _get_last_sequence(self, cr, uid, order, context=None):
        """ Get the last sequence number of the lines
        """
        if context is None:
            context = {}
        seq = 0
        for line in order.order_line:
            if seq < line.sequence:
                seq = line.sequence
        return seq


class sale_order_line(osv.osv):
    """ Hierarchical sale order lines

    """
    _inherit = "sale.order.line"

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'parent_id': fields.many2one('sale.order.line', string="Parent"),
        'child_id': fields.one2many(
            'sale.order.line', 'parent_id', string='Childs'),
        'parent_left': fields.integer(string='Left Parent', select=1),
        'parent_right': fields.integer(string='Right Parent', select=1),
        #'type': fields.selection([
        #    ('view','View'),
        #    ('normal','Normal'),
        #], 'Category Type'),
        'sequence': fields.integer(
            string=_('Sequence'), select=True,
            help=_("Gives the sequence order when displaying a list of sale order lines.")),
    }

#    _defaults = {
#        'type' : lambda *a : 'normal',
#    }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute(
                'select distinct parent_id from sale_order_line where id IN %s',
                (tuple(ids),))
            ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    _constraints = [
        (
            _check_recursion,
            _('Error ! You cannot create recursive order lines.'),
            ['parent_id']
        )
    ]

    def child_get(self, cr, uid, ids):
        return [ids]

    def add_spare_parts(self, cr, uid, ids, context=None):
        """ Add spare parts for each product in each order lines

        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        partner_obj = self.pool.get('res.partner')

        for line in self.browse(cr, uid, ids, context=context):
            if not line.product_id:
                continue
            if not line.order_id:
                continue
            order = line.order_id
            product = product_obj.browse(cr, uid, line.product_id.id,
                                         context=context)
            product_price_unit = line.price_unit
            new_line_ids = []
            for spare in product.spare_part_ids:
                spare_product = spare.product_id

                if context.get('partner_id', False):
                    context['lang'] = partner_obj.browse(
                        cr, uid, context.get('partner_id', False),
                        context=context).lang or False

                order_line_vals = self.product_id_change(
                    cr, uid, [],
                    order.pricelist_id.id,
                    spare_product.id,
                    partner_id=order.partner_id.id,
                    qty=spare.product_uom_qty,
                    uom=spare.product_uom_id.id,
                    qty_uos=spare.product_uos_qty,
                    uos=spare.product_uos_id.id,
                    context=context)['value']

                if product.spare_parts_pricing_policy == 'add_zeroing':
                    price_unit = 0.00
                    product_price_unit += order_line_vals['price_unit'] * spare.product_uom_qty
                elif product.spare_parts_pricing_policy == 'included_zeroing':
                    price_unit = 0.00
                elif product.spare_parts_pricing_policy == 'normal':
                    price_unit = order_line_vals['price_unit']

                order_line_vals.update({
                    'name': product_obj.name_get(cr, uid, [spare_product.id],
                                                context=context)[0][1],
                    'order_id': order.id,
                    'product_id': spare_product.id,
                    # Giving ancestor to enable cascade deletion
                    'parent_id': line.id,
                    'price_unit': price_unit,
                    #'parent_left': line.id,
                    'product_uom_qty': spare.product_uom_qty * line.product_uom_qty,
                    'product_uos_qty': spare.product_uom_qty * line.product_uos_qty,
                })

                tax_ids = []
                for tax in product.taxes_id:
                    tax_ids.append(tax.id)
                order_line_vals.update({
                    'tax_id': [(6, 0, tax_ids)],
                })
                new_line_id = self.create(cr, uid, order_line_vals, context)
                #line_id = self.copy(cr, uid, new_line_id, default=None, context=context)
                #self.unlink(cr, uid, new_line_id, context=context)
                new_line_ids.append(new_line_id)

            if new_line_ids:
                self.write(cr, uid, [line.id], {
                    'child_id': [(6, 0, new_line_ids)],
                    'price_unit': product_price_unit,
                })

        return True

    def product_id_change(
            self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, context=None):
        """ Add the produc spare parts dexcription if in order mode
        """
        context = context or {}
        product_obj = self.pool.get('product.product')
        value = super(sale_order_line, self).product_id_change(
            cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order,
            packaging=packaging, fiscal_position=fiscal_position, flag=flag,
            context=context)
        result = value['value']
        if not product:
            return value
        product = product_obj.browse(cr, uid, product, context=context)
        spare_parts_creation_policy = product.spare_parts_creation_policy
        if spare_parts_creation_policy == 'picking':
            result['name'] = result['name'] + "\n" + product.description_spare_parts
            value['value'].update(result)
        return value

    def create(self, cr, uid, vals, context=None):
        """ Changes from original method:

        Create each order lines relative to the product's spare parts
            relative to the current sale order line creation

        Manage hierarchical copy to keep right relation the newly created order

        """
        context = context or {}
        order_obj = self.pool.get('sale.order')
        product_obj = self.pool.get('product.product')
        context['create_seen'] = True
        order_line_id = super(sale_order_line, self).create(
            cr, uid, vals, context=context)
        order_line = self.browse(cr, uid, order_line_id, context=context)
        order = order_line.order_id
        product = order_line.product_id
        # Get and keep the last sequence to insert +1 into the new line
        last_seq = order_obj._get_last_sequence(cr, uid, order, context=context)
        self.write(cr, uid, [order_line_id], {
            'sequence': last_seq + 1,
        }, context=context)

        if not product:
            return order_line_id

        # Check if a copy has been called on object and so we do not create
        # spare parts only, if product is also oncopy_cascade, do not create
        # spare parts because they've been created during copy already
        spare_parts_creation_policy = product.spare_parts_creation_policy
        # waiting for link between child_id to work
        if not context.get('__copy_data_seen'):
            if spare_parts_creation_policy == 'order':
                # Changing the context partner by order one
                if order.partner_id:
                    context.update({
                        'partner_id': order.partner_id.id,
                    })
                # Add spare parts
                self.add_spare_parts(cr, uid, [order_line_id], context=context)

        # Keep same order id throught sale order line relation
        line = self.browse(cr, uid, order_line_id, context=context)
        sub_line = line
        while sub_line:
            order_id = sub_line.order_id.id
            sub_line = sub_line.parent_id
        if line.parent_id:
            order_id = line.parent_id.order_id.id
        if line.child_id:
            self.write(cr, uid, [c.id for c in line.child_id], {
                'order_id': order_id
            }, context=context)
        self.write(cr, uid, [line.id], {
            'order_id': order_id
        }, context=context)

        return order_line_id

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        parent_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            # Spare part deletion if allowed only in case of parent product
            if line.product_id:
                if line.child_id and line.product_id.ondelete_cascade_ok:
                    child_ids = [s.id for s in line.child_id]
                    self.unlink(cr, uid, child_ids, context=context)
                    ids = list(set(ids) - set(child_ids))

            if not line.product_id or not line.parent_id or not line.parent_id.product_id:
                continue
            parent_ids.append(line.parent_id.id)
            # Unallow spare part deletion without parent deletion
            if not line.parent_id.product_id.spare_parts_deletion_ok and line.id not in ids:
                raise osv.except_osv(
                    _('Warning !'),
                    _("You are trying to delete a child line, try deleting parent first. Or configure the parent product to allow individual spare part deletion."))

        res = super(sale_order_line, self).unlink(cr, uid, ids, context=context)

        # Recalculate price of parent product if needed
        if parent_ids:
            self.add_zeroing_price_calculation(cr, uid, list(set(parent_ids)), context=context)

        return res

    def add_zeroing_price_calculation(self, cr, uid, ids, context=None):
        """ Called by write !

        """
        context = context or {}
        res = dict([(id_, .0) for id_ in ids])
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id
            parent_price_unit = line.product_id.list_price

            for sline in line.child_id:
                sproduct_price_unit = {}
                if product.spare_parts_pricing_policy == 'add_zeroing':
                    parent_price_unit += sline.product_id.list_price * (sline.product_uom_qty / line.product_uom_qty)
                    sproduct_price_unit['price_unit'] = 0.00
                elif product.spare_parts_pricing_policy == 'included_zeroing':
                    sproduct_price_unit['price_unit'] = 0.00
                elif product.spare_parts_pricing_policy == 'normal':
                    continue
                else:
                    continue
                super(sale_order_line, self).write(
                    cr, uid, [sline.id], sproduct_price_unit, context=context)
            super(sale_order_line, self).write(cr, uid, [line.id], {
                'price_unit': parent_price_unit,
            })
            res[line.id] = parent_price_unit
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        res = super(sale_order_line, self).write(cr, uid, ids, vals, context=context)
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id and line.child_id:
                # Recalculate price of parent product if needed
                self.add_zeroing_price_calculation(
                    cr, uid, [line.id], context=context)
        return res

