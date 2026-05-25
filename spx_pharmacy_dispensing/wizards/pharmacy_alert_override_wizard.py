# -*- coding: utf-8 -*-
from odoo import fields, models, _

class PharmacyAlertOverrideWizard(models.TransientModel):
    _name = 'pharmacy.alert.override.wizard'
    _description = 'Override Safety Alert Wizard'

    alert_id = fields.Many2one('pharmacy.safety.alert', required=True)
    reason = fields.Text(required=True)

    def action_override(self):
        self.ensure_one()
        self.alert_id.write({'state':'overridden','override_reason': self.reason, 'override_user_id': self.env.user.id, 'override_date': fields.Datetime.now()})
        self.env['pharmacy.audit.entry'].create({'name': _('Safety alert overridden'), 'model_name':'pharmacy.safety.alert', 'res_id': self.alert_id.id, 'action_type':'override_alert', 'reason': self.reason})
        return {'type':'ir.actions.act_window_close'}

class PharmacyAuditReasonWizard(models.TransientModel):
    _name = 'pharmacy.audit.reason.wizard'
    _description = 'Audit Reason Wizard'

    model_name = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    action_type = fields.Selection([('void_dispensing','Void Dispensing'),('manual_adjustment','Manual Adjustment'),('other','Other')], default='other')
    reason = fields.Text(required=True)

    def action_confirm(self):
        rec = self.env[self.model_name].browse(self.res_id)
        if self.action_type == 'void_dispensing' and self.model_name == 'pharmacy.dispensing.log':
            rec.write({'state':'void','void_reason': self.reason})
        self.env['pharmacy.audit.entry'].create({'name': self.action_type.replace('_',' ').title(), 'model_name': self.model_name, 'res_id': self.res_id, 'action_type': self.action_type, 'reason': self.reason})
        return {'type':'ir.actions.act_window_close'}
