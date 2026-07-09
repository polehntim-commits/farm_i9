// Client script for I-9 Settings
//
// Surface the E-Verify -> store-copies coupling in the UI so the user sees it
// before saving (the authoritative enforcement is server-side in validate()).

frappe.ui.form.on("I-9 Settings", {
	enrolled_in_e_verify(frm) {
		if (frm.doc.enrolled_in_e_verify && !frm.doc.store_document_copies) {
			frm.set_value("store_document_copies", 1);
			frappe.show_alert({
				message: __(
					"E-Verify enrollment requires storing document copies — enabled automatically."
				),
				indicator: "blue",
			});
		}
	},
});
