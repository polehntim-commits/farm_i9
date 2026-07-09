import frappe


def execute():
    """Rename Farm I9 module -> Farm HR + force workspace resync.

    Called on `bench migrate` after the new JSON has been synced into the DB.
    The Module Def rename must happen BEFORE DocType.module updates because
    Frappe validates that the target module exists.
    """
    # Step 1: Rename the Module Def. Use rename_doc so ForeignKey relationships
    # get maintained; force=True bypasses validation.
    #
    # NOTE: Frappe v15.113 `rename_doc()` does NOT accept the
    # `ignore_permissions` kwarg (typing_validations wrapper rejects it). We
    # rely on the fact that patches run under the migrate session which has
    # System Manager equivalent permissions — no explicit permission bypass
    # needed.
    #
    # Frappe auto-creates a "Farm HR" Module Def when modules.txt is synced.
    # If a previous migrate failed AFTER modules.txt sync but BEFORE this
    # patch ran, BOTH Farm I9 and Farm HR now exist. In that case we use
    # merge=True so rename_doc collapses them into a single record.
    if frappe.db.exists("Module Def", "Farm I9"):
        need_merge = bool(frappe.db.exists("Module Def", "Farm HR"))
        frappe.rename_doc(
            "Module Def",
            "Farm I9",
            "Farm HR",
            force=True,
            merge=need_merge,
        )

    # Step 2: Update tabDocType.module for any DocTypes still pointing to Farm
    # I9. Belt-and-suspenders in case rename_doc didn't cascade.
    frappe.db.sql(
        """
        UPDATE `tabDocType` SET module = 'Farm HR' WHERE module = 'Farm I9'
        """
    )

    # Step 3: Delete stale Workspace record so migrate's workspace loader
    # rebuilds from the new JSON (name/title = Farm HR). Frappe treats existing
    # Workspace records as customized and skips JSON updates, so deleting forces
    # a reload. The after_migrate workspace_sync hook then re-imports it.
    if frappe.db.exists("Workspace", "Farm I9"):
        frappe.delete_doc(
            "Workspace", "Farm I9", force=True, ignore_permissions=True
        )
    frappe.db.commit()
