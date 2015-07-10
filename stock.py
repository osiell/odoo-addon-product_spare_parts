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

class stock_picking(osv.osv):

    _inherit = 'stock.picking'

    def _get_last_sequence(self, cr, uid, picking, context=None):
        """ Get the last sequence number of the lines
        """
        if context is None:
            context = {}
        seq = 0
        for line in picking.move_lines:
            if seq < line.sequence:
                seq = line.sequence
        return seq



class stock_move(osv.osv):
    """ Hierarchical stock_move

    """
    _inherit = "stock.move"

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
        'parent_id': fields.many2one('stock.move', string="Parent"),
        'child_id': fields.one2many(
            'stock.move', 'parent_id', string='Childs'),
        'parent_left': fields.integer(string='Left Parent', select=1),
        'parent_right': fields.integer(string='Right Parent', select=1),
        #'type': fields.selection([
        #    ('view','View'),
        #    ('normal','Normal'),
        #], 'Category Type'),
        'sequence': fields.integer(
            string='Sequence', select=True,
            help="Gives the sequence order when displaying a list of stock moves."),
    }

#    _defaults = {
#        'type' : lambda *a : 'normal',
#    }

    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute(
                'select distinct parent_id from stock_move where id IN %s',
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
            _('Error ! You cannot create recursive moves.'),
            ['parent_id']
        )
    ]

    def child_get(self, cr, uid, ids):
        return [ids]

    #def child_get(self, cr, uid, ids, context=None):
    #    """ Returns all childs

    #    """
    #    if context is None:
    #        context = {}
    #    res = dict([(id_, []) for id_ in ids])
    #    for line in self.browse(cr, uid, ids, context=context):
    #        res[line.id] = [l.id for l in line.child_id]
    #    return res

    def _add_spare_parts(self, cr, uid, ids, context=None):
        """ Add spare parts for each product in each order lines

        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        partner_obj = self.pool.get('res.partner')

        for move in self.browse(cr, uid, ids, context=context):
            if not move.product_id:
                continue
            if not move.picking_id:
                continue
            product = product_obj.browse(
                cr, uid, move.product_id.id, context=context)
            product_price_unit = 0.00
            for spare in product.spare_part_ids:
                spare_product = spare.product_id

                if context.get('partner_id', False):
                    context['lang'] = partner_obj.browse(
                        cr, uid, context.get('partner_id', False),
                        context=context).lang or False

                move_vals = self.onchange_product_id(
                    cr, uid, ids, prod_id=product.id,
                    loc_id=move.location_id.id,
                    loc_dest_id=move.location_dest_id.id,
                    partner_id=move.partner_id.id)

                move_vals['value'].update({
                    'name': product_obj.name_get(cr, uid, [spare_product.id],
                                                context=context)[0][1],
                    'picking_id': move.picking_id.id,
                    'product_id': spare_product.id,
                    # Giving ancestor to enable cascade deletion
                    'parent_id': move.id,
                    'product_qty': spare.product_uom_qty * move.product_qty,
                    'product_uos_qty': spare.product_uom_qty * move.product_uos_qty,
                })
                self.create(cr, uid, move_vals['value'], context)

        return True

    def create(self, cr, uid, vals, context=None):
        """ Changes from original method:

        20120729 - Create each order lines relative to the product's spare parts
            relative to the current sale order line creation

        """
        if context is None:
            context = {}

        picking_obj = self.pool.get('stock.picking')
        move_id = super(stock_move, self).create(cr, uid, vals,
                                                 context=context)
        move = self.browse(cr, uid, move_id, context=context)
        picking = move.picking_id
        if picking:
            # Get and keep the last sequence to insert +1 into the new line
            last_seq = picking_obj._get_last_sequence(cr, uid, picking, context=context)
            self.write(cr, uid, [move_id], {
                'sequence': last_seq + 1,
            }, context=context)
        if not move.product_id:
            return move_id

        # Check if a copy has been called on object and so we do not create
        # spare parts only, if product is also oncopy_cascade, do not create
        # spare parts because they've been created during copy already
        spare_parts_creation_policy = move.product_id.spare_parts_creation_policy
        if not context.get('__copy_data_seen'):
            if spare_parts_creation_policy == 'picking':

                # Changing the context partner by order one
                if move.picking_id and move.picking_id.partner_id:
                    context.update({
                        'partner_id': move.picking_id.partner_id.id,
                    })
                # Add spare parts
                self._add_spare_parts(cr, uid, [move_id], context=context)

        # Keep same order id throught move relation
        move = self.browse(cr, uid, move_id, context=context)
        sub_move = move
        while sub_move:
            picking_id = sub_move.picking_id.id
            sub_move = sub_move.parent_id
        if move.parent_id:
            picking_id = move.parent_id.picking_id.id
        if move.child_id:
            self.write(cr, uid, [c.id for c in move.child_id], {
                'picking_id': picking_id
            }, context=context)
        self.write(cr, uid, [move.id], {
            'picking_id': picking_id
        }, context=context)

        return move_id

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for move in self.browse(cr, uid, ids, context=context):
            if not move.product_id or not move.parent_id or not move.parent_id.product_id:
                continue
            # Unallow spare part deletion without parent deletion
            if not move.parent_id.product_id.spare_part_deletion_ok:
                raise osv.except_osv(
                    _('Warning !'),
                    _("You are trying to delete a child move, try deleting parent first. Or configure the parent product to allow individual spare part deletion."))
            # Spare part deletion if allowed
            if move.child_id and not move.parent_id.product_id.ondelete_cascade_ok:
                self.unlink(cr, uid, [s.id for s in move.child_id])

        return super(stock_move, self).unlink(cr, uid, ids, context=context)
