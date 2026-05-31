# V3.1.17 Safe Simple Dispense View

Fixes upgrade error:
- Field "medication_summary" does not exist in model "pharmacy.dispense.wizard"

What changed:
- Removed medication_summary from the popup XML.
- Removed dispense_date from popup XML.
- Added a safe backend fallback for Confirm Dispense that works with the existing wizard model.

Workflow remains:
Prescription > Dispense > Confirmation Popup > Confirm Dispense.

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade Pharmacy module.
6. Restart Odoo again.
7. Log out and back in.
8. Create a new test prescription and test Dispense.
