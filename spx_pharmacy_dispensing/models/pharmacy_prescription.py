# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PharmacyPrescription(models.Model):
    _name = 'pharmacy.prescription'
    _description = 'Pharmacy Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc, name desc'

    name = fields.Char(string='Prescription No.', default='New', copy=False, readonly=True, tracking=True)
    patient_id = fields.Many2one('pharmacy.patient', required=True, tracking=True)
    doctor_id = fields.Many2one('res.partner', string='Doctor', tracking=True)
    prescription_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    diagnosis_notes = fields.Text(string='Diagnosis / Notes', tracking=True)
    state = fields.Selection([('draft','Draft'),('checked','Checked'),('partially_dispensed','Partially Dispensed'),('dispensed','Dispensed'),('cancelled','Cancelled')], default='draft', tracking=True)
    line_ids = fields.One2many('pharmacy.prescription.line','prescription_id', copy=True)
    alert_ids = fields.One2many('pharmacy.safety.alert','prescription_id')
    dispensing_log_ids = fields.One2many('pharmacy.dispensing.log','prescription_id')
    sale_order_id = fields.Many2one('sale.order', readonly=True, copy=False)
    pos_order_id = fields.Many2one('pos.order', readonly=True, copy=False)
    prescription_file_ids = fields.Many2many('ir.attachment', compute='_compute_prescription_file_ids', string='Prescription Files')
    prescription_file_count = fields.Integer(compute='_compute_prescription_file_ids')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    amount_total = fields.Monetary(compute='_compute_amount_total')
    alert_count = fields.Integer(compute='_compute_counts')
    dispensing_count = fields.Integer(compute='_compute_counts')
    has_blocking_alert = fields.Boolean(compute='_compute_blocking_alert')

    @api.depends('line_ids.price_subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('price_subtotal'))

    def _compute_prescription_file_ids(self):
        Attachment = self.env['ir.attachment'].sudo()
        for rec in self:
            if rec.id:
                files = Attachment.search([('res_model', '=', 'pharmacy.prescription'), ('res_id', '=', rec.id)])
            else:
                files = Attachment.browse()
            rec.prescription_file_ids = files
            rec.prescription_file_count = len(files)

    def _compute_counts(self):
        for rec in self:
            rec.alert_count = len(rec.alert_ids)
            rec.dispensing_count = len(rec.dispensing_log_ids)

    def _compute_blocking_alert(self):
        for rec in self:
            rec.has_blocking_alert = any(a.state == 'open' and a.severity in ('high','critical') for a in rec.alert_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name','New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.prescription') or 'New'
        return super().create(vals_list)

    def action_check_safety(self):
        for rec in self:
            rec.alert_ids.unlink()
            rec._create_allergy_alerts(); rec._create_duplicate_alerts(); rec._create_interaction_alerts()
            rec.state = 'checked'
        return True

    def _create_allergy_alerts(self):
        Alert = self.env['pharmacy.safety.alert']
        for line in self.line_ids:
            allergens = line.product_id.product_tmpl_id.allergen_ids & self.patient_id.allergy_ids
            for allergen in allergens:
                Alert.create({'prescription_id': self.id, 'alert_type':'allergy', 'severity':'critical', 'message': _('Allergy alert: %s conflicts with patient allergy %s.') % (line.product_id.display_name, allergen.name)})

    def _create_duplicate_alerts(self):
        Alert = self.env['pharmacy.safety.alert']
        seen = {}
        for line in self.line_ids:
            cls = line.product_id.product_tmpl_id.drug_class_id
            if cls:
                if cls.id in seen:
                    Alert.create({'prescription_id': self.id, 'alert_type':'duplicate', 'severity':'high', 'message': _('Duplicate therapy: %s and %s are in the same class %s.') % (seen[cls.id].product_id.display_name, line.product_id.display_name, cls.name)})
                else:
                    seen[cls.id] = line

    def _create_interaction_alerts(self):
        Alert = self.env['pharmacy.safety.alert']
        Interaction = self.env['pharmacy.drug.interaction']
        products = self.line_ids.mapped('product_id')
        severity_map = {'low':'low','medium':'medium','high':'high','critical':'critical'}
        for i, p1 in enumerate(products):
            for p2 in products[i+1:]:
                rule = Interaction.search(['|', '&', ('product_a_id','=',p1.id), ('product_b_id','=',p2.id), '&', ('product_a_id','=',p2.id), ('product_b_id','=',p1.id), ('active','=',True)], limit=1)
                if rule:
                    Alert.create({'prescription_id': self.id, 'alert_type':'interaction', 'severity':severity_map.get(rule.severity,'medium'), 'message': _('Drug interaction: %s + %s. %s') % (p1.display_name, p2.display_name, rule.warning)})

    def action_open_dispense_wizard(self):
        self.ensure_one()
        if self.state in ('dispensed','cancelled'):
            raise UserError(_('This prescription cannot be dispensed.'))
        if not self.line_ids:
            raise UserError(_('Add at least one medication line.'))
        return {'type':'ir.actions.act_window','name':'Dispense Prescription','res_model':'pharmacy.dispense.wizard','view_mode':'form','target':'new','context':{'default_prescription_id': self.id}}

    def action_create_sale_order(self):
        self.ensure_one()
        if not self.patient_id.partner_id:
            partner = self.env['res.partner'].create({'name': self.patient_id.name, 'phone': self.patient_id.phone, 'email': self.patient_id.email})
            self.patient_id.partner_id = partner.id
        so = self.env['sale.order'].create({'partner_id': self.patient_id.partner_id.id, 'origin': self.name, 'pharmacy_prescription_id': self.id})
        for line in self.line_ids:
            qty = line.qty_remaining or line.qty_prescribed
            if qty > 0:
                self.env['sale.order.line'].create({'order_id': so.id, 'product_id': line.product_id.id, 'product_uom_qty': qty, 'price_unit': line.product_id.lst_price, 'name': line.product_id.display_name})
        self.sale_order_id = so.id
        return {'type':'ir.actions.act_window','res_model':'sale.order','view_mode':'form','res_id':so.id}

    def action_view_alerts(self):
        return {'type':'ir.actions.act_window','name':'Safety Alerts','res_model':'pharmacy.safety.alert','view_mode':'list,form','domain':[('prescription_id','=',self.id)]}

    def action_view_dispensing(self):
        return {'type':'ir.actions.act_window','name':'Dispensing Logs','res_model':'pharmacy.dispensing.log','view_mode':'list,form','domain':[('prescription_id','=',self.id)]}

    def action_view_prescription_files(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prescription Files',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'pharmacy.prescription'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'pharmacy.prescription', 'default_res_id': self.id},
        }

class PharmacyPrescriptionLine(models.Model):
    _name = 'pharmacy.prescription.line'
    _description = 'Prescription Medication Line'
    _order = 'id'

    prescription_id = fields.Many2one('pharmacy.prescription', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, domain=[('product_tmpl_id.is_pharmacy_drug','=',True)])
    strength = fields.Char(related='product_id.product_tmpl_id.strength', readonly=True)
    dosage_form = fields.Char(related='product_id.product_tmpl_id.dosage_form', readonly=True)
    qty_prescribed = fields.Float(default=1.0, required=True)
    qty_dispensed = fields.Float(compute='_compute_qty_dispensed', store=True)
    qty_remaining = fields.Float(compute='_compute_qty_dispensed', store=True)
    instructions = fields.Char()
    repeat_allowed = fields.Boolean(string='Repeat / Refill Allowed')
    refill_total = fields.Integer(default=0)
    refill_used = fields.Integer(compute='_compute_refills', store=True)
    price_unit = fields.Float(related='product_id.lst_price', readonly=False)
    price_subtotal = fields.Monetary(compute='_compute_subtotal', currency_field='currency_id')
    currency_id = fields.Many2one(related='prescription_id.currency_id')

    @api.depends('prescription_id.dispensing_log_ids.line_ids.qty_dispensed')
    def _compute_qty_dispensed(self):
        for line in self:
            disp = sum(self.env['pharmacy.dispensing.log.line'].search([('prescription_line_id','=',line.id)]).mapped('qty_dispensed'))
            line.qty_dispensed = disp
            line.qty_remaining = max(line.qty_prescribed - disp, 0)

    @api.depends('prescription_id.dispensing_log_ids.line_ids')
    def _compute_refills(self):
        for line in self:
            line.refill_used = self.env['pharmacy.dispensing.log.line'].search_count([('prescription_line_id','=',line.id),('is_refill','=',True)])

    @api.depends('qty_prescribed','price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.qty_prescribed * line.price_unit

    @api.constrains('qty_prescribed')
    def _check_qty(self):
        for rec in self:
            if rec.qty_prescribed <= 0:
                raise ValidationError(_('Quantity prescribed must be greater than zero.'))
