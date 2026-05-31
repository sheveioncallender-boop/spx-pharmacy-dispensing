# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PharmacyDispensingLog(models.Model):
    _name = 'pharmacy.dispensing.log'
    _description = 'Immutable Pharmacy Dispensing Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'dispense_date desc, name desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    prescription_id = fields.Many2one('pharmacy.prescription', required=True, tracking=True, ondelete='restrict')
    patient_id = fields.Many2one(related='prescription_id.patient_id', store=True, readonly=True)
    doctor_id = fields.Many2one(related='prescription_id.doctor_id', store=True, readonly=True)
    pharmacist_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, tracking=True)
    pharmacist_initials = fields.Char(required=True, tracking=True)
    dispense_date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    line_ids = fields.One2many('pharmacy.dispensing.log.line','dispensing_log_id', required=True)
    notes = fields.Text()
    state = fields.Selection([('posted','Posted'),('void','Voided')], default='posted', tracking=True)
    void_reason = fields.Text(readonly=True)
    register_type = fields.Selection([('general','General'),('antibiotic','Antibiotic'),('controlled','Controlled Drug'),('narcotic','Narcotic')], compute='_compute_register_type', store=True)

    @api.depends('line_ids.register_type')
    def _compute_register_type(self):
        priority = {'narcotic':4,'controlled':3,'antibiotic':2,'general':1}
        for rec in self:
            rec.register_type = max(rec.line_ids.mapped('register_type') or ['general'], key=lambda x: priority.get(x,0))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name','New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.dispensing.log') or 'New'
        records = super().create(vals_list)
        records._sync_prescription_state()
        records._create_register_entries()
        records._create_stock_moves()
        return records

    def write(self, vals):
        protected = set(vals) & {'prescription_id','patient_id','line_ids','dispense_date','pharmacist_initials'}
        if protected and not self.env.user.has_group('spx_pharmacy_dispensing.group_pharmacy_manager'):
            raise UserError(_('Dispensing logs are auditable records and cannot be edited by this user. Void the log with a reason instead.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(_('Dispensing logs cannot be deleted. Void them instead for audit compliance.'))

    def action_void(self):
        return {'type':'ir.actions.act_window','name':'Void Dispensing Log','res_model':'pharmacy.audit.reason.wizard','view_mode':'form','target':'new','context':{'default_model_name': self._name, 'default_res_id': self.id, 'default_action_type':'void_dispensing'}}

    def _sync_prescription_state(self):
        for log in self:
            rx = log.prescription_id
            if all(l.qty_remaining <= 0 for l in rx.line_ids):
                rx.state = 'dispensed'
            elif any(l.qty_dispensed > 0 for l in rx.line_ids):
                rx.state = 'partially_dispensed'

    def _create_register_entries(self):
        Register = self.env['pharmacy.drug.register']
        for log in self:
            for line in log.line_ids.filtered(lambda l: l.register_type in ('antibiotic','controlled','narcotic')):
                Register.create({
                    'dispensing_log_id': log.id, 'prescription_id': log.prescription_id.id, 'patient_id': log.patient_id.id,
                    'doctor_id': log.doctor_id.id, 'product_id': line.product_id.id, 'register_type': line.register_type,
                    'qty_supplied': line.qty_dispensed, 'qty_remaining': line.qty_remaining_after, 'pharmacist_initials': log.pharmacist_initials,
                    'dispense_date': log.dispense_date, 'lot_id': line.lot_id.id if line.lot_id else False,
                })

    def _create_stock_moves(self):
        StockMove = self.env['stock.move']
        stock_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        picking_type = self.env.ref('stock.picking_type_out', raise_if_not_found=False)
        if not stock_location or not customer_location:
            return
        for log in self:
            for line in log.line_ids:
                move = StockMove.create({
                    'name': '%s - %s' % (log.name, line.product_id.display_name),
                    'product_id': line.product_id.id, 'product_uom_qty': line.qty_dispensed,
                    'product_uom': line.product_id.uom_id.id, 'location_id': stock_location.id,
                    'location_dest_id': customer_location.id, 'origin': log.prescription_id.name,
                    'picking_type_id': picking_type.id if picking_type else False,
                })
                # Lot reservation can be completed manually if stricter FEFO batch picking is required.
                move._action_confirm(); move._action_assign()
                try:
                    move.quantity = line.qty_dispensed
                    move._action_done()
                except Exception:
                    log.message_post(body=_('Stock move created but automatic validation failed. Please validate manually: %s') % move.display_name)

class PharmacyDispensingLogLine(models.Model):
    _name = 'pharmacy.dispensing.log.line'
    _description = 'Dispensing Log Line'

    dispensing_log_id = fields.Many2one('pharmacy.dispensing.log', required=True, ondelete='cascade')
    prescription_line_id = fields.Many2one('pharmacy.prescription.line', required=True)
    product_id = fields.Many2one(related='prescription_line_id.product_id', store=True)
    qty_prescribed = fields.Float(related='prescription_line_id.qty_prescribed', readonly=True)
    qty_dispensed = fields.Float(required=True)
    qty_remaining_after = fields.Float(compute='_compute_remaining_after', store=True)
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    expiration_date = fields.Datetime(string='Expiry Date', compute='_compute_expiration_date', readonly=True)

    @api.depends('lot_id')
    def _compute_expiration_date(self):
        # Odoo versions / deployments may expose lot expiry using different field names
        # depending on whether Product Expiry is installed and enabled. Avoid a hard
        # related field so the module installs safely on Odoo 19 Community/CloudPepper.
        possible_fields = ('expiration_date', 'use_date', 'removal_date', 'alert_date')
        for rec in self:
            expiry = False
            lot = rec.lot_id
            if lot:
                for field_name in possible_fields:
                    if field_name in lot._fields:
                        expiry = lot[field_name]
                        if expiry:
                            break
            rec.expiration_date = expiry
    is_refill = fields.Boolean()
    register_type = fields.Selection(related='product_id.product_tmpl_id.pharmacy_drug_type', store=True)

    @api.depends('prescription_line_id.qty_remaining','qty_dispensed')
    def _compute_remaining_after(self):
        for rec in self:
            rec.qty_remaining_after = max((rec.prescription_line_id.qty_remaining or 0) - (rec.qty_dispensed or 0), 0)
