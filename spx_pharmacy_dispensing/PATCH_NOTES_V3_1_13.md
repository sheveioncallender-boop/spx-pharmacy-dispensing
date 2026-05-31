# V3.1.13 Force Wizard Required Field Fix

This patch is cumulative from V3.1.12.

Issue fixed:
- Confirm Dispense still showing:
  Missing required value for field 'Prescription Line' (prescription_line_id)
  on pharmacy.dispense.wizard.line.

What changed:
- Force removes required=True from prescription_line_id on the wizard line model.
- Patches any XML required flags for that field.
- Adds a post-init hook to update Odoo field metadata if the old required flag remained after upgrades.
- Keeps the defensive confirm logic that matches the prescription line from prescription + product.

Patched files:
No direct required=True pattern found; hook still added.

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing Pharmacy module.
6. Restart Odoo again.
7. Log out and back in.
8. Create a NEW test prescription and test Dispense > Confirm Dispense.
