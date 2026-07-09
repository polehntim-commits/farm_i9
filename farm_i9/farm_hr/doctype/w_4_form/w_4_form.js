// Client script for W-4 Form
//
// Mirrors the server-side Step 3 credit calc so the Total Credit Amount
// updates immediately in the UI as dependents are entered — not just on save.
// The collapsible Step 2/3/4 and Exemption sections are handled by Frappe's
// default section behavior; no client toggles needed here.

frappe.ui.form.on("W-4 Form", {
	qualifying_children_under_17: function (frm) {
		recalc_credit(frm);
	},
	other_dependents: function (frm) {
		recalc_credit(frm);
	},
});

function recalc_credit(frm) {
	const c = (frm.doc.qualifying_children_under_17 || 0) * 2000;
	const o = (frm.doc.other_dependents || 0) * 500;
	frm.set_value("total_credit_amount", c + o);
}
