"""Pure night-window planning; this tool never authorizes or dispatches work."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sys

BJT = timezone(timedelta(hours=8), "BJT")
UTC = timezone.utc
MAX_BYTES = 65_536
MAX_PEERS = 32
RULE_SNAPSHOT_DATE = "2026-10-06"
RULE_OBSERVED_AT = "2026-10-06T06:28:30+08:00"
RULE_EXPIRES_AT = "2026-10-07T06:28:30+08:00"
QODER_SOURCE = "https://docs.qoder.cn/product-overview/qwen-3-7-series-model-staggering-discount"
DEEPSEEK_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
TIME_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z")
SIGNATURE_SCHEMES = {"hmac-sha256", "ed25519", "ecdsa-p256", "ml-dsa", "unknown"}
UNITS_KINDS = {"completed_artifacts", "processed_records", "validated_items"}
RECEIPT_FIELDS = {"subject_sha256", "scope_sha256", "receipt_sha256", "verifier_sha256",
                  "issued_at", "expires_at", "verification_status", "signature_scheme"}
SAMPLE_FIELDS = {"observed_at", "expires_at", "instance_sha256", "scope_sha256", "workload_sha256",
                 "units_kind", "execution_receipt_sha256",
                 "verifier_sha256", "verification_status", "concurrency", "completed_units",
                 "failed_units", "elapsed_seconds", "p95_latency_seconds", "cpu_utilization_percent",
                 "memory_utilization_percent", "healthy"}


def parse_timestamp(value: str) -> datetime:
    """Require an explicit numeric offset (or Z), never host local time."""
    if not isinstance(value, str) or not TIME_TEXT.fullmatch(value):
        raise ValueError("aware_iso_timestamp_required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid_timestamp") from None
    if result.utcoffset() is None:
        raise ValueError("aware_iso_timestamp_required")
    return result.astimezone(UTC)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("nonfinite_json_number")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite_json_number")
    return number


def fields(value, allowed: set[str]) -> dict:
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    if not set(value).issubset(allowed):
        raise ValueError("unknown_input_field")
    return value


def enum(value, choices: set[str]):
    if not isinstance(value, str) or value not in choices:
        raise ValueError("invalid_enum")


def bounded_number(value, low, high, *, integer=False):
    types = (int,) if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, types) or not low <= value <= high:
        raise ValueError("invalid_number")
    if not math.isfinite(value):
        raise ValueError("nonfinite_json_number")


def validate_reference_fields(value: dict):
    for key, item in value.items():
        if key.endswith("_sha256") and (not isinstance(item, str) or not DIGEST.fullmatch(item)):
            raise ValueError("sha256_reference_required")
        if key in {"issued_at", "expires_at", "observed_at"}:
            parse_timestamp(item)
        if key == "verification_status":
            enum(item, {"verified", "unverified"})
        if key == "signature_scheme":
            enum(item, SIGNATURE_SCHEMES)


def validate_receipt(value):
    value = fields(value, RECEIPT_FIELDS)
    validate_reference_fields(value)


def validate_input(value: dict) -> dict:
    fields(value, {"task", "identity", "instance_authorization", "node_receipt",
                   "standard_methods_receipt", "peer_acknowledgements", "qoder",
                   "holiday_calendar", "workload"})
    task = fields(value.get("task", {}), {"scope_sha256", "own_subject_sha256",
                 "node_subject_sha256", "instance_subject_sha256", "required_peer_subject_sha256",
                 "workload_sha256", "units_kind"})
    validate_reference_fields({key: item for key, item in task.items() if key != "required_peer_subject_sha256"})
    if "units_kind" in task:
        enum(task["units_kind"], UNITS_KINDS)
    peers = task.get("required_peer_subject_sha256", [])
    if not isinstance(peers, list) or len(peers) > MAX_PEERS:
        raise ValueError("invalid_peer_list")
    for item in peers:
        validate_reference_fields({"peer_sha256": item})
    if len(set(peers)) != len(peers):
        raise ValueError("duplicate_required_peer")
    for name in ("identity", "instance_authorization", "node_receipt", "standard_methods_receipt"):
        if name in value:
            validate_receipt(value[name])
    acknowledgements = value.get("peer_acknowledgements", [])
    if not isinstance(acknowledgements, list) or len(acknowledgements) > MAX_PEERS:
        raise ValueError("invalid_peer_list")
    for receipt in acknowledgements:
        validate_receipt(receipt)
    qoder = fields(value.get("qoder", {}), {"account_type", "selected_model", "eligibility"})
    if "account_type" in qoder:
        enum(qoder["account_type"], {"unknown", "regular", "service_account"})
    if "selected_model" in qoder:
        enum(qoder["selected_model"], {"unspecified", "Qwen3.8-Max", "other"})
    if "eligibility" in qoder:
        validate_receipt(qoder["eligibility"])
    calendar = fields(value.get("holiday_calendar", {}), {"source_kind", "date", "is_public_holiday",
                  "issued_at", "expires_at", "verification_status", "receipt_sha256", "verifier_sha256"})
    validate_reference_fields(calendar)
    if "source_kind" in calendar:
        enum(calendar["source_kind"], {"supplier_public_holidays", "stock_exchange", "unknown"})
    if "date" in calendar:
        if not isinstance(calendar["date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", calendar["date"]):
            raise ValueError("invalid_calendar_date")
        try:
            date.fromisoformat(calendar["date"])
        except ValueError:
            raise ValueError("invalid_calendar_date") from None
    if "is_public_holiday" in calendar and type(calendar["is_public_holiday"]) is not bool:
        raise ValueError("boolean_required")
    workload = fields(value.get("workload", {}), {"pending_units", "current_concurrency",
                     "requested_concurrency", "local_samples", "huawei_x_samples"})
    for name in ("current_concurrency", "requested_concurrency"):
        if name in workload:
            bounded_number(workload[name], 1, 64, integer=True)
    if "pending_units" in workload:
        bounded_number(workload["pending_units"], 0, 1_000_000, integer=True)
    for name in ("local_samples", "huawei_x_samples"):
        samples = workload.get(name, [])
        if not isinstance(samples, list) or len(samples) > 2:
            raise ValueError("invalid_sample_list")
        for sample in samples:
            fields(sample, SAMPLE_FIELDS)
            validate_reference_fields(sample)
            if "units_kind" in sample:
                enum(sample["units_kind"], UNITS_KINDS)
            for key in ("concurrency", "completed_units", "failed_units"):
                if key in sample:
                    bounded_number(sample[key], 1 if key == "concurrency" else 0,
                                   64 if key == "concurrency" else 1_000_000_000, integer=True)
            for key in ("elapsed_seconds", "p95_latency_seconds", "cpu_utilization_percent",
                        "memory_utilization_percent"):
                if key in sample:
                    bounded_number(sample[key], 0, 100 if key.endswith("percent") else 86_400)
            if "healthy" in sample and type(sample["healthy"]) is not bool:
                raise ValueError("boolean_required")
    return value


def strict_input(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("input_too_large")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=reject_constant, parse_float=finite_float)
    return validate_input(value)


def night_window(at: datetime, closeout_minutes: int = 30) -> dict:
    if at.utcoffset() is None:
        raise ValueError("aware_iso_timestamp_required")
    bounded_number(closeout_minutes, 1, 180, integer=True)
    local = at.astimezone(BJT)
    anchor = local.date() - timedelta(days=1) if local.time() < time(8) else local.date()
    start = datetime.combine(anchor, time(23), BJT)
    end = datetime.combine(anchor + timedelta(days=1), time(8), BJT)
    closeout = end - timedelta(minutes=closeout_minutes)
    active = start <= local < end
    phase = "closeout" if active and local >= closeout else "work_window" if active else "outside_window"
    return {"timezone": "UTC+08:00", "window_start_bjt": start.isoformat(),
            "window_end_bjt": end.isoformat(), "closeout_start_bjt": closeout.isoformat(),
            "closeout_minutes": closeout_minutes, "closeout_policy_provisional": True,
            "closeout_peer_approval_verified": False, "phase": phase,
            "may_expand_plan": phase == "work_window",
            "action": "save_work_and_receipts_stop_expansion" if phase == "closeout" else
                      "evaluate_pending_work" if phase == "work_window" else "wait_for_next_window"}


def reference_status(receipt: dict, at: datetime, required=()) -> str:
    needed = {"receipt_sha256", "verifier_sha256", "issued_at", "expires_at", "verification_status", *required}
    if not needed.issubset(receipt):
        return "missing_fields"
    if receipt["verification_status"] != "verified":
        return "unverified_claim"
    issued, expires = parse_timestamp(receipt["issued_at"]), parse_timestamp(receipt["expires_at"])
    if issued >= expires:
        return "invalid_validity_range"
    if at < issued:
        return "not_yet_valid"
    if at >= expires:
        return "expired"
    return "current_external_claim"


def receipt_status(receipt: dict, at: datetime, scope, subject, *, signature=False, independent=False) -> str:
    if not scope or not subject:
        return "missing_binding"
    status = reference_status(receipt, at, ("subject_sha256", "scope_sha256"))
    if status != "current_external_claim":
        return status
    if receipt["scope_sha256"] != scope:
        return "scope_mismatch"
    if receipt["subject_sha256"] != subject:
        return "subject_mismatch"
    scheme = receipt.get("signature_scheme", "unknown")
    if signature and scheme == "unknown":
        return "signature_scheme_missing"
    if independent and scheme == "hmac-sha256":
        return "hmac_is_not_independent_signature"
    return status


def readiness(value: dict, at: datetime) -> dict:
    task = value.get("task", {})
    scope = task.get("scope_sha256")
    own, node, instance = (task.get(name) for name in
                          ("own_subject_sha256", "node_subject_sha256", "instance_subject_sha256"))
    statuses = {
        "identity": receipt_status(value.get("identity", {}), at, scope, own),
        "instance_authorization": receipt_status(value.get("instance_authorization", {}), at, scope, instance),
        "node_signature": receipt_status(value.get("node_receipt", {}), at, scope, node, signature=True),
        "standard_methods": receipt_status(value.get("standard_methods_receipt", {}), at, scope, node),
    }
    required = task.get("required_peer_subject_sha256", [])
    independent = bool(required) and not set(required).intersection({own, node})
    receipts = value.get("peer_acknowledgements", [])
    current_peers = 0
    for peer in required:
        matches = [r for r in receipts if r.get("subject_sha256") == peer]
        # Ambiguous or replayed duplicate claims do not count twice or select a convenient copy.
        if len(matches) == 1 and receipt_status(matches[0], at, scope, peer, signature=True,
                                               independent=True) == "current_external_claim":
            current_peers += 1
    statuses["independent_peers"] = ("current_external_claim" if independent and
         current_peers == len(required) else "missing_independent_peer_claims")
    return {"external_claim_status": statuses, "required_peer_count": len(required),
            "current_independent_peer_claim_count": current_peers if independent else 0,
            "prerequisites_satisfied_given_trusted_evidence": all(s == "current_external_claim" for s in statuses.values()),
            "evidence_is_external_input_claim": True, "cryptographic_verification_performed": False,
            "peer_consensus_verified": False, "pqc_verified": False,
            "dispatch_authorized": False, "eligible_for_task_dispatch": False, "dispatch_performed": False}


def provider_windows(value: dict, at: datetime) -> dict:
    local, utc = at.astimezone(BJT), at.astimezone(UTC)
    observed, expires = parse_timestamp(RULE_OBSERVED_AT), parse_timestamp(RULE_EXPIRES_AT)
    rules_current = observed <= utc < expires
    qoder, task = value.get("qoder", {}), value.get("task", {})
    regular = local.time() >= time(22) or local.time() < time(8)
    service = time(1) <= local.time() < time(7)
    account = qoder.get("account_type", "unknown")
    offpeak = (regular if account == "regular" else service if account == "service_account" else None) if rules_current else None
    eligibility = receipt_status(qoder.get("eligibility", {}), at, task.get("scope_sha256"),
                                 task.get("own_subject_sha256"))
    peak_hour = time(1) <= utc.time() < time(4) or time(6) <= utc.time() < time(10)
    calendar = value.get("holiday_calendar", {})
    calendar_used = False
    if not rules_current:
        classification, calendar_reason = "needs_revalidation", "rule_snapshot_not_current"
    elif utc.weekday() >= 5 or not peak_hour:
        classification, calendar_reason = "documented_offpeak", "holiday_not_needed_for_this_time"
    else:
        calendar_reason = "missing_current_supplier_holiday_claim"
        if calendar.get("source_kind") == "stock_exchange":
            calendar_reason = "stock_calendar_is_not_supplier_calendar"
        usable = (calendar.get("source_kind") == "supplier_public_holidays" and
                  calendar.get("date") == utc.date().isoformat() and
                  "is_public_holiday" in calendar and reference_status(calendar, at) == "current_external_claim")
        if usable:
            calendar_used, calendar_reason = True, "current_external_calendar_claim"
            classification = "offpeak_given_calendar_claim" if calendar["is_public_holiday"] else "peak_given_calendar_claim"
        else:
            classification = "unknown"
    return {"rules_snapshot_date": RULE_SNAPSHOT_DATE, "rules_observed_at_utc": observed.isoformat(),
        "rules_expires_at_utc": expires.isoformat(), "rules_current_for_requested_time": rules_current,
        "rule_status": "current_snapshot" if rules_current else "needs_revalidation",
        "rules_validity_policy_provisional": True, "account_calls_or_bills_verified": False,
        "qoder_cn": {"source": QODER_SOURCE, "documented_model": "Qwen3.8-Max",
            "selected_model_unchanged": True, "account_type_claim": account,
            "regular_product_offpeak_now": regular if rules_current else None,
            "service_account_offpeak_now": service if rules_current else None,
            "account_window_offpeak_given_type_claim": offpeak,
            "standard_credit_multiplier": 0.5, "offpeak_credit_multiplier": 0.2,
            "offpeak_to_standard_ratio": 0.4, "promotion_start_bjt": "2026-09-04T22:00:00+08:00",
            "promotion_end_announced": False, "rule_date_after_promotion_start": local >=
                datetime(2026, 9, 4, 22, tzinfo=BJT), "eligibility_claim_status": eligibility,
            "discount_candidate_given_eligibility_claim": offpeak is True and eligibility == "current_external_claim"
                and qoder.get("selected_model") == "Qwen3.8-Max" and local >= datetime(2026, 9, 4, 22, tzinfo=BJT),
            "account_eligibility_verified": False, "actual_credit_multiplier": None},
        "deepseek": {"source": DEEPSEEK_SOURCE, "classification": classification,
            "weekday_and_peak_hour_utc": utc.weekday() < 5 and peak_hour,
            "calendar_claim_used": calendar_used, "calendar_claim_status": calendar_reason,
            "calendar_verified": False, "offpeak_to_peak_price_ratio": 0.5, "actual_cost": None}}


def sample_is_current(sample: dict, at: datetime, task: dict) -> bool:
    required = SAMPLE_FIELDS - {"instance_sha256"}
    bindings = {"instance_sha256": task.get("instance_subject_sha256"), "scope_sha256": task.get("scope_sha256"),
                "workload_sha256": task.get("workload_sha256"), "units_kind": task.get("units_kind")}
    if not required.issubset(sample) or any(not expected or sample.get(key) != expected for key, expected in bindings.items()):
        return False
    observed, expires = parse_timestamp(sample["observed_at"]), parse_timestamp(sample["expires_at"])
    return (observed <= at < expires and observed < expires and sample["verification_status"] == "verified"
            and sample["elapsed_seconds"] > 0 and sample["completed_units"] > 0 and sample["healthy"] is True)


def concurrency_advice(value: dict, at: datetime, phase: str) -> dict:
    workload = value.get("workload", {})
    current, requested = workload.get("current_concurrency", 1), workload.get("requested_concurrency", 1)
    result = {"recommendation": "hold_current_concurrency", "suggested_concurrency": current,
              "basis": "no_verified_cloud_execution", "sample_claims_verified_by_this_tool": False,
              "cpu_ceiling_percent": 90, "memory_ceiling_percent": 80,
              "minimum_useful_throughput_gain_ratio": 1.05, "synthetic_load_or_memory_fill_allowed": False}
    if phase != "work_window":
        result["recommendation"] = "pause_expansion_save_receipts" if phase == "closeout" else "wait_for_window"
        return result
    if workload.get("pending_units", 0) == 0:
        result["recommendation"] = "idle_no_synthetic_work"
        return result
    samples = workload.get("huawei_x_samples", [])
    task = value.get("task", {})
    if len(samples) != 2 or not all(sample_is_current(s, at, task) for s in samples):
        result["basis"] = "missing_current_bound_cloud_sample_claims"
        return result
    baseline, candidate = samples
    if baseline["concurrency"] != current or candidate["concurrency"] != requested or requested <= current:
        result["basis"] = "candidate_concurrency_not_observed"
        return result
    baseline_rate = baseline["completed_units"] / baseline["elapsed_seconds"]
    candidate_rate = candidate["completed_units"] / candidate["elapsed_seconds"]
    if not math.isfinite(baseline_rate) or not math.isfinite(candidate_rate):
        result["basis"] = "invalid_derived_throughput"
        return result
    gain = candidate_rate / baseline_rate
    if not math.isfinite(gain):
        result["basis"] = "invalid_derived_throughput"
        return result
    # Preserve inclusive decimal thresholds: binary float division can turn an
    # exact 5% improvement into 4.99999999999998%, or 110% P95 into an excess.
    exact_gain = (Fraction(candidate["completed_units"]) * Fraction(str(baseline["elapsed_seconds"])) /
                  (Fraction(baseline["completed_units"]) * Fraction(str(candidate["elapsed_seconds"]))))
    failure = lambda s: Fraction(s["failed_units"], s["completed_units"] + s["failed_units"])
    if (exact_gain < Fraction(21, 20) or failure(candidate) > failure(baseline) or
            Fraction(str(candidate["p95_latency_seconds"])) > Fraction(str(baseline["p95_latency_seconds"])) * Fraction(11, 10) or
            any(s["cpu_utilization_percent"] > 90 or s["memory_utilization_percent"] > 80 for s in samples)):
        result["basis"] = "useful_throughput_or_health_gate_not_met"
        return result
    result.update(recommendation="consider_candidate_after_independent_verification",
                  suggested_concurrency=requested, basis="unverified_cloud_sample_claims")
    return result


def evaluate(at: str, value: dict | None = None, closeout_minutes: int = 30) -> dict:
    instant = parse_timestamp(at)
    value = validate_input({} if value is None else value)
    window = night_window(instant, closeout_minutes)
    evidence = readiness(value, instant)
    candidate = window["may_expand_plan"] and evidence["prerequisites_satisfied_given_trusted_evidence"]
    return {"schema": "openplanlink.night-schedule/1", "spec_id": "013-night-scheduling",
        "at_utc": instant.isoformat(), "at_bjt": instant.astimezone(BJT).isoformat(),
        "scope": "planning_and_external_claim_readiness_only", "window": window,
        "provider_rules": provider_windows(value, instant), "readiness": evidence,
        "planning_status": "candidate_requires_independent_verification" if candidate else "blocked_or_outside_window",
        "concurrency": concurrency_advice(value, instant, window["phase"]),
        "measurement": {"local": {"sample_claim_count": len(value.get("workload", {}).get("local_samples", [])),
                                  "measurement_verified_by_this_tool": False},
            "huawei_x": {"measurement_status": "unmeasured", "verified_jobs": 0,
                "scope": "jobs_initiated_and_independently_verified_by_this_component",
                "sample_claim_count": len(value.get("workload", {}).get("huawei_x_samples", [])),
                "instance_verified": False, "cpu_utilization_percent": None, "peak_memory_bytes": None,
                "wall_time_seconds": None, "throughput": None, "queue_wait_seconds": None,
                "cost": None, "execution_receipt": None, "local_benchmark_substituted": False}},
        "execution_interfaces_integrated": False, "jobs_dispatched": 0,
        "automations_created": 0, "network_access_performed": False,
        "credentials_read": False, "overall_a2a_and_huawei_execution_goal_completed": False}


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid_cli_arguments")


def main(argv=None) -> int:
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--at", required=True, help="ISO 8601 timestamp with Z or numeric timezone offset")
    parser.add_argument("--input", type=Path, help="optional bounded planning claims JSON, never credentials")
    parser.add_argument("--output", type=Path, help="optional new JSON file; existing files are refused")
    parser.add_argument("--closeout-minutes", type=int, default=30)
    try:
        args = parser.parse_args(argv)
        value = {}
        if args.input is not None:
            with args.input.open("rb") as handle:
                value = strict_input(handle.read(MAX_BYTES + 1))
        result = evaluate(args.at, value, args.closeout_minutes)
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output is not None:
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
        print(serialized, end="")
        return 0
    except (ValueError, OSError, UnicodeError, RecursionError, OverflowError) as error:
        # Never echo argparse values, filenames, exceptions, or raw input.
        print(json.dumps({"schema": "openplanlink.night-schedule-error/1", "result": "failed",
                          "error_type": type(error).__name__, "error_code": "invalid_input_or_output"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
