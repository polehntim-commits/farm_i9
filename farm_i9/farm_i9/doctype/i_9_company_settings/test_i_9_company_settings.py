"""Stub tests for I-9 Company Settings.

TODO(Phase 2): once a bench test site exists, assert that enabling
``enrolled_in_e_verify`` forces ``store_document_copies`` on, and that
``get_effective_setting`` prefers a Company override over global I-9 Settings.
"""

import unittest

from farm_i9.farm_i9.doctype.i_9_company_settings.i_9_company_settings import (
    I9CompanySettings,
)


class TestI9CompanySettings(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
