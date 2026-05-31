# V3.1.7 Dispense Wizard Access Fix

Based on the working V3.1.5/V3.1.6 branch.

Fix:
- Adds general internal-user access to the Dispense Prescription Wizard.
- This prevents the wizard from failing when the logged-in user is not assigned to Pharmacy User / Pharmacy Manager / Pharmacist groups.
- The actual prescription record access remains controlled by the module security rules.

Install:
1. Replace the GitHub module folder with this version.
2. Pull/sync repo in CloudPepper.
3. Restart Odoo.
4. Update Apps List.
5. Upgrade the existing module.
6. Log out and back in.
7. Test Dispense again.
