"""Controller for the I-9 Form DocType.

Encodes the federal I-9 workflow:

* Section 1 (employee attestation) can be completed electronically on/before
  the first day of employment.
* Section 2 (employer verification) requires in-person review of original
  documents within 3 business days of hire.
* Retention clock = MAX(hire_date + 3 years, termination_date + 1 year).
* Document-copy retention posture is driven by I-9 Settings and must be applied
  uniformly across every employee (INA 274B anti-discrimination rule).

Audit-log writes are performed by the module-level ``log_creation`` /
``log_update`` / ``log_deletion`` functions, which are wired in hooks.py.
"""

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, getdate, nowdate

from farm_i9.farm_i9.doctype.i_9_settings.i_9_settings import get_effective_setting

# Section 1 fields that must all be present before we auto-advance to
# "Section 1 Complete".
SECTION_1_REQUIRED = (
    "legal_last_name",
    "legal_first_name",
    "address_street",
    "address_city",
    "address_state",
    "address_zip",
    "date_of_birth",
    "citizenship_status",
)


class I9Form(Document):
    # ------------------------------------------------------------------ #
    # Frappe lifecycle
    # ------------------------------------------------------------------ #
    def validate(self):
        self.normalize_ssn()
        self.set_employer_representative()
        self.populate_employee_defaults()
        self.populate_company_defaults()
        self.apply_settings_defaults()
        self.enforce_company_required()
        self.enforce_document_copy_policy()

    def before_save(self):
        self.advance_workflow()
        self.calculate_retention()

    # ------------------------------------------------------------------ #
    # Field normalization
    # ------------------------------------------------------------------ #
    def normalize_ssn(self):
        """Store the SSN as a bare 9-digit string; keep a masked display copy."""
        if not self.ssn:
            self.ssn_masked = None
            return

        digits = re.sub(r"\D", "", self.ssn)
        if len(digits) != 9:
            frappe.throw(_("SSN must contain exactly 9 digits (with or without hyphens)."))

        self.ssn = digits
        self.ssn_masked = "***-**-" + digits[-4:]

    def set_employer_representative(self):
        """The employer representative defaults to the current desk user."""
        if not self.employer_representative:
            self.employer_representative = frappe.session.user

    def populate_employee_defaults(self):
        """Fill Section 1 fields from Employee record when not already set.

        fetch_from handles the simple 1:1 field copies at the JSON level.
        This method handles the two cases fetch_from can't:
          - middle_initial: employee.middle_name might be a full name; truncate to 1 char
          - address_*: employee.current_address is a Link to Address; resolve and split
        """
        if not self.employee:
            return

        emp = frappe.db.get_value(
            "Employee",
            self.employee,
            ["middle_name", "current_address"],
            as_dict=True,
        )
        if not emp:
            return

        if not self.legal_middle_initial and emp.middle_name:
            # Take the first character of the first token — handles "M." or
            # "Marie" and leaves single-char inputs alone.
            first_token = emp.middle_name.strip().split()[0] if emp.middle_name.strip() else ""
            if first_token:
                self.legal_middle_initial = first_token[0].upper()

        if emp.current_address:
            addr = frappe.get_doc("Address", emp.current_address)
            if not self.address_street:
                self.address_street = addr.address_line1 or ""
            if not self.address_apt:
                self.address_apt = addr.address_line2 or ""
            if not self.address_city:
                self.address_city = addr.city or ""
            if not self.address_state:
                # US state field on Frappe Address is a plain string like "OR" or "Oregon"
                # — leave whatever's there. Users can normalize to 2-char if needed.
                self.address_state = addr.state or ""
            if not self.address_zip:
                self.address_zip = addr.pincode or ""

    def populate_company_defaults(self):
        """Populate employer business identity from the linked ERPNext Company.

        The Company anchor takes precedence over the global I-9 Settings
        defaults (which run afterward and only fill fields still empty). The
        business address lives on a nested Address DocType, so it can't be a
        simple ``fetch_from`` in the JSON — we resolve it here on validate.
        """
        if not self.company:
            return

        if not self.employer_business_name:
            self.employer_business_name = frappe.db.get_value(
                "Company", self.company, "company_name"
            )

        if not self.employer_business_address:
            from frappe.contacts.doctype.address.address import get_default_address

            address_name = get_default_address("Company", self.company)
            if address_name:
                addr = frappe.get_doc("Address", address_name)
                self.employer_business_address = "\n".join(
                    filter(
                        None,
                        [
                            addr.address_line1,
                            addr.address_line2,
                            f"{addr.city or ''}, {addr.state or ''} {addr.pincode or ''}".strip(
                                ", "
                            ),
                            addr.country,
                        ],
                    )
                )

    def enforce_company_required(self):
        """Company is the legal anchor for a completed I-9."""
        if self.status == "Complete" and not self.company:
            frappe.throw(_("Company is required before completing the I-9."))

    def apply_settings_defaults(self):
        """Pull employer business identity defaults from I-9 Settings.

        Routed through ``get_effective_setting`` so a Company's I-9 Company
        Settings override wins over the global Single when present.
        """
        if not self.employer_business_name:
            self.employer_business_name = get_effective_setting(
                self.company, "business_legal_name"
            )
        if not self.employer_business_address:
            self.employer_business_address = get_effective_setting(
                self.company, "business_address"
            )

    # ------------------------------------------------------------------ #
    # Workflow transitions
    # ------------------------------------------------------------------ #
    def _section_1_complete(self):
        return all(self.get(f) for f in SECTION_1_REQUIRED)

    def _section_2_documents_present(self):
        if self.document_path == "List A":
            return bool(self.list_a_document_title)
        if self.document_path == "List B + List C":
            return bool(self.list_b_document_title and self.list_c_document_title)
        return False

    def advance_workflow(self):
        """Move the record forward through the status ladder and stamp the
        signature dates as each section is completed.

        Draft -> Section 1 Complete -> Awaiting Verification -> Complete.
        We never auto-downgrade a status the user set manually (e.g.
        Reverification Needed).
        """
        # Section 1 signature stamp
        if self._section_1_complete() and not self.section_1_signed_date:
            self.section_1_signed_date = nowdate()

        # Draft -> Section 1 Complete
        if self.status == "Draft" and self._section_1_complete():
            self.status = "Section 1 Complete"

        # Section 1 Complete -> Awaiting Verification (documents chosen, not signed)
        if (
            self.status == "Section 1 Complete"
            and self.document_path
            and not self._section_2_documents_present()
        ):
            self.status = "Awaiting Verification"

        # Employer verification complete -> Complete
        if self._section_2_documents_present() and self.employer_representative:
            if not self.employer_signed_date:
                self.employer_signed_date = nowdate()
            if self.first_day_of_employment and not self.hire_date:
                self.hire_date = self.first_day_of_employment
            if self.status in ("Section 1 Complete", "Awaiting Verification"):
                self.status = "Complete"

        # Keep hire_date mirroring first day of employment
        if self.first_day_of_employment:
            self.hire_date = self.first_day_of_employment

    # ------------------------------------------------------------------ #
    # Retention
    # ------------------------------------------------------------------ #
    def calculate_retention(self):
        """retention_until = MAX(hire_date + 3yr, termination_date + 1yr)."""
        candidates = []
        if self.hire_date:
            candidates.append(getdate(add_years(self.hire_date, 3)))
        if self.termination_date:
            candidates.append(getdate(add_years(self.termination_date, 1)))

        if candidates:
            self.retention_until = max(candidates)

    # ------------------------------------------------------------------ #
    # Document-copy posture (I-9 Settings driven, uniformity enforced)
    # ------------------------------------------------------------------ #
    def enforce_document_copy_policy(self):
        store_copies = get_effective_setting(self.company, "store_document_copies")

        if store_copies and self.status == "Complete" and not self.document_copies:
            frappe.throw(
                _(
                    "I-9 Settings requires storing document copies, but no copies "
                    "were attached. Add at least one document copy before completing."
                )
            )

        # Uniformity guard: copies attached while the farm-wide policy says NOT
        # to store copies is a discrimination-law (INA 274B) misconfiguration.
        if not store_copies and self.document_copies:
            frappe.msgprint(
                _(
                    "Warning: this record has document copies attached, but I-9 "
                    "Settings has 'Store Document Copies' disabled. Federal law "
                    "(INA 274B) requires a uniform policy across all employees. "
                    "Either enable copy storage for everyone or remove these copies."
                ),
                title=_("Uniformity Warning"),
                indicator="orange",
            )


