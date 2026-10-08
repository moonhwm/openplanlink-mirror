#!/usr/bin/env python
"""Local, standard-library memory tier pilot; no cloud or host sampling.

OPL-MEM-TIER-PILOT-20261008-01 / codex-review-20261005
Reuses CasStore for full originals and memory_risk for missing OS evidence.
Tier labels are logical recommendations, never physical moves or evictions.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import sqlite3
import tempfile

try:
    from .cas_store import CasStore
    from .memory_sample_audit import memory_risk
except ImportError:  # Direct CLI invocation.
    from cas_store import CasStore
    from memory_sample_audit import memory_risk

PILOT_ID = "OPL-MEM-TIER-PILOT-20261008-01"
AUTHOR = "codex-review-20261005"
TIERS = ("hot", "warm", "cold")
GIB = 1024 ** 3


class EventConflict(ValueError):
    """The same event identity cannot authorize a different operation."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def numeric(value, name, minimum=0):
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or value < minimum):
        raise ValueError(name + " must be finite and >= " + str(minimum))
    return value


class TierPolicy:
    def __init__(self, hot_min_accesses=3, warm_min_accesses=1,
                 hot_recency_hours=24, warm_recency_hours=168,
                 access_window_hours=168, hot_max_latency_ms=20,
                 warm_max_latency_ms=200, capacities_bytes=None,
                 warning_ratio=0.8):
        for name, value in (("hot_min_accesses", hot_min_accesses),
                            ("warm_min_accesses", warm_min_accesses)):
            if type(value) is not int or value < 1:
                raise ValueError(name + " must be a positive integer")
        self.hot_min_accesses = hot_min_accesses
        self.warm_min_accesses = warm_min_accesses
        self.hot_recency_hours = numeric(hot_recency_hours, "hot_recency_hours")
        self.warm_recency_hours = numeric(warm_recency_hours, "warm_recency_hours")
        self.access_window_hours = numeric(access_window_hours, "access_window_hours", 0.001)
        self.hot_max_latency_ms = numeric(hot_max_latency_ms, "hot_max_latency_ms")
        self.warm_max_latency_ms = numeric(warm_max_latency_ms, "warm_max_latency_ms")
        self.warning_ratio = numeric(warning_ratio, "warning_ratio", 0.001)
        if (hot_min_accesses < warm_min_accesses
                or hot_recency_hours > warm_recency_hours
                or hot_max_latency_ms > warm_max_latency_ms or warning_ratio > 1):
            raise ValueError("inconsistent tier policy")
        self.capacities_bytes = {tier: None for tier in TIERS}
        if capacities_bytes is not None:
            if set(capacities_bytes) - set(TIERS):
                raise ValueError("unknown capacity tier")
            for tier, capacity in capacities_bytes.items():
                if capacity is not None and (type(capacity) is not int or capacity < 1):
                    raise ValueError("capacity must be a positive integer or null")
                self.capacities_bytes[tier] = capacity

    def classify(self, count, age_hours, latency_budget_ms):
        # Budget is a requested retrieval SLA, not an observed latency.
        if latency_budget_ms is not None and latency_budget_ms <= self.hot_max_latency_ms:
            return "hot", "requested_latency_budget"
        if (age_hours is not None and count >= self.hot_min_accesses
                and age_hours <= self.hot_recency_hours):
            return "hot", "access_count_and_recency"
        if latency_budget_ms is not None and latency_budget_ms <= self.warm_max_latency_ms:
            return "warm", "requested_latency_budget"
        if (age_hours is not None and count >= self.warm_min_accesses
                and age_hours <= self.warm_recency_hours):
            return "warm", "access_count_and_recency"
        return "cold", "no_recent_demand_in_observed_event_window"

    def as_dict(self):
        return dict(self.__dict__)


