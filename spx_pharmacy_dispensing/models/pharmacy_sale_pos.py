# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    pharmacy_prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    pharmacy_prescription_line_id = fields.Many2one('pharmacy.prescription.line', string='Prescription Line')

class PosOrder(models.Model):
    _inherit = 'pos.order'
    pharmacy_prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')
    pharmacy_patient_id = fields.Many2one(related='pharmacy_prescription_id.patient_id', store=True, readonly=True)
