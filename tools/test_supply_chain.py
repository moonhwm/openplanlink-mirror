#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_supply_chain.py —— 供应链三查单测（stdlib unittest）。"""
import os
import json
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import supply_chain as SC


class SupplyChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="opl-supply-chain-")
        self.addCleanup(self.tmp.cleanup)
        self.notice_path = os.path.join(self.tmp.name, "NOTICE.txt")
        self.secret_path = os.path.join(self.tmp.name, "sample.txt")
        with open(self.notice_path, "w", encoding="utf-8") as f:
            f.write("NOTICE: demo")

    def test_empty_files_no_notice_rejected(self):
        r = SC.notice_check([])
        self.assertFalse(r["ok"])

    def test_notice_file_accepted(self):
        with open(self.notice_path, "w", encoding="utf-8") as f:
            f.write("NOTICE: demo")
        r = SC.notice_check([self.notice_path])
        self.assertTrue(r["ok"])

    def test_secret_scan_no_leak(self):
        with open(self.secret_path, "w", encoding="utf-8") as f:
            f.write("k=" + "s" + "k-" + "abcdefghij" * 3)
        r = SC.secret_scan([self.secret_path])
        self.assertFalse(r["ok"])
        self.assertTrue(all("sk-abcdefghij" not in json.dumps(r, ensure_ascii=False) for _ in [0]))

    def test_sbom_missing_field(self):
        r = SC.sbom_register({"name": "x"})
        self.assertFalse(r["ok"])

    def test_gate_reject_without_notice(self):
        r = SC.gate({"components": [{"name": "x", "version": "1", "license_layer": "AGPL-3.0",
                                     "source": "s", "files": []}]})
        self.assertFalse(r["ok"])
        self.assertEqual(r["report"][0]["verdict"], "不得引入")

    def test_gate_accept_with_notice(self):
        r = SC.gate({"components": [{"name": "x", "version": "1", "license_layer": "AGPL-3.0",
                                     "source": "s",
                                     "files": [self.notice_path]}]})
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    import json
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print("VERDICT=" + ("PASS" if result.wasSuccessful() else "BAD") + " tests=%d" % result.testsRun)
    sys.exit(0 if result.wasSuccessful() else 1)
