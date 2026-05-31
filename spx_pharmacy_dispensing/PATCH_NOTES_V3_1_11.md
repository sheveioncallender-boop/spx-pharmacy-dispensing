# V3.1.11 Dispense Line Link Fix

Cumulative version based on V3.1.10.

Fixes:
- Validation Error when confirming dispensing:
  Missing required value for field 'Prescription Line' (prescription_line_id)
  on pharmacy.dispense.wizard.line.

Cause:
- The dispense wizard lines were being created without linking each wizard line to the original prescription line.

Fix:
- Every wizard line now includes prescription_line_id.
- Confirm Dispense updates prescription line quantities and creates dispensing log records when available.
