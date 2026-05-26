# -*- coding: utf-8 -*-
from odoo import fields, models

class PharmacySafetyAlert(models.Model):
    _name = 'pharmacy.safety.alert'
    _description = 'Pharmacy Safety Alert'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    prescription_id = fields.Many2one('pharmacy.prescription', ondelete='cascade', index=True)
    patient_id = fields.Many2one(related='prescription_id.patient_id', store=True)
    alert_type = fields.Selection([('allergy','Allergy'),('duplicate','Duplicate Therapy'),('interaction','Drug Interaction'),('refill','Refill'),('expiry','Expiry')], required=True)
    severity = fields.Selection([('info','Info'),('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='medium')
    message = fields.Text(required=True)
    state = fields.Selection([('open','Open'),('acknowledged','Acknowledged'),('overridden','Overridden'),('resolved','Resolved')], default='open', tracking=True)
    override_reason = fields.Text(tracking=True)
    override_user_id = fields.Many2one('res.users', readonly=True)
    override_date = fields.Datetime(readonly=True)
