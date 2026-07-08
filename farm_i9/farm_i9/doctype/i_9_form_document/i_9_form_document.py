"""Child table row: one attached copy of an employee identity/work document.

Only used when I-9 Settings has ``store_document_copies`` enabled (the
"maximum audit defense" posture). See i_9_form.py for the uniformity rules.
"""

from frappe.model.document import Document


class I9FormDocument(Document):
    pass
