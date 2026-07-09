"""Keep the Farm HR workspace in sync with farm_i9's shipped JSON.

Wired as an ``after_migrate`` hook. See the module-level note in hooks.py for
the why: Frappe treats existing DB Workspace records as user-customized and
skips re-importing the app JSON, so shortcuts added to the workspace JSON in a
later release stay hidden (this is what hid the W-4 tile after Phase 2.1). We
delete-and-reimport on every migrate so the JSON is authoritative.
"""

import frappe


def refresh_farm_hr_workspace():
    """Force reload of the Farm HR workspace from farm_i9's JSON.

    Safe because the Farm HR workspace has no user customization surface — it's
    fully app-owned. If a user later wants to customize (add their own
    charts/links), they should fork this app rather than editing the workspace
    in the desk.
    """
    if not frappe.db.exists("Workspace", "Farm HR"):
        return
    try:
        # Delete the existing workspace, then re-import from the app's JSON so
        # any newly-added DocType shortcuts appear.
        frappe.delete_doc("Workspace", "Farm HR", force=True, ignore_permissions=True)

        import os

        from frappe.modules.import_file import import_file_by_path

        app_path = frappe.get_app_path(
            "farm_i9", "farm_hr", "workspace", "farm_hr", "farm_hr.json"
        )
        if os.path.exists(app_path):
            import_file_by_path(app_path, force=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Failed to refresh Farm HR workspace: {e}", "farm_i9 workspace_sync"
        )
