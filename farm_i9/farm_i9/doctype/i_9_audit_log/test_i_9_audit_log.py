"""Stub tests for I-9 Audit Log immutability.

TODO(Phase 2): once a bench test site exists, assert that a second save on an
existing audit-log row raises, and that on_trash is blocked.
"""

import unittest


class TestI9AuditLog(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
