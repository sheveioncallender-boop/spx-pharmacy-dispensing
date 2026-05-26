/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Component } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Order } from "@point_of_sale/app/store/models";

/**
 * SPXCORP Pharmacy POS Prescription Button - V3.1.2
 *
 * Safe frontend-only enhancement for the working V3.1.1 backend foundation.
 * This avoids the older POS popup imports that caused install/load issues.
 * The button opens a lightweight browser modal, stores prescription data on
 * the current POS order, and exports it in the POS order JSON at payment time.
 */

function readFileAsDataURL(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            resolve({ fileName: "", fileData: "", mimeType: "" });
            return;
        }
        const reader = new FileReader();
        reader.onload = () => resolve({ fileName: file.name, fileData: reader.result, mimeType: file.type });
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function pharmacyPrescriptionModal(existingPayload = {}) {
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.zIndex = "99999";
        overlay.style.background = "rgba(0,0,0,.45)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.innerHTML = `
            <div style="width: 720px; max-width: 94vw; max-height: 92vh; overflow:auto; background: #fff; border-radius: 14px; box-shadow: 0 20px 50px rgba(0,0,0,.25); font-family: Arial, sans-serif;">
                <div style="padding: 16px 20px; border-bottom: 1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; font-size:20px; color:#1F3C88;">Prescription Details</h3>
                    <button data-action="cancel" style="border:0; background:transparent; font-size:24px; cursor:pointer;">×</button>
                </div>
                <div style="padding: 18px 20px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; text-align:left;">
                        <label>Patient Name<br/><input data-field="patientName" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;" placeholder="Walk-in Patient"/></label>
                        <label>Date of Birth<br/><input data-field="dob" type="date" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;"/></label>
                        <label>Doctor Name<br/><input data-field="doctorName" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;" placeholder="Doctor / Prescriber"/></label>
                        <label>Prescription Date<br/><input data-field="prescriptionDate" type="date" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;"/></label>
                        <label>Pharmacist Initials<br/><input data-field="pharmacistInitials" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;" placeholder="e.g. SC"/></label>
                        <label>Total Refills<br/><input data-field="refillTotal" type="number" min="0" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;"/></label>
                        <label style="grid-column:1 / span 2; display:flex; gap:8px; align-items:center;"><input data-field="repeatAllowed" type="checkbox"/> Repeat / Refill Allowed</label>
                        <label style="grid-column:1 / span 2;">Diagnosis / Notes<br/><textarea data-field="diagnosisNotes" rows="3" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;" placeholder="Diagnosis, notes, allergies mentioned, or special instructions"></textarea></label>
                        <label style="grid-column:1 / span 2;">Medication Instructions<br/><textarea data-field="instructions" rows="3" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;" placeholder="Example: Take one tablet twice daily after meals"></textarea></label>
                        <label style="grid-column:1 / span 2;">Upload Prescription File / Photo<br/><input data-field="file" type="file" accept="image/*,.pdf" style="width:100%; padding:9px; border:1px solid #ccc; border-radius:8px;"/></label>
                        <div data-field="fileStatus" style="grid-column:1 / span 2; color:#666; font-size:13px;"></div>
                    </div>
                </div>
                <div style="padding: 14px 20px; border-top:1px solid #e5e7eb; display:flex; justify-content:flex-end; gap:10px;">
                    <button data-action="cancel" style="padding:10px 16px; border:1px solid #ccc; background:#fff; border-radius:8px; cursor:pointer;">Cancel</button>
                    <button data-action="save" style="padding:10px 16px; border:0; background:#1F3C88; color:#fff; border-radius:8px; cursor:pointer;">Save Prescription</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        const q = (selector) => overlay.querySelector(selector);
        const setValue = (field, value) => { const el = q(`[data-field="${field}"]`); if (el) el.value = value || ""; };
        setValue("patientName", existingPayload.patientName);
        setValue("dob", existingPayload.dob);
        setValue("doctorName", existingPayload.doctorName);
        setValue("prescriptionDate", existingPayload.prescriptionDate || new Date().toISOString().slice(0, 10));
        setValue("pharmacistInitials", existingPayload.pharmacistInitials);
        setValue("refillTotal", existingPayload.refillTotal || 0);
        setValue("diagnosisNotes", existingPayload.diagnosisNotes);
        setValue("instructions", existingPayload.instructions);
        q('[data-field="repeatAllowed"]').checked = !!existingPayload.repeatAllowed;
        if (existingPayload.fileName) q('[data-field="fileStatus"]').textContent = `Existing file saved: ${existingPayload.fileName}`;

        const close = (payload) => { overlay.remove(); resolve(payload); };
        overlay.querySelectorAll('[data-action="cancel"]').forEach((btn) => btn.addEventListener("click", () => close(null)));
        q('[data-action="save"]').addEventListener("click", async () => {
            const file = q('[data-field="file"]').files[0];
            const fileInfo = file ? await readFileAsDataURL(file) : {
                fileName: existingPayload.fileName || "",
                fileData: existingPayload.fileData || "",
                mimeType: existingPayload.mimeType || "",
            };
            close({
                patientName: q('[data-field="patientName"]').value,
                dob: q('[data-field="dob"]').value,
                doctorName: q('[data-field="doctorName"]').value,
                prescriptionDate: q('[data-field="prescriptionDate"]').value,
                pharmacistInitials: q('[data-field="pharmacistInitials"]').value,
                repeatAllowed: q('[data-field="repeatAllowed"]').checked,
                refillTotal: Number(q('[data-field="refillTotal"]').value || 0),
                diagnosisNotes: q('[data-field="diagnosisNotes"]').value,
                instructions: q('[data-field="instructions"]').value,
                ...fileInfo,
            });
        });
    });
}

class PharmacyPrescriptionButton extends Component {
    static template = "spx_pharmacy_dispensing.PharmacyPrescriptionButton";
    async onClick() {
        const order = this.env.services.pos.get_order();
        if (!order) return;
        const payload = await pharmacyPrescriptionModal(order.pharmacyPrescription || {});
        if (payload) {
            order.pharmacyPrescription = payload;
            if (order.trigger) order.trigger("change", order);
        }
    }
}

ProductScreen.addControlButton({
    component: PharmacyPrescriptionButton,
    condition: function () { return true; },
});

patch(Order.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pharmacyPrescription) {
            json.pharmacy_prescription = this.pharmacyPrescription;
        }
        return json;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.pharmacyPrescription = json.pharmacy_prescription || json.pharmacyPrescription || null;
    },
});
