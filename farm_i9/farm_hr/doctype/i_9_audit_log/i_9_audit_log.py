"""Controller for the I-9 Audit Log DocType.

Entries are append-only: once inserted they can never be modified or deleted.
The DocType JSON already grants NO write/delete/amend role to anyone; this
controller is the belt-and-suspenders guard against updates via ignore_permissions
or direct API calls.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class I9AuditLog(Document):
    def validate(self):
        # Allow the very first insert (document is still local / new), block
        # every subsequent write. ``is_new()`` is True only before the first
        # database insert.
        if not self.is_new() and not frappe.flags.in_install:
            frappe.throw(_("Audit log entries are immutable."))

    def on_trash(self):
        if not frappe.flags.in_install:
            frappe.throw(_("Audit log entries cannot be deleted."))
