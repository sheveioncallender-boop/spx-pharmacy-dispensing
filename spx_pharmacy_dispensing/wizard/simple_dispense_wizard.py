# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PharmacyDispenseWizard(models.TransientModel):
    _name = 'pharmacy.dispense.wizard'
    _description = 'Dispense Prescription Wizard'

    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription', required=True)
    patient_id = fields.Many2one(related='prescription_id.patient_id', string='Patient', readonly=True)
    pharmacist_initials = fields.Char(string='Pharmacist Initials', required=True)
    notes = fields.Text(string='Dispensing Notes')
    medication_summary = fields.Html(string='Medication Summary', compute='_compute_medication_summary', sanitize=False)
    dispense_date = fields.Datetime(string='Dispense Date', default=fields.Datetime.now)

    @api.depends('prescription_id')
    def _compute_medication_summary(self):
        for wizard in self:
            html = """
                <div style="padding:10px;border:1px solid #ddd;border-radius:6px;background:#fafafa;">
                    <strong>No medication lines found.</strong>
                </div>
            """
            prescription = wizard.prescription_id
            if prescription and getattr(prescription, 'line_ids', False):
                rows = []
                for line in prescription.line_ids:
                    product = getattr(line, 'product_id', False)
                    product_name = product.display_name if product else 'Unknown Product'
                    prescribed = (
                        getattr(line, 'qty_prescribed', 0.0)
                        or getattr(line, 'quantity', 0.0)
                        or getattr(line, 'product_uom_qty', 0.0)
                        or 0.0
                    )
                    dispensed = getattr(line, 'qty_dispensed', 0.0) or 0.0
                    remaining = getattr(line, 'qty_remaining', False)
                    if remaining is False or remaining is None:
                        remaining = max(prescribed - dispensed, 0.0)
                    instructions = getattr(line, 'instructions', '') or ''
                    rows.append("""
                        <tr>
                            <td style="padding:7px;border-bottom:1px solid #eee;">%s</td>
                            <td style="padding:7px;border-bottom:1px solid #eee;text-align:right;">%.2f</td>
                            <td style="padding:7px;border-bottom:1px solid #eee;text-align:right;">%.2f</td>
                            <td style="padding:7px;border-bottom:1px solid #eee;">%s</td>
                        </tr>
                    """ % (product_name, prescribed, remaining, instructions))
                html = """
                    <div style="padding:10px;border:1px solid #ddd;border-radius:6px;background:#fafafa;">
                        <p style="margin:0 0 8px 0;"><strong>Review medication before confirming dispense.</strong></p>
                        <table style="width:100%%;border-collapse:collapse;">
                            <thead>
                                <tr style="background:#f1f1f1;">
                                    <th style="padding:7px;text-align:left;">Medication</th>
                                    <th style="padding:7px;text-align:right;">Qty Prescribed</th>
                                    <th style="padding:7px;text-align:right;">Qty To Dispense</th>
                                    <th style="padding:7px;text-align:left;">Instructions</th>
                                </tr>
                            </thead>
                            <tbody>%s</tbody>
                        </table>
                    </div>
                """ % ''.join(rows)
            wizard.medication_summary = html

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        prescription_id = self.env.context.get('active_id') or self.env.context.get('default_prescription_id')
        if prescription_id:
            prescription = self.env['pharmacy.prescription'].browse(prescription_id).exists()
            if prescription:
                res['prescription_id'] = prescription.id
                res['pharmacist_initials'] = getattr(prescription, 'pharmacist_initials', '') or ''
        return res

    def _get_prescribed_qty(self, line):
        return (
            getattr(line, 'qty_prescribed', 0.0)
            or getattr(line, 'quantity', 0.0)
            or getattr(line, 'product_uom_qty', 0.0)
            or 0.0
        )

    def _get_dispensed_qty(self, line):
        return getattr(line, 'qty_dispensed', 0.0) or 0.0

    def _get_remaining_qty(self, line):
        if 'qty_remaining' in line._fields:
            remaining = getattr(line, 'qty_remaining', 0.0)
            if remaining is not False and remaining is not None:
                return remaining
        return max(self._get_prescribed_qty(line) - self._get_dispensed_qty(line), 0.0)

    def _create_dispensing_log(self, prescription, dispense_lines):
        if 'pharmacy.dispensing.log' not in self.env:
            return False

        Log = self.env['pharmacy.dispensing.log'].sudo()
        vals = {'prescription_id': prescription.id}

        if 'patient_id' in Log._fields and getattr(prescription, 'patient_id', False):
            vals['patient_id'] = prescription.patient_id.id
        if 'pharmacist_initials' in Log._fields:
            vals['pharmacist_initials'] = self.pharmacist_initials
        if 'notes' in Log._fields:
            vals['notes'] = self.notes or 'Prescription dispensed from confirmation popup.'
        if 'dispense_date' in Log._fields:
            vals['dispense_date'] = self.dispense_date
        elif 'date' in Log._fields:
            vals['date'] = self.dispense_date

        log = Log.create(vals)

        if 'pharmacy.dispensing.log.line' in self.env:
            LogLine = self.env['pharmacy.dispensing.log.line'].sudo()
            for pline, qty in dispense_lines:
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
                if 'lot_id' in LogLine._fields and getattr(pline, 'lot_id', False):
                    line_vals['lot_id'] = pline.lot_id.id
                if line_vals:
                    LogLine.create(line_vals)

        return log

    def action_confirm_dispense(self):
        self.ensure_one()
        prescription = self.prescription_id

        if not prescription:
            raise ValidationError(_("No prescription selected."))

        if not getattr(prescription, 'line_ids', False):
            raise ValidationError(_("Please add medication lines before dispensing."))

        dispensed_now = []
        for line in prescription.line_ids:
            if not getattr(line, 'product_id', False):
                continue

            remaining = self._get_remaining_qty(line)
            if remaining <= 0:
                continue

            if 'qty_dispensed' in line._fields:
                line.sudo().write({'qty_dispensed': self._get_dispensed_qty(line) + remaining})

            if 'qty_remaining' in line._fields:
                prescribed = self._get_prescribed_qty(line)
                new_dispensed = getattr(line, 'qty_dispensed', 0.0) or 0.0
                line.sudo().write({'qty_remaining': max(prescribed - new_dispensed, 0.0)})

            dispensed_now.append((line, remaining))

        if not dispensed_now:
            raise ValidationError(_("There are no remaining quantities to dispense."))

        self._create_dispensing_log(prescription, dispensed_now)

        if 'pharmacist_initials' in prescription._fields:
            prescription.sudo().write({'pharmacist_initials': self.pharmacist_initials})

        if 'state' in prescription._fields:
            still_remaining = any((self._get_remaining_qty(line) or 0.0) > 0 for line in prescription.line_ids)
            prescription.sudo().write({'state': 'partially_dispensed' if still_remaining else 'dispensed'})

        prescription.message_post(body=_("Prescription dispensed by %s. Dispensing log created.") % (self.pharmacist_initials or 'Pharmacist'))

        return {'type': 'ir.actions.act_window_close'}
