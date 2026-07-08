"""Scheduled tasks for farm_i9.

Phase 1 keeps this deliberately minimal: a daily pass that flags I-9 Forms whose
work-authorization document is approaching expiration so they can be
re-verified. Actual email reminders arrive in Phase 2.
"""

import frappe
from frappe.utils import add_days, getdate, nowdate


def check_reverification_due():
    """Flag Complete I-9 Forms whose work authorization is about to expire.

    Reads the reminder window from I-9 Settings. Any Complete form with a
    ``work_authorization_expiration`` on or before (today + window) is moved to
    the ``Reverification Needed`` status.
    """
    window = frappe.db.get_single_value(
        "I-9 Settings", "reminder_days_before_doc_expiration"
    ) or 30

    threshold = add_days(nowdate(), window)

    forms = frappe.get_all(
        "I-9 Form",
        filters={
            "status": "Complete",
            "work_authorization_expiration": ["is", "set"],
        },
        fields=["name", "work_authorization_expiration"],
    )

    for form in forms:
        exp = form.work_authorization_expiration
        if exp and getdate(exp) <= getdate(threshold):
            frappe.db.set_value(
                "I-9 Form", form.name, "status", "Reverification Needed"
            )

    frappe.db.commit()
