"""Real boundary and failure-path tests for pure night scheduling."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import night_schedule as schedule

NOW = "2026-10-06T06:30:00+08:00"
SCOPE, OWN, NODE, INSTANCE, PEER, VERIFIER = (char * 64 for char in "abcdef")
WORKLOAD = "7" * 64


def receipt(subject, scheme="ed25519"):
    return {"subject_sha256": subject, "scope_sha256": SCOPE, "receipt_sha256": "1" * 64,
            "verifier_sha256": VERIFIER, "issued_at": "2026-10-06T05:00:00+08:00",
            "expires_at": "2026-10-06T08:00:00+08:00", "verification_status": "verified",
            "signature_scheme": scheme}


def ready_input():
    return {"task": {"scope_sha256": SCOPE, "own_subject_sha256": OWN, "node_subject_sha256": NODE,
                     "instance_subject_sha256": INSTANCE, "required_peer_subject_sha256": [PEER],
                     "workload_sha256": WORKLOAD, "units_kind": "validated_items"},
            "identity": receipt(OWN), "instance_authorization": receipt(INSTANCE),
            "node_receipt": receipt(NODE, "hmac-sha256"), "standard_methods_receipt": receipt(NODE),
            "peer_acknowledgements": [receipt(PEER)],
            "qoder": {"account_type": "regular", "selected_model": "Qwen3.8-Max", "eligibility": receipt(OWN)}}


def sample(concurrency, completed):
    return {"observed_at": "2026-10-06T05:45:00+08:00", "expires_at": "2026-10-06T08:00:00+08:00",
            "instance_sha256": INSTANCE, "execution_receipt_sha256": "2" * 64,
            "scope_sha256": SCOPE, "workload_sha256": WORKLOAD, "units_kind": "validated_items",
            "verifier_sha256": VERIFIER, "verification_status": "verified", "concurrency": concurrency,
            "completed_units": completed, "failed_units": 0, "elapsed_seconds": 100,
            "p95_latency_seconds": 2, "cpu_utilization_percent": 60, "memory_utilization_percent": 50,
            "healthy": True}


def sampled_input():
    value = ready_input()
    value["workload"] = {"pending_units": 100, "current_concurrency": 1, "requested_concurrency": 2,
                         "huawei_x_samples": [sample(1, 100), sample(2, 150)]}
    return value


def calendar(public_holiday):
    return {"source_kind": "supplier_public_holidays", "date": "2026-10-06",
            "is_public_holiday": public_holiday, "verification_status": "verified",
            "receipt_sha256": "3" * 64, "verifier_sha256": VERIFIER,
            "issued_at": "2026-10-05T00:00:00Z", "expires_at": "2026-10-07T00:00:00Z"}


class WindowTests(unittest.TestCase):
    def test_cross_midnight_and_all_half_open_boundaries(self):
        cases = [("2026-10-05T22:59:59+08:00", "outside_window"),
                 ("2026-10-05T23:00:00+08:00", "work_window"),
                 ("2026-10-05T23:59:59+08:00", "work_window"),
                 ("2026-10-06T00:00:00+08:00", "work_window"),
                 ("2026-10-06T07:29:59+08:00", "work_window"),
                 ("2026-10-06T07:30:00+08:00", "closeout"),
                 ("2026-10-06T07:59:59+08:00", "closeout"),
                 ("2026-10-06T08:00:00+08:00", "outside_window")]
        for at, phase in cases:
            with self.subTest(at=at):
                result = schedule.evaluate(at)["window"]
                self.assertEqual(result["phase"], phase)
                self.assertEqual(result["may_expand_plan"], phase == "work_window")

    def test_midnight_uses_previous_date_and_after_close_uses_next_window(self):
        early = schedule.evaluate("2026-10-06T00:00:00+08:00")["window"]
        self.assertEqual(early["window_start_bjt"], "2026-10-05T23:00:00+08:00")
        self.assertEqual(early["window_end_bjt"], "2026-10-06T08:00:00+08:00")
        later = schedule.evaluate("2026-10-06T08:00:00+08:00")["window"]
        self.assertEqual(later["window_start_bjt"], "2026-10-06T23:00:00+08:00")

    def test_offsets_and_utc_produce_identical_instant(self):
        bjt, utc, offset = (schedule.evaluate(at) for at in
                           (NOW, "2026-10-05T22:30:00Z", "2026-10-05T17:30:00-05:00"))
        self.assertEqual(bjt, utc)
        self.assertEqual(bjt, offset)

    def test_naive_timestamp_is_never_localized(self):
        for at in ("2026-10-06T06:00:00", "2026-10-06 06:00:00+08:00", "2026-10-06", "now"):
            with self.subTest(at=at), self.assertRaises(ValueError):
                schedule.evaluate(at)
        with self.assertRaises(ValueError):
            schedule.night_window(datetime(2026, 10, 6, 6))

    def test_closeout_buffer_is_explicit_and_provisional(self):
        result = schedule.evaluate("2026-10-06T07:58:59+08:00", closeout_minutes=1)["window"]
        self.assertEqual(result["phase"], "work_window")
        closing = schedule.evaluate("2026-10-06T07:59:00+08:00", closeout_minutes=1)["window"]
        self.assertEqual(closing["action"], "save_work_and_receipts_stop_expansion")
        self.assertTrue(closing["closeout_policy_provisional"])
        self.assertFalse(closing["closeout_peer_approval_verified"])
        self.assertEqual(schedule.evaluate("2026-10-06T05:00:00+08:00", closeout_minutes=180)["window"]["phase"], "closeout")
        for minutes in (0, 181, 1.5, True):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                schedule.evaluate(NOW, closeout_minutes=minutes)

    def test_invalid_timezone_offsets_are_not_silently_normalized(self):
        for offset in ("+08:60", "+00:99", "-01:60", "+24:00"):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                schedule.evaluate("2026-10-06T06:00:00" + offset)
        value = ready_input()
        value["identity"]["issued_at"] = "2026-10-06T05:00:00+00:99"
        with self.assertRaises(ValueError):
            schedule.evaluate(NOW, value)


class ProviderTests(unittest.TestCase):
    def qoder_at(self, at, account="regular"):
        # Synthetic current-rule window for historical boundary calculations.
        with patch.object(schedule, "RULE_OBSERVED_AT", "2026-10-05T06:00:00Z"), \
             patch.object(schedule, "RULE_EXPIRES_AT", "2026-10-06T06:00:00Z"):
            return schedule.evaluate(at, {"qoder": {"account_type": account}})["provider_rules"]["qoder_cn"]

    def test_qoder_regular_and_service_account_boundaries(self):
        for at, regular, service in [("2026-10-05T21:59:59+08:00", False, False),
            ("2026-10-05T22:00:00+08:00", True, False), ("2026-10-06T00:59:59+08:00", True, False),
            ("2026-10-06T01:00:00+08:00", True, True), ("2026-10-06T06:59:59+08:00", True, True),
            ("2026-10-06T07:00:00+08:00", True, False), ("2026-10-06T08:00:00+08:00", False, False)]:
            with self.subTest(at=at):
                self.assertEqual(self.qoder_at(at)["account_window_offpeak_given_type_claim"], regular)
                self.assertEqual(self.qoder_at(at, "service_account")["account_window_offpeak_given_type_claim"], service)

    def test_unknown_account_keeps_both_rules_without_eligibility(self):
        result = self.qoder_at(NOW, "unknown")
        self.assertIsNone(result["account_window_offpeak_given_type_claim"])
        self.assertFalse(result["account_eligibility_verified"])
        self.assertIsNone(result["actual_credit_multiplier"])
        self.assertEqual(result["standard_credit_multiplier"], 0.5)
        self.assertEqual(result["offpeak_credit_multiplier"], 0.2)
        self.assertEqual(result["offpeak_to_standard_ratio"], 0.4)

    def test_eligibility_claim_never_becomes_actual_discount_or_model_switch(self):
        value = ready_input()
        result = schedule.evaluate(NOW, value)["provider_rules"]["qoder_cn"]
        self.assertTrue(result["discount_candidate_given_eligibility_claim"])
        self.assertTrue(result["selected_model_unchanged"])
        self.assertFalse(result["account_eligibility_verified"])
        self.assertIsNone(result["actual_credit_multiplier"])
        value["qoder"]["selected_model"] = "other"
        self.assertFalse(schedule.evaluate(NOW, value)["provider_rules"]["qoder_cn"]["discount_candidate_given_eligibility_claim"])

    def test_date_before_qoder_new_discount_is_not_marked_eligible(self):
        result = self.qoder_at("2026-09-04T21:59:59+08:00")
        self.assertFalse(result["rule_date_after_promotion_start"])
        self.assertFalse(result["discount_candidate_given_eligibility_claim"])

    def test_deepseek_exact_utc_peak_boundaries_keep_calendar_unknown(self):
        cases = [("00:59:59", "documented_offpeak"), ("01:00:00", "unknown"),
                 ("03:59:59", "unknown"), ("04:00:00", "documented_offpeak"),
                 ("05:59:59", "documented_offpeak"), ("06:00:00", "unknown"),
                 ("09:59:59", "unknown"), ("10:00:00", "documented_offpeak")]
        for clock, expected in cases:
            with self.subTest(clock=clock):
                result = schedule.evaluate(f"2026-10-06T{clock}Z")["provider_rules"]["deepseek"]
                self.assertEqual(result["classification"], expected)
                self.assertFalse(result["calendar_verified"])
                self.assertIsNone(result["actual_cost"])

    def test_deepseek_bjt_conversion_and_weekend(self):
        self.assertEqual(schedule.evaluate("2026-10-06T09:00:00+08:00")["provider_rules"]["deepseek"]["classification"], "unknown")
        with patch.object(schedule, "RULE_OBSERVED_AT", "2026-10-10T00:00:00Z"), \
             patch.object(schedule, "RULE_EXPIRES_AT", "2026-10-11T00:00:00Z"):
            result = schedule.evaluate("2026-10-10T01:00:00Z")["provider_rules"]["deepseek"]
        self.assertEqual(result["classification"], "documented_offpeak")
        self.assertEqual(result["offpeak_to_peak_price_ratio"], 0.5)
        self.assertFalse(result["calendar_claim_used"])

    def test_deepseek_holiday_true_and_false_are_only_conditional_claims(self):
        for holiday, expected in ((True, "offpeak_given_calendar_claim"), (False, "peak_given_calendar_claim")):
            with self.subTest(holiday=holiday):
                result = schedule.evaluate("2026-10-06T01:00:00Z", {"holiday_calendar": calendar(holiday)})["provider_rules"]["deepseek"]
                self.assertEqual(result["classification"], expected)
                self.assertTrue(result["calendar_claim_used"])
                self.assertFalse(result["calendar_verified"])

    def test_wrong_stale_unverified_and_stock_calendars_do_not_establish_rate(self):
        for field, bad in (("date", "2026-10-05"), ("expires_at", "2026-10-06T01:00:00Z"),
                           ("verification_status", "unverified"), ("source_kind", "stock_exchange")):
            value = calendar(False)
            value[field] = bad
            with self.subTest(field=field):
                result = schedule.evaluate("2026-10-06T01:00:00Z", {"holiday_calendar": value})["provider_rules"]["deepseek"]
                self.assertEqual(result["classification"], "unknown")
                self.assertFalse(result["calendar_claim_used"])
        with self.assertRaises(ValueError):
            schedule.evaluate(NOW, {"holiday_calendar": {"date": "2026-02-30"}})

    def test_rule_validity_is_half_open_and_revalidation_is_required_outside(self):
        observed = schedule.evaluate(schedule.RULE_OBSERVED_AT, ready_input())["provider_rules"]
        self.assertTrue(observed["rules_current_for_requested_time"])
        for at in ("2026-10-06T06:28:29+08:00", schedule.RULE_EXPIRES_AT,
                   "2027-10-06T06:30:00+08:00", "2025-10-06T06:30:00+08:00"):
            with self.subTest(at=at):
                result = schedule.evaluate(at, ready_input())["provider_rules"]
                self.assertFalse(result["rules_current_for_requested_time"])
                self.assertEqual(result["rule_status"], "needs_revalidation")
                self.assertEqual(result["deepseek"]["classification"], "needs_revalidation")
                self.assertIsNone(result["qoder_cn"]["account_window_offpeak_given_type_claim"])
                self.assertFalse(result["qoder_cn"]["discount_candidate_given_eligibility_claim"])
                self.assertIsNone(result["qoder_cn"]["actual_credit_multiplier"])

    def test_rule_validity_metadata_has_explicit_24_hour_window(self):
        result = schedule.evaluate(NOW)["provider_rules"]
        span = schedule.parse_timestamp(result["rules_expires_at_utc"]) - schedule.parse_timestamp(result["rules_observed_at_utc"])
        self.assertEqual(span.total_seconds(), 86_400)
        self.assertTrue(result["rules_validity_policy_provisional"])


class EvidenceTests(unittest.TestCase):
    def test_missing_evidence_never_dispatches(self):
        result = schedule.evaluate(NOW)
        evidence = result["readiness"]
        self.assertFalse(evidence["prerequisites_satisfied_given_trusted_evidence"])
        self.assertFalse(evidence["dispatch_authorized"])
        self.assertFalse(evidence["dispatch_performed"])
        self.assertFalse(result["overall_a2a_and_huawei_execution_goal_completed"])

    def test_complete_external_claims_are_only_planning_candidate(self):
        result = schedule.evaluate(NOW, ready_input())
        evidence = result["readiness"]
        self.assertTrue(evidence["prerequisites_satisfied_given_trusted_evidence"])
        self.assertEqual(result["planning_status"], "candidate_requires_independent_verification")
        for field in ("dispatch_authorized", "dispatch_performed", "eligible_for_task_dispatch",
                      "cryptographic_verification_performed", "pqc_verified", "peer_consensus_verified"):
            self.assertFalse(evidence[field], field)

    def test_every_independent_prerequisite_is_required(self):
        for field in ("identity", "instance_authorization", "node_receipt", "standard_methods_receipt", "peer_acknowledgements"):
            value = ready_input()
            del value[field]
            with self.subTest(field=field):
                self.assertFalse(schedule.evaluate(NOW, value)["readiness"]["prerequisites_satisfied_given_trusted_evidence"])

    def test_receipt_validity_is_half_open_and_history_does_not_upgrade(self):
        value = ready_input()
        value["node_receipt"]["issued_at"] = NOW
        self.assertTrue(schedule.evaluate(NOW, value)["readiness"]["prerequisites_satisfied_given_trusted_evidence"])
        value["node_receipt"]["expires_at"] = NOW
        value["node_receipt"]["issued_at"] = "2026-10-06T02:50:00+08:00"
        status = schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["node_signature"]
        self.assertEqual(status, "expired")
        value["node_receipt"]["issued_at"] = "2026-10-06T06:30:01+08:00"
        value["node_receipt"]["expires_at"] = "2026-10-06T08:00:00+08:00"
        self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["node_signature"], "not_yet_valid")

    def test_false_claim_malformed_interval_and_missing_verifier_block(self):
        for field, bad, status in (("verification_status", "unverified", "unverified_claim"),
                                  ("issued_at", "2026-10-06T08:00:00+08:00", "invalid_validity_range")):
            value = ready_input()
            value["identity"][field] = bad
            with self.subTest(field=field):
                self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["identity"], status)
        value = ready_input()
        del value["identity"]["verifier_sha256"]
        self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["identity"], "missing_fields")

    def test_binding_scope_and_subject_are_not_interchangeable(self):
        value = ready_input()
        value["instance_authorization"]["subject_sha256"] = OWN
        evidence = schedule.evaluate(NOW, value)["readiness"]
        self.assertEqual(evidence["external_claim_status"]["instance_authorization"], "subject_mismatch")
        self.assertEqual(evidence["external_claim_status"]["identity"], "current_external_claim")
        value = ready_input()
        value["node_receipt"]["scope_sha256"] = "0" * 64
        self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["node_signature"], "scope_mismatch")

    def test_node_signature_unknown_blocks_and_hmac_never_counts_as_peer_signature(self):
        value = ready_input()
        value["node_receipt"]["signature_scheme"] = "unknown"
        self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["external_claim_status"]["node_signature"], "signature_scheme_missing")
        value = ready_input()
        value["peer_acknowledgements"][0]["signature_scheme"] = "hmac-sha256"
        evidence = schedule.evaluate(NOW, value)["readiness"]
        self.assertEqual(evidence["current_independent_peer_claim_count"], 0)
        self.assertFalse(evidence["prerequisites_satisfied_given_trusted_evidence"])
        self.assertFalse(evidence["pqc_verified"])

    def test_declared_ml_dsa_is_not_a_pqc_verification(self):
        value = ready_input()
        value["peer_acknowledgements"][0]["signature_scheme"] = "ml-dsa"
        result = schedule.evaluate(NOW, value)["readiness"]
        self.assertTrue(result["prerequisites_satisfied_given_trusted_evidence"])
        self.assertFalse(result["pqc_verified"])
        self.assertFalse(result["peer_consensus_verified"])

    def test_self_node_empty_or_duplicate_seats_cannot_satisfy_independence(self):
        for peer in (OWN, NODE):
            value = ready_input()
            value["task"]["required_peer_subject_sha256"] = [peer]
            value["peer_acknowledgements"] = [receipt(peer)]
            with self.subTest(peer=peer):
                self.assertFalse(schedule.evaluate(NOW, value)["readiness"]["prerequisites_satisfied_given_trusted_evidence"])
        value = ready_input()
        value["task"]["required_peer_subject_sha256"] = []
        self.assertFalse(schedule.evaluate(NOW, value)["readiness"]["prerequisites_satisfied_given_trusted_evidence"])
        value = ready_input()
        value["task"]["required_peer_subject_sha256"] = [PEER, PEER]
        with self.assertRaises(ValueError):
            schedule.evaluate(NOW, value)

    def test_duplicate_acknowledgements_are_ambiguous_and_missing_other_seat_blocks(self):
        value = ready_input()
        value["peer_acknowledgements"].append(receipt(PEER))
        self.assertEqual(schedule.evaluate(NOW, value)["readiness"]["current_independent_peer_claim_count"], 0)
        value = ready_input()
        value["task"]["required_peer_subject_sha256"].append("9" * 64)
        evidence = schedule.evaluate(NOW, value)["readiness"]
        self.assertEqual(evidence["current_independent_peer_claim_count"], 1)
        self.assertFalse(evidence["prerequisites_satisfied_given_trusted_evidence"])

    def test_maximum_peers_and_claims_are_bounded(self):
        for field in ("required", "ack"):
            value = ready_input()
            if field == "required":
                value["task"]["required_peer_subject_sha256"] = [f"{number:064x}" for number in range(33)]
            else:
                value["peer_acknowledgements"] = [receipt(PEER) for _ in range(33)]
            with self.subTest(field=field), self.assertRaises(ValueError):
                schedule.evaluate(NOW, value)


class ThroughputTests(unittest.TestCase):
    def test_missing_prerequisites_block_increase_even_with_useful_cloud_samples(self):
        for field in ("identity", "instance_authorization", "node_receipt",
                      "standard_methods_receipt", "peer_acknowledgements"):
            value = sampled_input()
            del value[field]
            with self.subTest(field=field):
                result = schedule.evaluate(NOW, value)
                self.assertEqual(result["planning_status"], "blocked_or_outside_window")
                self.assertFalse(result["readiness"]["dispatch_authorized"])
                self.assertEqual(result["concurrency"]["recommendation"], "hold_current_concurrency")
                self.assertEqual(result["concurrency"]["suggested_concurrency"], 1)
                self.assertEqual(result["concurrency"]["basis"], "missing_current_bound_prerequisite_claims")

    def test_invalid_prerequisites_block_increase_even_with_useful_cloud_samples(self):
        cases = (("identity", "expires_at", NOW),
                 ("instance_authorization", "subject_sha256", OWN),
                 ("node_receipt", "scope_sha256", OWN),
                 ("standard_methods_receipt", "verification_status", "unverified"),
                 ("peer_acknowledgements", "signature_scheme", "hmac-sha256"))
        for field, attribute, invalid in cases:
            value = sampled_input()
            claim = value[field][0] if field == "peer_acknowledgements" else value[field]
            claim[attribute] = invalid
            with self.subTest(field=field, attribute=attribute):
                result = schedule.evaluate(NOW, value)
                self.assertEqual(result["planning_status"], "blocked_or_outside_window")
                self.assertFalse(result["readiness"]["dispatch_authorized"])
                self.assertEqual(result["concurrency"]["recommendation"], "hold_current_concurrency")
                self.assertEqual(result["concurrency"]["suggested_concurrency"], 1)

    def test_cloud_claims_can_only_suggest_observed_candidate_and_never_measured_result(self):
        result = schedule.evaluate(NOW, sampled_input())
        self.assertEqual(result["concurrency"]["recommendation"], "consider_candidate_after_independent_verification")
        self.assertEqual(result["concurrency"]["suggested_concurrency"], 2)
        self.assertFalse(result["concurrency"]["sample_claims_verified_by_this_tool"])
        metrics = result["measurement"]["huawei_x"]
        self.assertEqual(metrics["measurement_status"], "unmeasured")
        self.assertEqual(metrics["verified_jobs"], 0)
        for field in ("cpu_utilization_percent", "peak_memory_bytes", "wall_time_seconds", "throughput",
                      "queue_wait_seconds", "cost", "execution_receipt"):
            self.assertIsNone(metrics[field], field)

    def test_local_samples_cannot_be_substituted_for_huawei_cloud(self):
        value = sampled_input()
        value["workload"]["local_samples"] = value["workload"].pop("huawei_x_samples")
        result = schedule.evaluate(NOW, value)
        self.assertEqual(result["concurrency"]["recommendation"], "hold_current_concurrency")
        self.assertEqual(result["measurement"]["local"]["sample_claim_count"], 2)
        self.assertEqual(result["measurement"]["huawei_x"]["sample_claim_count"], 0)
        self.assertFalse(result["measurement"]["huawei_x"]["local_benchmark_substituted"])

    def test_idle_and_closeout_do_not_expand_or_fill_memory(self):
        value = sampled_input()
        value["workload"]["pending_units"] = 0
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "idle_no_synthetic_work")
        closing = schedule.evaluate("2026-10-06T07:30:00+08:00", sampled_input())["concurrency"]
        self.assertEqual(closing["recommendation"], "pause_expansion_save_receipts")
        self.assertEqual(closing["suggested_concurrency"], 1)
        self.assertFalse(closing["synthetic_load_or_memory_fill_allowed"])

    def test_current_bound_positive_cloud_samples_and_receipts_are_required(self):
        cases = [("expires_at", NOW), ("observed_at", "2026-10-06T06:30:01+08:00"),
                 ("verification_status", "unverified"), ("instance_sha256", OWN),
                 ("elapsed_seconds", 0), ("completed_units", 0), ("healthy", False)]
        for field, bad in cases:
            value = sampled_input()
            value["workload"]["huawei_x_samples"][1][field] = bad
            with self.subTest(field=field):
                self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")
        value = sampled_input()
        del value["workload"]["huawei_x_samples"][1]["execution_receipt_sha256"]
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")

    def test_gain_latency_failure_cpu_and_memory_gates_each_block(self):
        for field, bad in (("completed_units", 104), ("p95_latency_seconds", 2.21),
                           ("failed_units", 1), ("cpu_utilization_percent", 90.01),
                           ("memory_utilization_percent", 80.01)):
            value = sampled_input()
            value["workload"]["huawei_x_samples"][1][field] = bad
            with self.subTest(field=field):
                self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")

    def test_health_thresholds_are_inclusive_and_minimum_gain_is_five_percent(self):
        value = sampled_input()
        candidate = value["workload"]["huawei_x_samples"][1]
        candidate.update(completed_units=105, p95_latency_seconds=2.2,
                         cpu_utilization_percent=90, memory_utilization_percent=80)
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "consider_candidate_after_independent_verification")

    def test_unobserved_requested_concurrency_is_never_suggested(self):
        value = sampled_input()
        value["workload"]["requested_concurrency"] = 64
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["suggested_concurrency"], 1)
        value = sampled_input()
        value["workload"]["huawei_x_samples"][0]["concurrency"] = 3
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")

    def test_finite_sample_fields_cannot_create_nonfinite_derived_throughput(self):
        value = sampled_input()
        value["workload"]["huawei_x_samples"][1]["elapsed_seconds"] = 1e-323
        result = schedule.evaluate(NOW, value)["concurrency"]
        self.assertEqual(result["recommendation"], "hold_current_concurrency")
        self.assertEqual(result["basis"], "invalid_derived_throughput")

    def test_exact_five_percent_gain_is_not_rejected_by_float_rounding(self):
        value = sampled_input()
        baseline, candidate = value["workload"]["huawei_x_samples"]
        baseline.update(completed_units=20, elapsed_seconds=25)
        candidate.update(completed_units=21, elapsed_seconds=25)
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "consider_candidate_after_independent_verification")

    def test_exact_110_percent_p95_is_not_rejected_by_float_rounding(self):
        value = sampled_input()
        baseline, candidate = value["workload"]["huawei_x_samples"]
        baseline["p95_latency_seconds"] = 1.13
        candidate["p95_latency_seconds"] = 1.243
        self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "consider_candidate_after_independent_verification")

    def test_sample_scope_workload_and_unit_must_match_current_task(self):
        for field, other in (("scope_sha256", "9" * 64), ("workload_sha256", "8" * 64),
                             ("units_kind", "processed_records")):
            value = sampled_input()
            value["workload"]["huawei_x_samples"][1][field] = other
            with self.subTest(field=field):
                self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")

    def test_cloud_samples_with_missing_workload_or_units_binding_are_not_compared(self):
        for field in ("scope_sha256", "workload_sha256", "units_kind"):
            value = sampled_input()
            del value["workload"]["huawei_x_samples"][1][field]
            with self.subTest(sample_missing=field):
                self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")
        for field in ("workload_sha256", "units_kind"):
            value = sampled_input()
            del value["task"][field]
            with self.subTest(task_missing=field):
                self.assertEqual(schedule.evaluate(NOW, value)["concurrency"]["recommendation"], "hold_current_concurrency")


class JsonAndCliTests(unittest.TestCase):
    def run_cli(self, arguments):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = schedule.main(arguments)
        return code, json.loads(buffer.getvalue()), buffer.getvalue()

    def test_duplicate_nonfinite_nonobject_and_nonutf8_json_rejected(self):
        for raw in (b'{"task":{},"task":{}}', b'{"task":{"x":1,"x":2}}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'{"x":1e999}', b'[]', b'"private"', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                schedule.strict_input(raw)

    def test_unknown_fields_private_text_paths_macs_and_boolean_numbers_rejected(self):
        cases = [{"credential": "synthetic-private-text"}, {"task": {"scope_sha256": "relative/path"}},
                 {"identity": {"subject_sha256": "00:11:22:33:44:55"}},
                 {"workload": {"pending_units": True}}, {"workload": {"current_concurrency": 65}},
                 {"workload": {"local_samples": [{"healthy": "ACTIVE_HEALTHY"}]}},
                 {"identity": {"verified": True, "queued": True}}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                schedule.evaluate(NOW, value)

    def test_size_limit_and_sample_count_limit(self):
        with self.assertRaises(ValueError):
            schedule.strict_input(b" " * (schedule.MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            schedule.evaluate(NOW, {"workload": {"local_samples": [{}, {}, {}]}})

    def test_cli_outputs_same_json_to_exclusive_new_file(self):
        with tempfile.TemporaryDirectory() as task_dir:
            output = Path(task_dir) / "result.json"
            code, result, text = self.run_cli(["--at", NOW, "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)
            self.assertNotIn(str(output), text)
            self.assertFalse(result["network_access_performed"])
            self.assertEqual(result["jobs_dispatched"], 0)

    def test_cli_refuses_existing_output_without_overwriting_or_echoing_path(self):
        with tempfile.TemporaryDirectory() as task_dir:
            output = Path(task_dir) / "private-marker.json"
            output.write_text("preserved-private-marker", encoding="utf-8")
            code, result, text = self.run_cli(["--at", NOW, "--output", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserved-private-marker")
            self.assertEqual(result["error_code"], "invalid_input_or_output")
            self.assertNotIn("private-marker", text)

    def test_cli_reads_bounded_input_and_never_echoes_reference_or_error_text(self):
        with tempfile.TemporaryDirectory() as task_dir:
            source = Path(task_dir) / "private-claims.json"
            source.write_text(json.dumps(ready_input()), encoding="utf-8")
            code, result, text = self.run_cli(["--at", NOW, "--input", str(source)])
            self.assertEqual(code, 0)
            self.assertTrue(result["readiness"]["prerequisites_satisfied_given_trusted_evidence"])
            for reference in (SCOPE, OWN, NODE, INSTANCE, PEER, VERIFIER, WORKLOAD, str(source)):
                self.assertNotIn(reference, text)
            source.write_text('{"private":"synthetic-original-material"}', encoding="utf-8")
            code, _, text = self.run_cli(["--at", NOW, "--input", str(source)])
            self.assertEqual(code, 2)
            self.assertNotIn("synthetic-original-material", text)
            source.write_bytes(b" " * (schedule.MAX_BYTES + 1))
            self.assertEqual(self.run_cli(["--at", NOW, "--input", str(source)])[0], 2)

    def test_cli_missing_bad_argument_naive_time_and_missing_file_use_fixed_error(self):
        for args in ([], ["--private-marker", "synthetic-private"],
                     ["--at", "2026-10-06T06:00:00"],
                     ["--at", NOW, "--closeout-minutes", "synthetic-private"],
                     ["--at", NOW, "--input", "synthetic-private-missing.json"]):
            with self.subTest(args=args):
                code, result, text = self.run_cli(args)
                self.assertEqual(code, 2)
                self.assertEqual(set(result), {"schema", "result", "error_type", "error_code"})
                self.assertNotIn("synthetic-private", text)

    def test_pure_evaluation_and_cli_do_not_use_network_or_subprocesses(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("process forbidden")):
            self.assertFalse(schedule.evaluate(NOW, ready_input())["network_access_performed"])
            self.assertEqual(self.run_cli(["--at", NOW])[0], 0)

    def test_input_claims_are_not_mutated(self):
        value = sampled_input()
        original = deepcopy(value)
        schedule.evaluate(NOW, value)
        self.assertEqual(value, original)


if __name__ == "__main__":
    unittest.main()
