"""Controller for the W-4 Form DocType.

Captures an employee's federal income-tax withholding election on the 2020+
redesigned Form W-4 (five steps). Mirrors the I-9 Form's architectural pattern:

* Company + Employee links with auto-fill from the Employee record.
* SSN stored as a bare 9-digit string with a masked display copy.
* Step 3 dependent credit auto-calculated on the server (client JS mirrors it
  for real-time UI feedback).
* A signed PDF is the legal record; a W-4 cannot be marked ``Signed`` without
  it, and retention runs 5 years from the signing date (simplified IRS rule).

Audit-log writes reuse the same site-wide **I-9 Audit Log** ledger via the
module-level ``log_creation`` / ``log_update`` / ``log_deletion`` functions
wired in hooks.py — the compliance ledger is shared across I-9 *and* W-4
activity. The audit-write helper is duplicated here (rather than refactored out
of i_9_form.py) to keep the I-9 Form controller untouched per this phase's
scope, and because the W-4 leaves ``reference_i9`` null (that Link points at
I-9 Form) and records the W-4 name in the details payload instead.
"""

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, nowdate

# Step 3 credit multipliers, per the W-4 form instructions.
CREDIT_PER_CHILD = 2000
CREDIT_PER_OTHER_DEPENDENT = 500

# Simplified retention window: signed_date + this many years.
RETENTION_YEARS = 5


class W4Form(Document):
    # ------------------------------------------------------------------ #
    # Frappe lifecycle
    # ------------------------------------------------------------------ #
    def before_insert(self):
        """Default the tax year to the current calendar year."""
        if not self.tax_year:
            self.tax_year = frappe.utils.now_datetime().year

    def validate(self):
        self.populate_employee_defaults()
        self.calculate_credit()
        self.mask_ssn()
        self.handle_signed_transition()

    # ------------------------------------------------------------------ #
    # Employee auto-fill
    # ------------------------------------------------------------------ #
    def populate_employee_defaults(self):
        """Fill name + address fields from the Employee record when empty.

        fetch_from handles the simple 1:1 copies (first/last name, company) at
        the JSON level. This mirrors I-9 Form for the two cases fetch_from
        can't cover:
          - middle_initial: employee.middle_name may be a full name; truncate
            to the first character, uppercased.
          - address_*: employee.current_address is a Link to Address; resolve
            and split into street/apt/city/state/zip.
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
                self.address_state = addr.state or ""
            if not self.address_zip:
                self.address_zip = addr.pincode or ""

    # ------------------------------------------------------------------ #
    # Step 3 credit
    # ------------------------------------------------------------------ #
    def calculate_credit(self):
        """total_credit_amount = (children × 2000) + (other dependents × 500)."""
        children = self.qualifying_children_under_17 or 0
        others = self.other_dependents or 0
        self.total_credit_amount = (children * CREDIT_PER_CHILD) + (
            others * CREDIT_PER_OTHER_DEPENDENT
        )

    # ------------------------------------------------------------------ #
    # SSN masking
    # ------------------------------------------------------------------ #
    def mask_ssn(self):
        """Store the SSN as a bare 9-digit string; keep a masked display copy."""
        if not self.ssn:
            self.ssn_masked = None
            return

        digits = re.sub(r"\D", "", self.ssn)
        if len(digits) != 9:
            frappe.throw(_("SSN must contain exactly 9 digits (with or without hyphens)."))

        self.ssn = digits
        self.ssn_masked = "***-**-" + digits[-4:]

    # ------------------------------------------------------------------ #
    # Signed-status enforcement + retention
    # ------------------------------------------------------------------ #
    def handle_signed_transition(self):
        """When a W-4 reaches Signed, enforce the legal-record + anchor rules
        and stamp the signing/retention dates.
        """
        if self.status != "Signed":
            return

        if not self.company:
            frappe.throw(_("Company is required before a W-4 can be marked Signed."))

        if not self.w4_pdf_attachment:
            frappe.throw(
                _(
                    "Attach the signed W-4 PDF (the legal record of the withholding "
                    "election) before marking this W-4 Signed."
                )
            )

        if not self.signed_date:
            self.signed_date = nowdate()

        self.retention_until = add_years(self.signed_date, RETENTION_YEARS)


# ---------------------------------------------------------------------- #
# Audit-log hooks (wired in hooks.py doc_events)
#
# These reuse the shared I-9 Audit Log ledger. reference_i9 (a Link to I-9
# Form) stays null for W-4 rows; the W-4 name travels in the details payload.
# ---------------------------------------------------------------------- #
def _write_audit(action, doc, details=None):
    """Create an immutable I-9 Audit Log entry for a W-4 event."""
    payload = {"w4_form": doc.name}
    payload.update(details or {})

    entry = frappe.new_doc("I-9 Audit Log")
    entry.timestamp = frappe.utils.now_datetime()
    entry.user = frappe.session.user
    entry.action = action
    entry.reference_i9 = None
    entry.company = getattr(doc, "company", None)
    entry.ip_address = frappe.local.request_ip if getattr(frappe, "local", None) else None
    entry.details = json.dumps(payload, default=str, indent=2)
    entry.insert(ignore_permissions=True)


def log_creation(doc, method=None):
    _write_audit(
        "W-4 record created",
        doc,
        {"status": doc.status, "employee": doc.employee, "tax_year": doc.tax_year},
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

    _write_audit("W-4 record updated", doc, {"changed_fields": changes})


def log_deletion(doc, method=None):
    _write_audit(
        "W-4 record deleted",
        doc,
        {"status": doc.status, "reason": frappe.form_dict.get("reason", "unspecified")},
    )
