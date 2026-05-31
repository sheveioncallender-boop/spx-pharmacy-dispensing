# V3.1.8 Product Brand Field Fix

Fixes this error after enabling Website/eCommerce:

"product.template"."brand_id" field is undefined.

Cause:
- A product view referenced brand_id, but the field was not available on product.template.

Fix:
- Adds pharmacy.product.brand model.
- Adds brand_id field to product.template.
- Adds access rights for the brand model.

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing Pharmacy module.
6. Hard refresh the browser.
7. Open the product again.
