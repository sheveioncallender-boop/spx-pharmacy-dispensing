# V3.1.3 Safe POS Button Patch

This patch removes the Odoo 19 POS frontend imports that caused the red JavaScript module loading error.

What it adds:
- A safe visible Prescription button in POS.
- Prescription detail modal.
- Prescription file/photo capture in the POS browser session.
- Keeps V3.1.1 backend POS order linkage intact.

Important:
This is a safe UI compatibility patch. It avoids breaking POS while we confirm the exact Odoo 19 POS JS API available on CloudPepper.
