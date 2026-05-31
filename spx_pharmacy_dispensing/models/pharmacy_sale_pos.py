# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pharmacy_prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pharmacy_prescription_line_id = fields.Many2one('pharmacy.prescription.line', string='Prescription Line')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    pharmacy_prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription', copy=False)
    pharmacy_patient_id = fields.Many2one(related='pharmacy_prescription_id.patient_id', store=True, readonly=True)
    pharmacy_prescription_required = fields.Boolean(string='Prescription Required', compute='_compute_pharmacy_prescription_required', store=True)

    # Backend foundation fields. The next POS frontend patch will fill these from the POS Prescription popup.
    pharmacy_prescription_payload = fields.Text(string='POS Prescription Payload', copy=False, readonly=True)
    pharmacy_prescription_attachment = fields.Binary(string='Uploaded Prescription File', attachment=True, copy=False)
    pharmacy_prescription_attachment_name = fields.Char(string='Prescription File Name', copy=False)
    pharmacy_pharmacist_initials = fields.Char(string='Pharmacist Initials', copy=False)
    pharmacy_prescription_notes = fields.Text(string='Prescription Notes', copy=False)

    @api.depends('lines.product_id.product_tmpl_id.requires_prescription', 'lines.product_id.product_tmpl_id.pharmacy_drug_type')
    def _compute_pharmacy_prescription_required(self):
        for order in self:
            order.pharmacy_prescription_required = any(
                line.product_id.product_tmpl_id.requires_prescription
                or line.product_id.product_tmpl_id.pharmacy_drug_type in ('antibiotic', 'controlled', 'narcotic')
                for line in order.lines if line.product_id
            )

    def action_create_pharmacy_prescription(self):
        """Manual backend fallback: create a prescription from an existing POS order.

        This is intentionally backend-only for V3.1.1. It proves that POS orders,
        pharmacy prescriptions, dispensing logs and attachments can be linked safely
        before the frontend POS button is introduced in the next patch.
        """
        self.ensure_one()
        if self.pharmacy_prescription_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Prescription',
                'res_model': 'pharmacy.prescription',
                'view_mode': 'form',
                'res_id': self.pharmacy_prescription_id.id,
            }
        payload = {}
        if self.pharmacy_prescription_payload:
            try:
                payload = json.loads(self.pharmacy_prescription_payload)
            except Exception:
                payload = {}
        rx = self._pharmacy_create_prescription_from_order(payload)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prescription',
            'res_model': 'pharmacy.prescription',
            'view_mode': 'form',
            'res_id': rx.id,
        }

    def _pharmacy_create_prescription_from_order(self, payload=None):
        self.ensure_one()
        payload = payload or {}
        Patient = self.env['pharmacy.patient'].sudo()
        Prescription = self.env['pharmacy.prescription'].sudo()
        PrescriptionLine = self.env['pharmacy.prescription.line'].sudo()
        DispensingLog = self.env['pharmacy.dispensing.log'].sudo()
        Attachment = self.env['ir.attachment'].sudo()

        partner = self.partner_id
        patient = False
        patient_id = payload.get('patient_id') or payload.get('patientId')
        if patient_id:
            patient = Patient.browse(int(patient_id)).exists()
        if not patient:
            patient_name = payload.get('patient_name') or payload.get('patientName') or (partner.name if partner else _('Walk-in Patient'))
            patient_vals = {
                'name': patient_name,
                'partner_id': partner.id if partner else False,
                'phone': payload.get('phone') or (partner.phone if partner else False),
                'email': payload.get('email') or (partner.email if partner else False),
                'date_of_birth': payload.get('dob') or payload.get('date_of_birth') or payload.get('dateOfBirth') or False,
                'medical_notes': payload.get('patient_notes') or payload.get('patientNotes') or False,
            }
            patient = Patient.create(patient_vals)

        doctor = False
        doctor_name = payload.get('doctor_name') or payload.get('doctorName')
        if doctor_name:
            doctor = self.env['res.partner'].sudo().search([('name', '=', doctor_name)], limit=1)
            if not doctor:
                doctor = self.env['res.partner'].sudo().create({'name': doctor_name, 'is_company': False})

        rx = Prescription.create({
            'patient_id': patient.id,
            'doctor_id': doctor.id if doctor else False,
            'prescription_date': payload.get('prescription_date') or payload.get('prescriptionDate') or fields.Date.context_today(self),
            'diagnosis_notes': payload.get('diagnosis_notes') or payload.get('diagnosisNotes') or payload.get('notes') or self.pharmacy_prescription_notes or False,
            'pos_order_id': self.id,
        })

        for line in self.lines.filtered(lambda l: l.product_id and l.qty > 0):
            tmpl = line.product_id.product_tmpl_id
            if tmpl.is_pharmacy_drug or tmpl.requires_prescription or self.pharmacy_prescription_required:
                PrescriptionLine.create({
                    'prescription_id': rx.id,
                    'product_id': line.product_id.id,
                    'qty_prescribed': abs(line.qty) or 1.0,
                    'instructions': payload.get('instructions') or False,
                    'repeat_allowed': bool(payload.get('repeat_allowed') or payload.get('repeatAllowed')),
                    'refill_total': int(payload.get('refill_total') or payload.get('refillTotal') or 0),
                    'price_unit': line.price_unit,
                })

        if not rx.line_ids:
            # Fallback for early testing where pharmacy flags may not be configured yet.
            for line in self.lines.filtered(lambda l: l.product_id and l.qty > 0):
                PrescriptionLine.create({
                    'prescription_id': rx.id,
                    'product_id': line.product_id.id,
                    'qty_prescribed': abs(line.qty) or 1.0,
                    'instructions': payload.get('instructions') or False,
                    'price_unit': line.price_unit,
                })

        rx.action_check_safety()

        initials = payload.get('pharmacist_initials') or payload.get('pharmacistInitials') or self.pharmacy_pharmacist_initials or self.env.user.name[:3].upper()
        if rx.line_ids:
            DispensingLog.create({
                'prescription_id': rx.id,
                'pharmacist_initials': initials,
                'notes': _('Created from POS order %s') % (self.pos_reference or self.name),
                'line_ids': [(0, 0, {'prescription_line_id': rx_line.id, 'qty_dispensed': rx_line.qty_prescribed, 'is_refill': False}) for rx_line in rx.line_ids],
            })

        if self.pharmacy_prescription_attachment:
            Attachment.create({
                'name': self.pharmacy_prescription_attachment_name or _('Prescription Upload'),
                'res_model': 'pharmacy.prescription',
                'res_id': rx.id,
                'type': 'binary',
                'datas': self.pharmacy_prescription_attachment,
            })

        self.write({
            'pharmacy_prescription_id': rx.id,
            'pharmacy_pharmacist_initials': initials,
        })
        rx.message_post(body=_('Prescription linked to POS order %s.') % (self.pos_reference or self.name))
        self.message_post(body=_('Linked Pharmacy Prescription: %s') % rx.name)
        return rx
