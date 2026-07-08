"""Controller for the I-9 Settings single DocType.

The single most important rule here: E-Verify enrollment legally requires
retaining copies of any List B document bearing a photograph, so enabling
``enrolled_in_e_verify`` forces ``store_document_copies`` on.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class I9Settings(Document):
    def validate(self):
        if self.enrolled_in_e_verify and not self.store_document_copies:
            self.store_document_copies = 1
            frappe.msgprint(
                _(
                    "E-Verify enrollment requires retaining copies of List B photo "
                    "documents. 'Store Document Copies' has been enabled automatically."
                ),
                title=_("Policy Enforced"),
                indicator="blue",
            )
