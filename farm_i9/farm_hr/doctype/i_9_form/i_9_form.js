// Client script for I-9 Form
//
// Handles field-visibility toggles that can't be expressed purely with
// static depends_on rules — notably the document-copies section, whose
// visibility depends on the I-9 Settings single value.

frappe.ui.form.on("I-9 Form", {
	refresh(frm) {
		frm.trigger("toggle_document_copies");
		frm.trigger("toggle_citizenship_fields");
		frm.trigger("toggle_document_path");
	},

	onload(frm) {
		// Cache the settings flag so the toggle is synchronous on refresh.
		frappe.db
			.get_single_value("I-9 Settings", "store_document_copies")
			.then((val) => {
				frm._store_document_copies = !!val;
				frm.trigger("toggle_document_copies");
			});
	},

	citizenship_status(frm) {
		frm.trigger("toggle_citizenship_fields");
	},

	document_path(frm) {
		frm.trigger("toggle_document_path");
	},

	toggle_document_copies(frm) {
		// Show the document-copies table only when the farm-wide policy stores
		// copies. Read from the cached single value populated in onload().
		const show = !!frm._store_document_copies;
		frm.toggle_display("sb_document_copies", show);
		frm.toggle_display("document_copies", show);
	},

	toggle_citizenship_fields(frm) {
		const status = frm.doc.citizenship_status;
		const show_alien = [
			"Lawful Permanent Resident",
			"Authorized Alien",
		].includes(status);
		const show_expiry = status === "Authorized Alien";

		frm.toggle_display("alien_registration_number", show_alien);
		frm.toggle_display("work_authorization_expiration", show_expiry);
	},

	toggle_document_path(frm) {
		const path = frm.doc.document_path;
		const show_a = path === "List A";
		const show_bc = path === "List B + List C";

		["sb_list_a"].forEach((f) => frm.toggle_display(f, show_a));
		["sb_list_b", "sb_list_c"].forEach((f) => frm.toggle_display(f, show_bc));
	},
});
