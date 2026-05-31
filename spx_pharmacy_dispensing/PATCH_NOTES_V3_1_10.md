# V3.1.10 Dispense Wizard Line Access Fix

Cumulative version based on V3.1.9.

Includes:
- POS Actions Menu Prescription button
- Dispense Wizard access fix
- Product brand_id fix
- Website product marketing fields fix
- Dispense Wizard Line access fix

Fixes:
- Access Error when confirming/opening the dispense wizard:
  "You are not allowed to create 'Dispense Prescription Wizard Line' (pharmacy.dispense.wizard.line) records."

Install:
1. Replace GitHub module folder with this version.
2. Pull/sync in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing Pharmacy module.
6. Log out and back in.
7. Test Dispense > Confirm Dispense again.
