# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PharmacyDispenseWizard(models.TransientModel):
    _name = 'pharmacy.dispense.wizard'
    _description = 'Dispense Prescription Wizard'

    prescription_id = fields.Many2one('pharmacy.prescription', required=True)
    patient_id = fields.Many2one(related='prescription_id.patient_id', readonly=True)
    pharmacist_initials = fields.Char(required=True)
    notes = fields.Text()
    line_ids = fields.One2many('pharmacy.dispense.wizard.line','wizard_id')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        rx = self.env['pharmacy.prescription'].browse(self.env.context.get('default_prescription_id'))
        if rx:
            res['line_ids'] = [(0,0, {'prescription_line_id': l.id, 'qty_to_dispense': l.qty_remaining}) for l in rx.line_ids if l.qty_remaining > 0]
        return res

    def action_dispense(self):
        self.ensure_one()
        rx = self.prescription_id
        blocking = rx.alert_ids.filtered(lambda a: a.state == 'open' and a.severity in ('high','critical'))
        if blocking and not self.env.user.has_group('spx_pharmacy_dispensing.group_pharmacy_manager'):
            raise UserError(_('This prescription has blocking safety alerts. A Pharmacy Manager must acknowledge/override before dispensing.'))
        lines = []
        for l in self.line_ids.filtered(lambda x: x.qty_to_dispense > 0):
            if l.qty_to_dispense > l.prescription_line_id.qty_remaining:
                raise UserError(_('Cannot dispense more than remaining balance for %s.') % l.prescription_line_id.product_id.display_name)
            lines.append((0,0, {'prescription_line_id': l.prescription_line_id.id, 'qty_dispensed': l.qty_to_dispense, 'lot_id': l.lot_id.id if l.lot_id else False, 'is_refill': l.is_refill}))
        if not lines:
            raise UserError(_('Enter at least one quantity to dispense.'))
        log = self.env['pharmacy.dispensing.log'].create({'prescription_id': rx.id, 'pharmacist_initials': self.pharmacist_initials, 'notes': self.notes, 'line_ids': lines})
        return {'type':'ir.actions.act_window','res_model':'pharmacy.dispensing.log','view_mode':'form','res_id':log.id}

class PharmacyDispenseWizardLine(models.TransientModel):
    _name = 'pharmacy.dispense.wizard.line'
    _description = 'Dispense Prescription Wizard Line'

    wizard_id = fields.Many2one('pharmacy.dispense.wizard', required=True, ondelete='cascade')
    prescription_line_id = fields.Many2one('pharmacy.prescription.line', required=True)
    product_id = fields.Many2one(related='prescription_line_id.product_id', readonly=True)
    qty_remaining = fields.Float(related='prescription_line_id.qty_remaining', readonly=True)
    qty_to_dispense = fields.Float()
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    is_refill = fields.Boolean()
