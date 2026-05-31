# V3.1.9 Product Marketing Fields Fix

This patch is cumulative and includes:
- V3.1.7 Dispense Wizard access fix
- V3.1.8 Product Brand field fix
- V3.1.9 Website/product marketing fields fix

Fixes:
- "product.template"."hot_deals" field is undefined.

Adds safe product.template fields:
- hot_deals
- featured_product
- new_arrival
- best_seller
- promo_label

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing Pharmacy module.
6. Hard refresh browser with Ctrl + F5.
7. Open the product again.
