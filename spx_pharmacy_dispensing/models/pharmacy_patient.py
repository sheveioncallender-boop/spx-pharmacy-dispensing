# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class PharmacyPatient(models.Model):
    _name = 'pharmacy.patient'
    _description = 'Pharmacy Patient Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Linked Contact', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(compute='_compute_age', store=True)
    gender = fields.Selection([('male','Male'),('female','Female'),('other','Other'),('unknown','Unknown')], default='unknown', tracking=True)
    phone = fields.Char(tracking=True)
    email = fields.Char(tracking=True)
    address = fields.Text()
    blood_group = fields.Selection([('a+','A+'),('a-','A-'),('b+','B+'),('b-','B-'),('ab+','AB+'),('ab-','AB-'),('o+','O+'),('o-','O-'),('unknown','Unknown')], default='unknown')
    primary_doctor_id = fields.Many2one('res.partner', string='Primary Doctor', domain=[('is_company','=',False)], tracking=True)
    allergy_ids = fields.Many2many('pharmacy.allergen', 'pharmacy_patient_allergen_rel', 'patient_id', 'allergen_id', string='Allergies', tracking=True)
    medical_notes = fields.Text(tracking=True)
    prescription_ids = fields.One2many('pharmacy.prescription','patient_id')
    dispensing_log_ids = fields.One2many('pharmacy.dispensing.log','patient_id')
    prescription_count = fields.Integer(compute='_compute_counts')
    dispensing_count = fields.Integer(compute='_compute_counts')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.age = relativedelta(today, rec.date_of_birth).years if rec.date_of_birth else 0

    def _compute_counts(self):
        for rec in self:
            rec.prescription_count = len(rec.prescription_ids)
            rec.dispensing_count = len(rec.dispensing_log_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('pharmacy.patient') or 'New'
        return super().create(vals_list)

    def action_view_prescriptions(self):
        return {'type':'ir.actions.act_window','name':'Prescriptions','res_model':'pharmacy.prescription','view_mode':'tree,form','domain':[('patient_id','=',self.id)],'context':{'default_patient_id': self.id}}

    def action_view_dispensing(self):
        return {'type':'ir.actions.act_window','name':'Dispensing History','res_model':'pharmacy.dispensing.log','view_mode':'tree,form','domain':[('patient_id','=',self.id)]}

class PharmacyAllergen(models.Model):
    _name = 'pharmacy.allergen'
    _description = 'Pharmacy Allergen / Allergy'
    _order = 'name'
    name = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [('name_unique','unique(name)','This allergy already exists.')]
