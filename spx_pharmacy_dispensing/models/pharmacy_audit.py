# -*- coding: utf-8 -*-
from odoo import fields, models

class PharmacyAuditEntry(models.Model):
    _name = 'pharmacy.audit.entry'
    _description = 'Pharmacy Audit Entry'
    _order = 'create_date desc'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    model_name = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    action_type = fields.Selection([('override_alert','Override Alert'),('void_dispensing','Void Dispensing'),('manual_adjustment','Manual Adjustment'),('other','Other')], default='other')
    reason = fields.Text(required=True)
