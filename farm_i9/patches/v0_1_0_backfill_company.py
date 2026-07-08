import frappe


def execute():
    # Backfill company on existing I-9 Forms from linked Employee
    for i9 in frappe.get_all(
        "I-9 Form", filters={"company": ("in", ["", None])}, fields=["name", "employee"]
    ):
        if i9.employee:
            company = frappe.db.get_value("Employee", i9.employee, "company")
            if company:
                frappe.db.set_value("I-9 Form", i9.name, "company", company)

    # Backfill company on existing I-9 Audit Log entries from linked reference_i9
    for log in frappe.get_all(
        "I-9 Audit Log",
        filters={"company": ("in", ["", None])},
        fields=["name", "reference_i9"],
    ):
        if log.reference_i9:
            company = frappe.db.get_value("I-9 Form", log.reference_i9, "company")
            if company:
                frappe.db.set_value("I-9 Audit Log", log.name, "company", company)

    frappe.db.commit()