class MemoryTierPilot:
    """Caller supplies authorized data; bundled demo and tests use only synthetic text.

    SQLite serializes metadata/event commits. CAS uses its existing separate DB:
    a failed/crashed CAS write may leave an orphan, but cannot consume an event.
    No background workers, outbound APIs, original deletion, or physical tiering.
    """
    def __init__(self, root, policy=None):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy = policy or TierPolicy()
        self.cas = CasStore(str(self.root / "originals"))
        self.db = sqlite3.connect(str(self.root / "pilot.sqlite"))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS objects(
                hash TEXT PRIMARY KEY, size INTEGER NOT NULL,
                created_at TEXT NOT NULL, latency_budget_ms REAL, evidence_kind TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS refs(
                ref_id TEXT PRIMARY KEY, original_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS accesses(
                event_id TEXT PRIMARY KEY, original_hash TEXT NOT NULL, accessed_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()
        # Existing CasStore exposes no close method.
        self.cas._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def original(self, original_hash):
        if (not isinstance(original_hash, str) or len(original_hash) != 64
                or any(c not in "0123456789abcdef" for c in original_hash)):
            raise ValueError("original_hash must be a full SHA-256 hex digest")
        data = self.cas.get(original_hash)
        if hashlib.sha256(data).hexdigest() != original_hash:
            raise ValueError("original integrity mismatch")
        return data

    def consume(self, event_id, event_type, source, payload):
        """event_driven-compatible type/source/payload/key semantics, durable and fail closed.

        Timestamp belongs in payload. Dictionary key order is immaterial; array
        order and operation/source are significant. Only successful operations
        are committed, so failed operations can be retried with the same identity.
        """
        if any(not isinstance(v, str) or not v for v in (event_id, event_type, source)):
            raise ValueError("event identity, type and source must be nonempty strings")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        fingerprint = hashlib.sha256(canonical([event_type, source, payload]).encode("utf-8")).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
            if previous is not None:
                if previous["fingerprint"] != fingerprint:
                    raise EventConflict("event_id reused with a different payload, type or source")
                self.db.commit()
                return {"ok": True, "duplicate": True, "result": json.loads(previous["result"])}
            timestamp = utc(payload["occurred_at_utc"]).isoformat()
            if event_type == "memory_ingest":
                result = self._ingest(payload, timestamp)
            elif event_type == "memory_access":
                digest = payload["original_hash"]
                self.original(digest)  # Verify bytes before updating demand evidence.
                if self.db.execute("SELECT 1 FROM objects WHERE hash=?", (digest,)).fetchone() is None:
                    raise ValueError("unknown original")
                self.db.execute("INSERT INTO accesses VALUES(?,?,?)", (event_id, digest, timestamp))
                result = {"original_hash": digest, "access_recorded": True}
            else:
                raise ValueError("unsupported event type")
            self.db.execute("INSERT INTO events VALUES(?,?,?)", (event_id, fingerprint, canonical(result)))
            self.db.commit()
            return {"ok": True, "duplicate": False, "result": result}
        except Exception:
            self.db.rollback()
            raise

    def _ingest(self, payload, timestamp):
        text, ref_id = payload["text"], payload["reference_id"]
        kind = payload["evidence_kind"]
        if not isinstance(text, str) or not isinstance(ref_id, str) or not ref_id:
            raise ValueError("text and reference_id must be strings")
        if kind not in ("synthetic", "authorized_local"):
            raise ValueError("explicit synthetic/authorized_local evidence kind required")
        budget = payload.get("latency_budget_ms")
        if budget is not None:
            numeric(budget, "latency_budget_ms")
        data = text.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        previous_ref = self.db.execute("SELECT original_hash FROM refs WHERE ref_id=?", (ref_id,)).fetchone()
        if previous_ref is not None and previous_ref[0] != digest:
            raise EventConflict("reference_id cannot replace its full original")
        previous = self.db.execute("SELECT * FROM objects WHERE hash=?", (digest,)).fetchone()
        if previous is not None:
            if previous["evidence_kind"] != kind:
                raise ValueError("mixed evidence kinds for the same original")
            self.original(digest)
            budgets = [b for b in (budget, previous["latency_budget_ms"]) if b is not None]
            self.db.execute("UPDATE objects SET latency_budget_ms=? WHERE hash=?",
                            (min(budgets) if budgets else None, digest))
        else:
            stored = self.cas.put(data)
            if stored != digest or self.original(stored) != data:
                raise ValueError("CAS did not preserve full original")
            self.db.execute("INSERT INTO objects VALUES(?,?,?,?,?)", (digest, len(data), timestamp, budget, kind))
        self.db.execute("INSERT OR IGNORE INTO refs VALUES(?,?)", (ref_id, digest))
        return {"original_hash": digest, "reference_id": ref_id,
                "deduplicated": previous is not None, "full_original_retained": True}

    def report(self, now_utc, synthetic_rates_per_gib_month=None):
        """Read one SQLite snapshot; verify all retained original bytes."""
        self.db.execute("BEGIN")
        try:
            return self._report(now_utc, synthetic_rates_per_gib_month)
        finally:
            self.db.rollback()  # Read transaction only, including invalid evidence.

    def _report(self, now_utc, synthetic_rates_per_gib_month):
        now = utc(now_utc)
        window_start = now - dt.timedelta(hours=self.policy.access_window_hours)
        objects, used = [], {tier: 0 for tier in TIERS}
        for row in self.db.execute("SELECT * FROM objects ORDER BY hash"):
            if len(self.original(row["hash"])) != row["size"]:
                raise ValueError("original size differs from metadata")
            if utc(row["created_at"]) > now:
                raise ValueError("report precedes ingestion evidence")
            accesses = [utc(r[0]) for r in self.db.execute(
                "SELECT accessed_at FROM accesses WHERE original_hash=?", (row["hash"],))]
            if any(t > now for t in accesses):
                raise ValueError("future access evidence cannot drive a report")
            recent = [t for t in accesses if t >= window_start]
            last = max(accesses) if accesses else None
            age = (now - last).total_seconds() / 3600 if last else None
            tier, reason = self.policy.classify(len(recent), age, row["latency_budget_ms"])
            refs = [r[0] for r in self.db.execute("SELECT ref_id FROM refs WHERE original_hash=? ORDER BY ref_id", (row["hash"],))]
            used[tier] += row["size"]
            objects.append({"original_hash": row["hash"], "logical_original_bytes": row["size"],
                            "reference_ids": refs, "tier": tier, "tier_reason": reason,
                            "accesses_in_window": len(recent), "last_access_utc": last.isoformat() if last else None,
                            "requested_latency_budget_ms": row["latency_budget_ms"],
                            "observed_latency_ms": None, "evidence_kind": row["evidence_kind"],
                            "full_original_retained": True})
        capacity = {}
        for tier in TIERS:
            limit = self.policy.capacities_bytes[tier]
            ratio = used[tier] / limit if limit is not None else None
            state = "unknown" if ratio is None else ("exceeded" if ratio > 1 else
                    "warning" if ratio >= self.policy.warning_ratio else "within_limit")
            capacity[tier] = {"used_logical_bytes": used[tier], "capacity_bytes": limit,
                              "utilization_ratio": ratio, "state": state}
        rates = synthetic_rates_per_gib_month
        if rates is not None:
            if set(rates) != set(TIERS):
                raise ValueError("synthetic rates must specify all three tiers")
            for tier in TIERS:
                numeric(rates[tier], tier + " rate")
        components = {tier: used[tier] / GIB * rates[tier] if rates is not None else None for tier in TIERS}
        unique_bytes = sum(used.values())
        baseline_bytes = sum(obj["logical_original_bytes"] * len(obj["reference_ids"]) for obj in objects)
        return {
            "pilot_id": PILOT_ID, "author": AUTHOR, "report_at_utc": now.isoformat(),
            "execution_scope": "local_logical_pilot", "demo": bool(objects) and all(o["evidence_kind"] == "synthetic" for o in objects),
            "policy": self.policy.as_dict(), "objects": objects, "capacity": capacity,
            "baseline": {"without_dedup_reference_bytes": baseline_bytes, "unique_original_bytes": unique_bytes,
                         "avoided_duplicate_bytes": baseline_bytes - unique_bytes,
                         "all_hot_estimate_units_per_month": unique_bytes / GIB * rates["hot"] if rates is not None else None},
            "cost": {"kind": "synthetic_estimate" if rates is not None else "not_estimated",
                     "unit": "synthetic_units_per_month", "rates_per_gib_month": rates,
                     "components": components, "estimated_total": sum(components.values()) if rates is not None else None,
                     "actual_cloud_bill": None, "billing_evidence": None,
                     "exclusions": ["CPU", "RAM", "requests", "egress", "replicas", "compression", "metadata", "queue"]},
            "resources": {"cpu_seconds": None, "memory_peak_bytes": None, "elapsed_seconds": None,
                          "throughput_events_per_second": None, "queue_wait_seconds": None,
                          "cloud_cost": None, "host_identity": None},
            "os_memory_risk": memory_risk({}, now.isoformat()),
            "event_ledger_count": self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "claims": {"cloud_synced": False, "cloud_online": None, "external_receipt": None,
                       "physical_tiers_moved": False, "originals_deleted": False},
        }


def demo(root):
    """Reproducible, entirely artificial fixture, safe to publish."""
    policy = TierPolicy(capacities_bytes={"hot": 40, "warm": 100, "cold": 100})
    with MemoryTierPilot(root, policy) as pilot:
        base = {"evidence_kind": "synthetic", "occurred_at_utc": "2026-10-01T00:00:00Z"}
        texts = ("SYNTHETIC demo original A: frequent lookup.",
                 "SYNTHETIC demo original B: occasional lookup.",
                 "SYNTHETIC demo original C: archival fixture.")
        results = []
        for i, text in enumerate(texts):
            payload = dict(base, text=text, reference_id="demo-reference-" + str(i))
            results.append(pilot.consume("demo-ingest-" + str(i), "memory_ingest", "synthetic-fixture", payload))
        results.append(pilot.consume("demo-ingest-alias", "memory_ingest", "synthetic-fixture",
                                     dict(base, text=texts[0], reference_id="demo-reference-alias")))
        for i in range(3):
            payload = {"original_hash": results[0]["result"]["original_hash"],
                       "occurred_at_utc": "2026-10-08T00:00:0" + str(i) + "Z"}
            results.append(pilot.consume("demo-access-hot-" + str(i), "memory_access", "synthetic-fixture", payload))
        warm = {"original_hash": results[1]["result"]["original_hash"], "occurred_at_utc": "2026-10-06T00:00:00Z"}
        results.append(pilot.consume("demo-access-warm", "memory_access", "synthetic-fixture", warm))
        duplicate = pilot.consume("demo-access-warm", "memory_access", "synthetic-fixture", warm)
        try:
            pilot.consume("demo-access-warm", "memory_access", "synthetic-fixture",
                          dict(warm, occurred_at_utc="2026-10-07T00:00:00Z"))
        except EventConflict:
            conflict = {"status": "rejected", "reason": "event_id_payload_conflict", "side_effects": False}
        report = pilot.report("2026-10-08T01:00:00Z", {"hot": 10, "warm": 3, "cold": 1})
        report["demo_events"] = {"unique_fixture_events": len(results), "duplicate": duplicate, "conflict": conflict}
        report["note"] = "Entirely synthetic demonstration; cost rates are artificial, resources unmeasured, no cloud calls."
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True, help="use only bundled synthetic fixtures")
    parser.add_argument("--root", help="explicit local pilot directory; default is a temporary directory")
    parser.add_argument("--report", help="write strict JSON to an explicit local file")
    args = parser.parse_args(argv)
    if args.root:
        report = demo(args.root)
    else:
        with tempfile.TemporaryDirectory(prefix="opl-memory-tier-demo-") as root:
            report = demo(root)
    output = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.report:
        pathlib.Path(args.report).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
