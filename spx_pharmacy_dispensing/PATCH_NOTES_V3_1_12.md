# V3.1.12 Defensive Dispense Confirmation Fix

Cumulative version based on V3.1.11.

Fixes:
- Same Validation Error when confirming dispensing:
  Missing required value for field 'Prescription Line' (prescription_line_id).

Why V3.1.12:
- In your Odoo 19 wizard screen the line displays, but the many2one value can still fail validation/save.
- This version removes the hard required restriction from the transient wizard line and defensively resolves the prescription line during Confirm Dispense using the current prescription + product.

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing Pharmacy module.
6. Log out and back in.
7. Test Dispense > Confirm Dispense again.
