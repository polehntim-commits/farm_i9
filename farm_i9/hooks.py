app_name = "farm_i9"
app_title = "Farm I-9"
app_publisher = "Polehn Farm"
app_description = (
    "I-9 employment eligibility verification workflow for farm ERPNext "
    "installations. Configurable audit posture per farm."
)
app_email = "polehntim@gmail.com"
app_license = "MIT"
app_version = "0.0.1"

# ---------------------------------------------------------------------------
# DocType events
#
# NOTE ON PATHS: Frappe derives a DocType's module folder from
# ``frappe.scrub(doctype_name)``, which replaces BOTH spaces and hyphens with
# underscores. So the DocType "I-9 Form" lives in the folder ``i_9_form`` (not
# ``i9_form``). The brief's hooks.py used ``i9_form``; the paths below are
# corrected to the scrub-accurate ``i_9_form`` so the module actually imports.
# ---------------------------------------------------------------------------
doc_events = {
    "I-9 Form": {
        "after_insert": "farm_i9.farm_hr.doctype.i_9_form.i_9_form.log_creation",
        "on_update": "farm_i9.farm_hr.doctype.i_9_form.i_9_form.log_update",
        "on_trash": "farm_i9.farm_hr.doctype.i_9_form.i_9_form.log_deletion",
    },
    "W-4 Form": {
        "after_insert": "farm_i9.farm_hr.doctype.w_4_form.w_4_form.log_creation",
        "on_update": "farm_i9.farm_hr.doctype.w_4_form.w_4_form.log_update",
        "on_trash": "farm_i9.farm_hr.doctype.w_4_form.w_4_form.log_deletion",
    },
    "Employee": {
        "on_update": "farm_i9.utils.employee_hooks.sync_termination_date",
    },
}

# Scheduled tasks (Phase 1 minimal — reminders come in Phase 2)
#
# NOTE ON PATHS: `tasks.py` and `utils/` sit at the Python package root
# (`farm_i9/tasks.py`, `farm_i9/utils/employee_hooks.py`), NOT inside the
# nested `farm_i9/farm_i9/` module dir which is reserved for DocType folders.
# So the dotted paths here are `farm_i9.tasks.*` and `farm_i9.utils.*`, not
# `farm_i9.farm_i9.tasks.*`. Original brief incorrectly nested them.
scheduler_events = {
    "daily": [
        "farm_i9.tasks.check_reverification_due",
    ],
}

# Fixtures for pre-seeded document types
fixtures = [
    {"dt": "I-9 Document Type"},
]

# ---------------------------------------------------------------------------
# after_migrate: keep the Farm HR workspace authoritative from JSON.
#
# Frappe preserves existing DB Workspace records as "customized" and skips
# re-importing the app's workspace JSON, so DocType shortcuts added to the JSON
# in a later release never appear (this is what hid the W-4 tile post-2.1). We
# delete-and-reimport the workspace on every migrate so the JSON always wins.
# ``utils/`` lives at the package root, so the path is ``farm_i9.utils.*``.
# ---------------------------------------------------------------------------
after_migrate = [
    "farm_i9.utils.workspace_sync.refresh_farm_hr_workspace",
]

# Client scripts / assets loaded on desk (kept minimal for Phase 1; DocType
# level .js files are picked up automatically by Frappe).
