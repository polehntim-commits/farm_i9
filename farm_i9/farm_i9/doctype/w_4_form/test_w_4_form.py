"""Stub tests for W-4 Form. Fleshed out in a later phase once a test site
with ERPNext + HR is available in CI.
"""

import unittest


class TestW4Form(unittest.TestCase):
    def test_placeholder(self):
        # TODO(Phase 2): assert SSN masking, Step 3 credit calc, signed-status
        # PDF enforcement, and retention calc once a bench test site is wired up.
        self.assertTrue(True)
