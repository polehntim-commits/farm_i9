"""Controller for the I-9 Settings single DocType.

The single most important rule here: E-Verify enrollment legally requires
retaining copies of any List B document bearing a photograph, so enabling
``enrolled_in_e_verify`` forces ``store_document_copies`` on.

Phase 1.2 adds ``get_effective_setting`` — a resolver that lets each ERPNext
Company override any of these fields via an I-9 Company Settings record, while
this Single stays the global fallback.
"""

import frappe
from frappe import _
from frappe.model.document import Document


def get_effective_setting(company, field_name):
    """
    Return the effective value for a setting field, checking Company-level
    override first, then falling back to global I-9 Settings.

    - company: the Company name, or None. If None, always falls back to global.
    - field_name: the fieldname on I-9 Settings / I-9 Company Settings.

    For text fields (email, address, name, ein), the override is considered
    "set" only if it's a non-empty string. For int/check fields, any explicit
    value counts as override — since 0 is a legitimate config choice, we can't
    distinguish "unset" from "explicit 0" on a Check without a nullable flag.
    We treat non-existence of a Company Settings doc as "no override."
    """
    if company:
        override_name = frappe.db.exists("I-9 Company Settings", {"company": company})
        if override_name:
            override = frappe.get_cached_doc("I-9 Company Settings", override_name)
            val = override.get(field_name)
            # For string fields, treat empty as "not overridden"
            if isinstance(val, str):
                if val.strip():
                    return val
            elif val is not None:
                # Check / Int / Select — any value counts
                return val

    # Fall through to global I-9 Settings
    return frappe.db.get_single_value("I-9 Settings", field_name)


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

    @staticmethod
    def resolve(company, field_name):
        return get_effective_setting(company, field_name)
