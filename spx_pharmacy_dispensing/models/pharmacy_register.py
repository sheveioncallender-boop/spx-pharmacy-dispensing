# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class PharmacyDrugRegister(models.Model):
    _name = 'pharmacy.drug.register'
    _description = 'Antibiotic / Controlled / Narcotic Register'
    _inherit = ['mail.thread']
    _order = 'dispense_date desc, id desc'

    register_type = fields.Selection([('antibiotic','Antibiotic'),('controlled','Controlled Drug'),('narcotic','Narcotic')], required=True, index=True)
    dispensing_log_id = fields.Many2one('pharmacy.dispensing.log', required=True, ondelete='restrict')
    prescription_id = fields.Many2one('pharmacy.prescription', required=True, ondelete='restrict')
    patient_id = fields.Many2one('pharmacy.patient', required=True)
    doctor_id = fields.Many2one('res.partner')
    product_id = fields.Many2one('product.product', required=True)
    qty_supplied = fields.Float(required=True)
    qty_remaining = fields.Float()
    lot_id = fields.Many2one('stock.lot', string='Batch / Lot')
    dispense_date = fields.Datetime(required=True)
    pharmacist_initials = fields.Char(required=True)

    def write(self, vals):
        if not self.env.user.has_group('spx_pharmacy_dispensing.group_pharmacy_manager'):
            raise UserError(_('Drug registers are controlled records. Only a Pharmacy Manager may adjust them.'))
        return super().write(vals)

    def unlink(self):
        raise UserError(_('Drug register entries cannot be deleted.'))
