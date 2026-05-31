# V3.1.6 Dispense Wizard Access Fix

Based on the working V3.1.5 POS Actions Menu version.

Fix:
- Allows Pharmacy User, Pharmacy Manager and Pharmacist groups to access the Dispense Prescription Wizard.
- Resolves the backend error:
  "You are not allowed to access 'Dispense Prescription Wizard' (pharmacy.dispense.wizard) records."

Install:
1. Replace the GitHub module folder with this version.
2. Pull/sync repo in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing module.
6. Test Dispense again.
