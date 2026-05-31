# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PharmacyDispenseWizard(models.TransientModel):
    _name = 'pharmacy.dispense.wizard'
    _description = 'Dispense Prescription Wizard'

    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription', required=True)
    patient_id = fields.Many2one(related='prescription_id.patient_id', string='Patient', readonly=True)
    pharmacist_initials = fields.Char(string='Pharmacist Initials')
    dispense_date = fields.Datetime(string='Dispense Date', default=fields.Datetime.now)
    line_ids = fields.One2many('pharmacy.dispense.wizard.line', 'wizard_id', string='Dispense Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        prescription_id = self.env.context.get('active_id') or self.env.context.get('default_prescription_id')
        if prescription_id:
            prescription = self.env['pharmacy.prescription'].browse(prescription_id)
            res['prescription_id'] = prescription.id

            command_lines = []
            for line in prescription.line_ids:
                qty_prescribed = getattr(line, 'qty_prescribed', 0.0) or getattr(line, 'quantity', 0.0) or getattr(line, 'product_uom_qty', 0.0) or 0.0
                qty_dispensed = getattr(line, 'qty_dispensed', 0.0) or 0.0
                qty_remaining = getattr(line, 'qty_remaining', False)
                if qty_remaining is False:
                    qty_remaining = max(qty_prescribed - qty_dispensed, 0.0)

                vals = {
                    'prescription_line_id': line.id,
                    'product_id': line.product_id.id if getattr(line, 'product_id', False) else False,
                    'qty_prescribed': qty_prescribed,
                    'qty_dispensed': qty_remaining or qty_prescribed or 0.0,
                    'qty_remaining': qty_remaining,
                }

                if getattr(line, 'lot_id', False):
                    vals['lot_id'] = line.lot_id.id
                if getattr(line, 'instructions', False):
                    vals['instructions'] = line.instructions

                command_lines.append((0, 0, vals))

            res['line_ids'] = command_lines
        return res

    def action_confirm_dispense(self):
        for wizard in self:
            if not wizard.line_ids:
                raise ValidationError(_("There are no medication lines to dispense."))

            for wline in wizard.line_ids:
                if not wline.prescription_line_id:
                    raise ValidationError(_("A dispense line is missing its prescription line link."))

                if wline.qty_dispensed <= 0:
                    continue

                pline = wline.prescription_line_id

                if 'qty_dispensed' in pline._fields:
                    pline.qty_dispensed = (pline.qty_dispensed or 0.0) + wline.qty_dispensed

                if 'qty_remaining' in pline._fields:
                    qty_prescribed = getattr(pline, 'qty_prescribed', 0.0) or getattr(pline, 'quantity', 0.0) or 0.0
                    pline.qty_remaining = max(qty_prescribed - (getattr(pline, 'qty_dispensed', 0.0) or 0.0), 0.0)

                if 'pharmacy.dispensing.log' in self.env:
                    Log = self.env['pharmacy.dispensing.log']
                    log_vals = {'prescription_id': wizard.prescription_id.id}
                    if 'patient_id' in Log._fields and wizard.patient_id:
                        log_vals['patient_id'] = wizard.patient_id.id
                    if 'pharmacist_initials' in Log._fields:
                        log_vals['pharmacist_initials'] = wizard.pharmacist_initials
                    if 'dispense_date' in Log._fields:
                        log_vals['dispense_date'] = wizard.dispense_date
                    elif 'date' in Log._fields:
                        log_vals['date'] = wizard.dispense_date
                    log = Log.create(log_vals)

                    if 'pharmacy.dispensing.log.line' in self.env:
                        LogLine = self.env['pharmacy.dispensing.log.line']
                        line_vals = {}
                        if 'log_id' in LogLine._fields:
                            line_vals['log_id'] = log.id
                        if 'prescription_line_id' in LogLine._fields:
                            line_vals['prescription_line_id'] = pline.id
                        if 'product_id' in LogLine._fields and wline.product_id:
                            line_vals['product_id'] = wline.product_id.id
                        if 'qty_dispensed' in LogLine._fields:
                            line_vals['qty_dispensed'] = wline.qty_dispensed
                        elif 'quantity' in LogLine._fields:
                            line_vals['quantity'] = wline.qty_dispensed
                        if 'lot_id' in LogLine._fields and wline.lot_id:
                            line_vals['lot_id'] = wline.lot_id.id
                        if line_vals:
                            LogLine.create(line_vals)

            if 'state' in wizard.prescription_id._fields:
                remaining = any((getattr(line, 'qty_remaining', 0.0) or 0.0) > 0 for line in wizard.prescription_id.line_ids)
                wizard.prescription_id.state = 'partially_dispensed' if remaining else 'dispensed'

        return {'type': 'ir.actions.act_window_close'}


class PharmacyDispenseWizardLine(models.TransientModel):
    _name = 'pharmacy.dispense.wizard.line'
    _description = 'Dispense Prescription Wizard Line'

    wizard_id = fields.Many2one('pharmacy.dispense.wizard', string='Wizard', required=True, ondelete='cascade')
    prescription_line_id = fields.Many2one('pharmacy.prescription.line', string='Prescription Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.lot', string='Batch/Lot')
    qty_prescribed = fields.Float(string='Qty Prescribed')
    qty_dispensed = fields.Float(string='Qty to Dispense')
    qty_remaining = fields.Float(string='Qty Remaining')
    instructions = fields.Char(string='Instructions')
