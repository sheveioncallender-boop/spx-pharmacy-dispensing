# V3.1.16 Simple Dispense Wizard View Fix

Cumulative version based on V3.1.15.

Fixes upgrade error:
- Field "dispense_date" does not exist in model "pharmacy.dispense.wizard"

What changed:
- Removed dispense_date from the simple dispense wizard view.
- Keeps the simple confirmation popup workflow:
  Prescription > Dispense > Review Popup > Confirm Dispense.

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade Pharmacy module.
6. Restart Odoo again.
7. Log out and back in.
8. Create a new test prescription and click Dispense.
