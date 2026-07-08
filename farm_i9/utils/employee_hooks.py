"""Hooks that react to changes on the ERPNext ``Employee`` DocType.

Phase 1: keep I-9 Form retention dates in sync when an employee is terminated.
The I-9 retention clock is MAX(hire_date + 3yr, termination_date + 1yr), so a
newly-set relieving date must flow back into every linked I-9 Form.
"""

import frappe


def sync_termination_date(doc, method=None):
    """When an Employee's relieving/termination date changes, update linked I-9
    Forms so their ``retention_until`` recalculates.

    ``doc`` is the Employee document. ERPNext stores the termination date in the
    ``relieving_date`` field.
    """
    relieving_date = doc.get("relieving_date")
    if not relieving_date:
        return

    i9_names = frappe.get_all(
        "I-9 Form",
        filters={"employee": doc.name},
        pluck="name",
    )

    for name in i9_names:
        i9 = frappe.get_doc("I-9 Form", name)
        if i9.termination_date == relieving_date:
            continue
        i9.termination_date = relieving_date
        # save() re-runs the controller, which recomputes retention_until
        i9.save(ignore_permissions=True)