# ---------------------------------------------------------------------- #
# Audit-log hooks (wired in hooks.py doc_events)
# ---------------------------------------------------------------------- #
def _write_audit(action, doc, details=None):
    """Create an immutable I-9 Audit Log entry."""
    entry = frappe.new_doc("I-9 Audit Log")
    entry.timestamp = frappe.utils.now_datetime()
    entry.user = frappe.session.user
    entry.action = action
    entry.reference_i9 = doc.name
    entry.company = getattr(doc, "company", None)
    entry.ip_address = frappe.local.request_ip if getattr(frappe, "local", None) else None
    entry.details = json.dumps(details or {}, default=str, indent=2)
    entry.insert(ignore_permissions=True)


def log_creation(doc, method=None):
    _write_audit(
        "I-9 record created",
        doc,
        {"status": doc.status, "employee": doc.employee},
    )


def log_update(doc, method=None):
    """Record a diff of changed fields, redacting the raw SSN value."""
    before = doc.get_doc_before_save()
    if not before:
        return

    redact = {"ssn"}
    changes = {}
    for df in doc.meta.fields:
        fn = df.fieldname
        if df.fieldtype in ("Section Break", "Column Break", "Table", "HTML"):
            continue
        old = before.get(fn)
        new = doc.get(fn)
        if old != new:
            if fn in redact:
                changes[fn] = {"old": "***", "new": "***"}
            else:
                changes[fn] = {"old": old, "new": new}

    if not changes:
        return

    _write_audit("I-9 record updated", doc, {"changed_fields": changes})


def log_deletion(doc, method=None):
    _write_audit(
        "I-9 record deleted",
        doc,
        {"status": doc.status, "reason": frappe.form_dict.get("reason", "unspecified")},
    )
