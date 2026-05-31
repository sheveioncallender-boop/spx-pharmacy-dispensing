# -*- coding: utf-8 -*-

def post_init_hook(env):
    # Force Odoo field metadata for the transient wizard line to be non-required.
    # This protects against older module metadata after repeated upgrades.
    field = env['ir.model.fields'].sudo().search([
        ('model', '=', 'pharmacy.dispense.wizard.line'),
        ('name', '=', 'prescription_line_id'),
    ], limit=1)
    if field and field.required:
        field.write({'required': False})
