# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import ValidationError


class PharmacyDispenseWizardSafeConfirm(models.TransientModel):
    _inherit = 'pharmacy.dispense.wizard'

    def _spx_prescribed_qty(self, line):
        return getattr(line, 'qty_prescribed', 0.0) or getattr(line, 'quantity', 0.0) or getattr(line, 'product_uom_qty', 0.0) or 0.0

    def _spx_dispensed_qty(self, line):
        return getattr(line, 'qty_dispensed', 0.0) or 0.0

    def _spx_remaining_qty(self, line):
        if 'qty_remaining' in line._fields:
            remaining = getattr(line, 'qty_remaining', 0.0)
            if remaining is not False and remaining is not None:
                return remaining
        return max(self._spx_prescribed_qty(line) - self._spx_dispensed_qty(line), 0.0)

    def action_confirm_dispense(self):
        for wizard in self:
            prescription = wizard.prescription_id
            if not prescription:
                raise ValidationError(_("No prescription selected."))

            if not getattr(prescription, 'line_ids', False):
                raise ValidationError(_("Please add medication lines before dispensing."))

            dispensed_now = []
            for line in prescription.line_ids:
                if not getattr(line, 'product_id', False):
                    continue

                qty = wizard._spx_remaining_qty(line)
                if qty <= 0:
                    continue

                if 'qty_dispensed' in line._fields:
                    line.sudo().write({'qty_dispensed': wizard._spx_dispensed_qty(line) + qty})

                if 'qty_remaining' in line._fields:
                    prescribed = wizard._spx_prescribed_qty(line)
                    new_dispensed = getattr(line, 'qty_dispensed', 0.0) or 0.0
                    line.sudo().write({'qty_remaining': max(prescribed - new_dispensed, 0.0)})

                dispensed_now.append((line, qty))

            if not dispensed_now:
                raise ValidationError(_("There are no remaining quantities to dispense."))

            # Create dispensing log if present
            if 'pharmacy.dispensing.log' in self.env:
                Log = self.env['pharmacy.dispensing.log'].sudo()
                vals = {'prescription_id': prescription.id}

                if 'patient_id' in Log._fields and getattr(prescription, 'patient_id', False):
                    vals['patient_id'] = prescription.patient_id.id
                if 'pharmacist_initials' in Log._fields:
                    vals['pharmacist_initials'] = getattr(wizard, 'pharmacist_initials', '') or ''
                if 'notes' in Log._fields:
                    vals['notes'] = getattr(wizard, 'notes', '') or 'Prescription dispensed from confirmation popup.'

                log = Log.create(vals)

                if 'pharmacy.dispensing.log.line' in self.env:
                    LogLine = self.env['pharmacy.dispensing.log.line'].sudo()
                    for pline, qty in dispensed_now:
                        line_vals = {}
                        if 'log_id' in LogLine._fields:
                            line_vals['log_id'] = log.id
                        if 'prescription_line_id' in LogLine._fields:
                            line_vals['prescription_line_id'] = pline.id
                        if 'product_id' in LogLine._fields and getattr(pline, 'product_id', False):
                            line_vals['product_id'] = pline.product_id.id
                        if 'qty_dispensed' in LogLine._fields:
                            line_vals['qty_dispensed'] = qty
                        elif 'quantity' in LogLine._fields:
                            line_vals['quantity'] = qty
                        if line_vals:
                            LogLine.create(line_vals)

            if 'pharmacist_initials' in prescription._fields:
                prescription.sudo().write({'pharmacist_initials': getattr(wizard, 'pharmacist_initials', '') or ''})

            if 'state' in prescription._fields:
                still_remaining = any((wizard._spx_remaining_qty(line) or 0.0) > 0 for line in prescription.line_ids)
                prescription.sudo().write({'state': 'partially_dispensed' if still_remaining else 'dispensed'})

            prescription.message_post(body=_("Prescription dispensed. Dispensing log created."))

        return {'type': 'ir.actions.act_window_close'}
