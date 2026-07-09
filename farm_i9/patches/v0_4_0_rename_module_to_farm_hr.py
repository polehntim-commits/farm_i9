import frappe


def execute():
    """Rename Farm I9 module -> Farm HR + force workspace resync.

    Called on `bench migrate` after the new JSON has been synced into the DB.

    Rather than use `frappe.rename_doc("Module Def", ...)` — which throws
    ValidationError when the target already exists, even with merge=True in
    Frappe v15.113 — this patch takes a direct SQL approach:

    1. Ensure "Farm HR" Module Def exists (Frappe auto-creates it during
       modules.txt sync, but insert defensively if it's missing).
    2. Reassign every DocType that references "Farm I9" to "Farm HR" via
       a single UPDATE — this is what rename_doc would have done under
       the hood anyway.
    3. Delete the orphaned "Farm I9" Module Def (safe once no DocType
       references it).
    4. Delete the stale "Farm I9" Workspace so the after_migrate
       workspace_sync hook re-imports the new JSON as "Farm HR".
    """
    # Step 1: Ensure Farm HR Module Def exists. Frappe's modules.txt sync
    # normally creates it, but if we're running against a partially-migrated
    # site (or fresh install where modules.txt sync failed), insert it
    # ourselves.
    if not frappe.db.exists("Module Def", "Farm HR"):
        frappe.get_doc({
            "doctype": "Module Def",
            "module_name": "Farm HR",
            "app_name": "farm_i9",
        }).insert(ignore_permissions=True)

    # Step 2: Reassign DocTypes. Direct SQL because rename_doc validation
    # rejects the operation when both source and target Module Defs exist.
    frappe.db.sql(
        """
        UPDATE `tabDocType` SET module = 'Farm HR' WHERE module = 'Farm I9'
        """
    )

    # Step 3: Delete the orphaned Farm I9 Module Def now that no DocType
    # references it. Belt-and-suspenders count-check in case something else
    # slipped in.
    if frappe.db.exists("Module Def", "Farm I9"):
        remaining = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDocType` WHERE module = 'Farm I9'"
        )[0][0]
        if remaining == 0:
            frappe.delete_doc("Module Def", "Farm I9", force=True)

    # Step 4: Delete stale Workspace record so the after_migrate
    # workspace_sync hook re-imports the app's workspace JSON as "Farm HR".
    if frappe.db.exists("Workspace", "Farm I9"):
        frappe.delete_doc("Workspace", "Farm I9", force=True)

    frappe.db.commit()
