
/*
 * SPXCORP Pharmacy POS Safe Button - V3.1.3
 * This version avoids Odoo POS internal JS imports so the POS screen will not
 * break with "javascript modules" errors on Odoo 19 Community.
 *
 * It provides the safe visible POS button + prescription capture UI.
 * Backend POS linkage remains available from V3.1.1 on the POS Order form.
 */
(function () {
    "use strict";

    const STORAGE_KEY_PREFIX = "spx_pharmacy_pos_prescription_";

    function getOrderLabel() {
        const candidates = Array.from(document.querySelectorAll("button, div, span"))
            .map((el) => (el.textContent || "").trim())
            .filter((txt) => /^\d{3,}$/.test(txt));
        return candidates[0] || "current";
    }

    function storageKey() {
        return STORAGE_KEY_PREFIX + getOrderLabel();
    }

    function loadPayload() {
        try {
            return JSON.parse(localStorage.getItem(storageKey()) || "{}");
        } catch (e) {
            return {};
        }
    }

    function savePayload(payload) {
        localStorage.setItem(storageKey(), JSON.stringify(payload || {}));
    }

    function readFile(file) {
        return new Promise((resolve) => {
            if (!file) {
                resolve({ fileName: "", fileData: "", mimeType: "" });
                return;
            }
            const reader = new FileReader();
            reader.onload = () => resolve({
                fileName: file.name,
                fileData: reader.result,
                mimeType: file.type || "application/octet-stream",
            });
            reader.onerror = () => resolve({ fileName: "", fileData: "", mimeType: "" });
            reader.readAsDataURL(file);
        });
    }

    function openModal() {
        const existing = loadPayload();

        const overlay = document.createElement("div");
        overlay.id = "spx-pharmacy-prescription-overlay";
        overlay.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;";
        overlay.innerHTML = `
            <div style="width:720px;max-width:94vw;max-height:92vh;overflow:auto;background:#fff;border-radius:14px;box-shadow:0 20px 50px rgba(0,0,0,.28);">
                <div style="padding:16px 20px;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;background:#0B2B45;color:white;border-radius:14px 14px 0 0;">
                    <div>
                        <h3 style="margin:0;font-size:21px;">Prescription Details</h3>
                        <div style="font-size:12px;opacity:.9;">SPXCORP Pharmacy POS</div>
                    </div>
                    <button data-close="1" style="border:0;background:transparent;color:white;font-size:26px;cursor:pointer;">×</button>
                </div>
                <div style="padding:18px 20px;text-align:left;">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                        <label>Patient Name<br><input data-field="patientName" value="${existing.patientName || ""}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;" placeholder="Walk-in Patient"></label>
                        <label>Date of Birth<br><input data-field="dob" type="date" value="${existing.dob || ""}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;"></label>
                        <label>Doctor Name<br><input data-field="doctorName" value="${existing.doctorName || ""}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;" placeholder="Doctor / Prescriber"></label>
                        <label>Prescription Date<br><input data-field="prescriptionDate" type="date" value="${existing.prescriptionDate || new Date().toISOString().slice(0,10)}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;"></label>
                        <label>Pharmacist Initials<br><input data-field="pharmacistInitials" value="${existing.pharmacistInitials || ""}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;" placeholder="e.g. JP"></label>
                        <label>Total Refills<br><input data-field="refillTotal" type="number" min="0" value="${existing.refillTotal || 0}" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;"></label>
                        <label style="grid-column:1 / span 2;display:flex;gap:8px;align-items:center;"><input data-field="repeatAllowed" type="checkbox" ${existing.repeatAllowed ? "checked" : ""}> Repeat / Refill Allowed</label>
                        <label style="grid-column:1 / span 2;">Diagnosis / Notes<br><textarea data-field="diagnosisNotes" rows="3" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;" placeholder="Diagnosis, notes, allergies or special instructions">${existing.diagnosisNotes || ""}</textarea></label>
                        <label style="grid-column:1 / span 2;">Medication Instructions<br><textarea data-field="instructions" rows="3" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;" placeholder="Example: Take one capsule three times daily">${existing.instructions || ""}</textarea></label>
                        <label style="grid-column:1 / span 2;">Upload Prescription File / Photo<br><input data-field="file" type="file" accept="image/*,.pdf" style="width:100%;padding:9px;border:1px solid #bbb;border-radius:8px;"></label>
                        <div style="grid-column:1 / span 2;font-size:13px;color:#555;">${existing.fileName ? "Saved file: " + existing.fileName : "Upload is stored with this POS session draft."}</div>
                    </div>
                    <div style="margin-top:12px;padding:10px;background:#eef7e8;border:1px solid #b8e0a8;border-radius:8px;color:#276419;font-size:13px;">
                        Safe mode: this captures prescription details without breaking POS loading. Backend linkage remains available from the POS Order after checkout.
                    </div>
                </div>
                <div style="padding:14px 20px;border-top:1px solid #e5e7eb;display:flex;justify-content:flex-end;gap:10px;">
                    <button data-close="1" style="padding:10px 16px;border:1px solid #bbb;background:#fff;border-radius:8px;cursor:pointer;">Cancel</button>
                    <button data-save="1" style="padding:10px 16px;border:0;background:#39A935;color:#fff;border-radius:8px;cursor:pointer;font-weight:bold;">Save Prescription</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        overlay.querySelectorAll("[data-close]").forEach((btn) => btn.addEventListener("click", () => overlay.remove()));
        overlay.querySelector("[data-save]").addEventListener("click", async () => {
            const q = (name) => overlay.querySelector(`[data-field="${name}"]`);
            const fileInfo = await readFile(q("file").files[0]);
            const payload = {
                patientName: q("patientName").value,
                dob: q("dob").value,
                doctorName: q("doctorName").value,
                prescriptionDate: q("prescriptionDate").value,
                pharmacistInitials: q("pharmacistInitials").value,
                repeatAllowed: q("repeatAllowed").checked,
                refillTotal: Number(q("refillTotal").value || 0),
                diagnosisNotes: q("diagnosisNotes").value,
                instructions: q("instructions").value,
                orderLabel: getOrderLabel(),
                savedAt: new Date().toISOString(),
                fileName: fileInfo.fileName || existing.fileName || "",
                fileData: fileInfo.fileData || existing.fileData || "",
                mimeType: fileInfo.mimeType || existing.mimeType || "",
            };
            savePayload(payload);
            updateButtonState();
            overlay.remove();
        });
    }

    function updateButtonState() {
        const btn = document.getElementById("spx-pharmacy-pos-button");
        if (!btn) return;
        const payload = loadPayload();
        const hasData = payload && (payload.patientName || payload.doctorName || payload.fileName);
        btn.innerHTML = hasData ? "✓ Prescription" : "Prescription";
        btn.style.background = hasData ? "#39A935" : "#0B2B45";
    }

    function injectButton() {
        if (document.getElementById("spx-pharmacy-pos-button")) {
            updateButtonState();
            return;
        }

        const anchor = document.querySelector(".control-buttons") ||
                       document.querySelector(".payment-buttons") ||
                       document.querySelector(".pos .pads") ||
                       document.querySelector(".pos-content") ||
                       document.body;

        const btn = document.createElement("button");
        btn.id = "spx-pharmacy-pos-button";
        btn.type = "button";
        btn.style.cssText = "position:fixed;left:275px;bottom:18px;z-index:9999;padding:13px 18px;border:0;border-radius:8px;background:#0B2B45;color:white;font-weight:bold;box-shadow:0 4px 12px rgba(0,0,0,.22);cursor:pointer;";
        btn.innerHTML = "Prescription";
        btn.addEventListener("click", openModal);
        anchor.appendChild(btn);
        updateButtonState();
    }

    function start() {
        setInterval(injectButton, 1500);
        setTimeout(injectButton, 800);
        console.log("SPXCORP Pharmacy safe POS prescription button loaded.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
