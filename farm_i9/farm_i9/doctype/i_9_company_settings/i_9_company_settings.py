"""Controller for the I-9 Company Settings DocType.

Per-Company override of the global I-9 Settings audit posture. One record per
Company (named by ``company`` so the doc ID equals the Company name). Any field
left blank/unset falls back to global I-9 Settings via
``i_9_settings.get_effective_setting``.

Mirrors the E-Verify rule from I-9 Settings: enabling ``enrolled_in_e_verify``
forces ``store_document_copies`` on, since E-Verify legally requires retaining
copies of any List B document bearing a photograph.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class I9CompanySettings(Document):
    def validate(self):
        if self.enrolled_in_e_verify and not self.store_document_copies:
            self.store_document_copies = 1
            frappe.msgprint(
                _(
                    "E-Verify enrollment requires retaining copies of List B photo "
                    "documents. Enabled automatically."
                ),
                title=_("Policy Enforced"),
                indicator="blue",
            )
