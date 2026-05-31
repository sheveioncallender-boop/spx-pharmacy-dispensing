# -*- coding: utf-8 -*-
from odoo import models, _


class PharmacyPrescriptionDispensePopupAction(models.Model):
    _inherit = 'pharmacy.prescription'

    def action_dispense(self):
        self.ensure_one()
        return {
            'name': _('Dispense Prescription'),
            'type': 'ir.actions.act_window',
            'res_model': 'pharmacy.dispense.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_prescription_id': self.id,
                'active_id': self.id,
                'active_model': 'pharmacy.prescription',
            },
        }

    def action_open_dispense_wizard(self):
        return self.action_dispense()

    def button_dispense(self):
        return self.action_dispense()
