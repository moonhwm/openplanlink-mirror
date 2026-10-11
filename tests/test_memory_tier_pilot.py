"""Synthetic behavior tests; passing does not certify a cloud deployment.
ID: OPL-MEM-TIER-TEST-20261008-01; author: codex-review-20261005.
"""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.memory_tier_pilot import EventConflict, MemoryTierPilot, TierPolicy, demo

NOW = "2026-10-08T01:00:00Z"
START = "2026-10-01T00:00:00Z"


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pilot = MemoryTierPilot(self.tmp.name)

    def tearDown(self):
        self.pilot.close()
        self.tmp.cleanup()

    def ingest(self, ref="r1", text="SYNTHETIC original\n完整原件", key="i1", **kwargs):
        payload = dict(text=text, reference_id=ref, evidence_kind="synthetic", occurred_at_utc=START, **kwargs)
        return self.pilot.consume(key, "memory_ingest", "fixture", payload)["result"]["original_hash"]

    def access(self, digest, key, timestamp=NOW):
        return self.pilot.consume(key, "memory_access", "fixture", {"original_hash": digest, "occurred_at_utc": timestamp})

    def test_dedup_preserves_original_and_full_hash_references(self):
        original = "SYNTHETIC 原文\r\n不可抹除全文"
        a = self.ingest(text=original)
        b = self.ingest(ref="r2", text=original, key="i2")
        self.assertEqual(a, hashlib.sha256(original.encode("utf-8")).hexdigest())
        self.assertEqual(a, b)
        self.assertEqual(self.pilot.original(a), original.encode("utf-8"))
        self.assertEqual(self.pilot.cas.stats()["objects"], 1)
        report = self.pilot.report(NOW)
        self.assertEqual(report["objects"][0]["reference_ids"], ["r1", "r2"])
        self.assertEqual(report["baseline"]["avoided_duplicate_bytes"], len(original.encode("utf-8")))

    def test_event_replay_is_durable_and_key_order_independent(self):
        digest = self.ingest()
        self.access(digest, "access1")
        self.pilot.close()
        self.pilot = MemoryTierPilot(self.tmp.name)
        replay = self.pilot.consume("access1", "memory_access", "fixture", {"occurred_at_utc": NOW, "original_hash": digest})
        self.assertTrue(replay["duplicate"])
        self.assertEqual(self.pilot.report(NOW)["objects"][0]["accesses_in_window"], 1)
        self.assertEqual(self.pilot.report(NOW)["event_ledger_count"], 2)

    def test_payload_conflict_and_reference_replacement_fail_closed(self):
        digest = self.ingest()
        self.access(digest, "a1")
        before = self.pilot.report(NOW)
        with self.assertRaises(EventConflict):
            self.access(digest, "a1", "2026-10-07T00:00:00Z")
        with self.assertRaises(EventConflict):
            self.ingest(text="SYNTHETIC replacement", key="replacement")
        payload = {"original_hash": digest, "occurred_at_utc": NOW}
        for kind, source in (("memory_ingest", "fixture"), ("memory_access", "changed-source")):
            with self.subTest(kind=kind, source=source), self.assertRaises(EventConflict):
                self.pilot.consume("a1", kind, source, payload)
        self.assertEqual(self.pilot.report(NOW), before)

    def test_failed_cas_write_does_not_consume_event_and_can_retry(self):
        with patch.object(self.pilot.cas, "put", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                self.ingest()
        self.assertEqual(self.pilot.report(NOW)["event_ledger_count"], 0)
        digest = self.ingest()
        self.assertEqual(self.pilot.original(digest), "SYNTHETIC original\n完整原件".encode("utf-8"))

    def test_window_and_recency_drive_promotion_and_demotion(self):
        digest = self.ingest()
        self.assertEqual(self.pilot.report(NOW)["objects"][0]["tier"], "cold")
        self.access(digest, "a1")
        self.assertEqual(self.pilot.report(NOW)["objects"][0]["tier"], "warm")
        self.access(digest, "a2")
        self.access(digest, "a3")
        self.assertEqual(self.pilot.report(NOW)["objects"][0]["tier"], "hot")
        self.assertEqual(self.pilot.report("2026-10-10T01:00:00Z")["objects"][0]["tier"], "warm")
        expired = self.pilot.report("2026-10-16T01:00:00Z")["objects"][0]
        self.assertEqual((expired["tier"], expired["accesses_in_window"]), ("cold", 0))
        self.assertEqual(self.pilot.original(digest), "SYNTHETIC original\n完整原件".encode("utf-8"))

    def test_requested_latency_and_configurable_policy_are_not_observed_latency(self):
        self.pilot.policy = TierPolicy(hot_min_accesses=2, hot_max_latency_ms=5, warm_max_latency_ms=50)
        hot = self.ingest(latency_budget_ms=5)
        self.ingest(ref="r2", text="SYNTHETIC warm", key="i2", latency_budget_ms=50)
        self.ingest(ref="r3", text="SYNTHETIC cold", key="i3", latency_budget_ms=51)
        objects = self.pilot.report(NOW)["objects"]
        self.assertEqual({o["reference_ids"][0]: o["tier"] for o in objects}, {"r1": "hot", "r2": "warm", "r3": "cold"})
        self.assertTrue(all(o["observed_latency_ms"] is None for o in objects))
        self.assertEqual(self.pilot.original(hot), "SYNTHETIC original\n完整原件".encode("utf-8"))

    def test_capacity_boundaries_alert_without_eviction(self):
        digest = self.ingest(text="SYNTHETIC")  # 9 UTF-8 bytes.
        for limit, warning, expected in ((10, 0.9, "warning"), (9, 1, "warning"), (8, 0.8, "exceeded"), (20, 0.8, "within_limit")):
            with self.subTest(limit=limit):
                self.pilot.policy = TierPolicy(capacities_bytes={"cold": limit}, warning_ratio=warning)
                report = self.pilot.report(NOW)
                self.assertEqual(report["capacity"]["cold"]["state"], expected)
                self.assertEqual(report["capacity"]["hot"]["state"], "unknown")
                self.assertEqual(self.pilot.original(digest), b"SYNTHETIC")

    def test_cost_estimate_and_unknown_resources_keep_evidence_distinct(self):
        self.ingest(text="SYNTHETIC", latency_budget_ms=1)
        unknown = self.pilot.report(NOW)
        self.assertIsNone(unknown["cost"]["estimated_total"])
        report = self.pilot.report(NOW, {"hot": 10, "warm": 3, "cold": 1})
        self.assertEqual(report["cost"]["kind"], "synthetic_estimate")
        self.assertAlmostEqual(report["cost"]["estimated_total"], 9 / (1024 ** 3) * 10)
        self.assertIsNone(report["cost"]["actual_cloud_bill"])
        self.assertTrue(all(value is None for value in report["resources"].values()))
        self.assertFalse(report["os_memory_risk"]["measurement_valid"])
        self.assertIsNone(report["os_memory_risk"]["R_mem_mb"])
        json.dumps(report, allow_nan=False)

    def test_invalid_config_and_future_evidence_cannot_fabricate_report(self):
        for kwargs in ({"warning_ratio": float("nan")}, {"hot_min_accesses": True}, {"capacities_bytes": {"hot": 0}}, {"hot_recency_hours": 200}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                TierPolicy(**kwargs)
        digest = self.ingest()
        for rates in ({"hot": float("inf"), "warm": 3, "cold": 1}, {"hot": 1}):
            with self.subTest(rates=rates), self.assertRaises(ValueError):
                self.pilot.report(NOW, rates)
        self.access(digest, "future", "2026-10-09T00:00:00Z")
        with self.assertRaises(ValueError):
            self.pilot.report(NOW)

    def test_original_corruption_fails_before_demand_or_event_commit(self):
        digest = self.ingest()
        with patch.object(self.pilot.cas, "get", return_value=b"SYNTHETIC tampered"):
            with self.assertRaises(ValueError):
                self.access(digest, "corrupt")
            with self.assertRaises(ValueError):
                self.pilot.report(NOW)
        report = self.pilot.report(NOW)
        self.assertEqual(report["event_ledger_count"], 1)
        self.assertEqual(report["objects"][0]["accesses_in_window"], 0)


class DemoTests(unittest.TestCase):
    def test_published_demo_is_reproducible_and_clearly_synthetic(self):
        with tempfile.TemporaryDirectory() as root:
            report = demo(root)
            self.assertEqual(demo(root), report)
        self.assertTrue(report["demo"])
        self.assertEqual({o["tier"] for o in report["objects"]}, {"hot", "warm", "cold"})
        self.assertEqual(report["demo_events"]["conflict"]["status"], "rejected")
        self.assertTrue(report["demo_events"]["duplicate"]["duplicate"])
        fixture = pathlib.Path(__file__).resolve().parents[1] / "docs" / "memory_tier_pilot_example.json"
        self.assertEqual(json.loads(fixture.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
