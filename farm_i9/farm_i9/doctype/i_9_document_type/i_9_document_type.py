"""Controller for the I-9 Document Type lookup DocType.

Pre-seeded from fixtures/i_9_document_type.json with the current USCIS
List A / List B / List C acceptable documents.
"""

from frappe.model.document import Document


class I9DocumentType(Document):
    pass
