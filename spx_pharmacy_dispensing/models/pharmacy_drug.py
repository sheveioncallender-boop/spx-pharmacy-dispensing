# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PharmacyDrugClass(models.Model):
    _name = 'pharmacy.drug.class'
    _description = 'Drug Class / Therapy Group'
    _order = 'name'
    name = fields.Char(required=True)
    description = fields.Text()

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_pharmacy_drug = fields.Boolean(string='Pharmacy Medicine')
    pharmacy_drug_type = fields.Selection([
        ('general','General'), ('antibiotic','Antibiotic'), ('controlled','Controlled Drug'), ('narcotic','Narcotic')
    ], default='general', string='Register Type')
    drug_class_id = fields.Many2one('pharmacy.drug.class', string='Drug/Therapy Class')
    strength = fields.Char(help='Example: 500mg')
    dosage_form = fields.Char(help='Example: Tablet, Capsule, Syrup')
    route = fields.Char(help='Example: Oral, Topical')
    requires_prescription = fields.Boolean(default=False)
    controlled_schedule = fields.Char(string='Controlled Schedule')
    allergen_ids = fields.Many2many('pharmacy.allergen', 'pharmacy_product_allergen_rel', 'product_tmpl_id', 'allergen_id', string='Allergy Warnings')

class PharmacyDrugInteraction(models.Model):
    _name = 'pharmacy.drug.interaction'
    _description = 'Drug Interaction Rule'
    _inherit = ['mail.thread']
    _order = 'severity desc, product_a_id, product_b_id'

    active = fields.Boolean(default=True)
    product_a_id = fields.Many2one('product.product', required=True, domain=[('product_tmpl_id.is_pharmacy_drug','=',True)])
    product_b_id = fields.Many2one('product.product', required=True, domain=[('product_tmpl_id.is_pharmacy_drug','=',True)])
    severity = fields.Selection([('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='medium', required=True, tracking=True)
    warning = fields.Text(required=True, tracking=True)
    recommendation = fields.Text()

    _sql_constraints = [('unique_pair','unique(product_a_id, product_b_id)','This interaction rule already exists for this pair.')]


class PharmacyProductBrand(models.Model):
    _name = 'pharmacy.product.brand'
    _description = 'Pharmacy Product Brand'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class PharmacyProductTemplateBrand(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one(
        'pharmacy.product.brand',
        string='Brand',
        help='Product brand used for pharmacy product classification.'
    )
