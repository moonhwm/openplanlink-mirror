#!/usr/bin/env python3
"""slime_router.py -- K3 slime-mold collaboration architecture v1.2
trail-weighted routing (stigmergic port selection), single-file, stdlib only.

Subcommands:
  register  <pool> <endpoint> [--cost C] [--platform P]
  select    <pool> [--eta ETA]
  report    <pool> <endpoint> <ok|fail> [--latency_ms L] [--cost_units U] [--decay D]
            [--reason channel|task|compliance] [--target T]
  status    <pool>
  unfreeze  <pool> --target T
  heartbeat <pool> --cluster <id>
State: state/<pool>.json ; events: state/<pool>.events.jsonl ;
       heartbeats: state/<pool>.heartbeat.json

v1.1 (2026-09-09) upgrades from cluster-B reader-side findings:
  - state json carries ts_written / ttl_seconds (freshness) and a
    self-describing "protocol" section (semantics on disk).
  - status reports age_seconds / stale and per-cluster heartbeat liveness.
  - all state writes are atomic (tmp + os.replace) with .bak fallback on read.

v1.2 (2026-09-09) canary/revival fix (swarm finding):
  - the z exploration branch now draws uniformly from active+dormant;
    picking a dormant port is a legal "canary probe" (canary event).
  - a dormant port reported ok is revived: status->active with a small
    restart trail = CANARY_REVIVE_TRAIL_RATIO * mean(active trails),
    logged as a "revival" event; reported fail stays dormant (streak reset).
  - recovery from dormancy no longer relies solely on the D2 breaker.

v1.3 (2026-09-09) fail-reason classification:
  - report fail takes --reason channel|task|compliance (default channel,
    backward compatible with v1.2 behaviour).
  - channel: trail *= 0.5 and fail_count += 1 (unchanged).
  - task: task-layer unsolvable (e.g. pixels saturated); trail NOT
    punished, counted separately as task_fail_count, "task_fail" event.
  - compliance: forbidden by compliance (e.g. robots/LII); trail NOT
    punished, counted as compliance_count, "compliance_fail" event; with
    --target the target is frozen pool-wide (deduped "frozen_targets"
    list in state, "frozen_target" event). select is unchanged -- callers
    must honour status["frozen_targets"] themselves.
  - fail_rate numerator/denominator count channel-class fails only;
    status exposes fail_rate_channel / task_fail_count / compliance_count
    per endpoint and frozen_targets at pool level.

v1.4 (2026-09-09) manual unfreeze:
  - new subcommand "unfreeze <pool> --target T" removes T from pool-level
    frozen_targets. Unfreezing is a human adjudication action: the operator
    must confirm the compliance basis; the logged "unfrozen" event (with
    target and source="manual") is the audit trail.
  - unfreezing a target that is not frozen exits with code 1 and writes
    nothing to disk (no state save, no event).
"""

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time

# ---- v0.2 constants (defaults; CLI-overridable where noted) ----
ETA_DEFAULT = 2.0        # trail exponent in select (trail^ETA)
Z_EXPLORE = 0.03         # exploration floor (SMA.m L55)
DECAY_DEFAULT = 0.97     # pool-wide trail decay per report
DEP_BASE = 1.0           # deposit base for ok reports
DORM_STREAK = 10         # consecutive reports below share threshold -> dormancy
DORM_SHARE = 0.05        # share threshold (<5%) for dormancy (S1-S5 v2)
DORM_SHARE_AMEND_B = 0.08  # relaxed threshold when fail_rate > 10% (Amendment B)
FAIL_RATE_AMEND_B = 0.10
CC_WINDOW_S = 10.0       # common-cause batch window
CC_MIN_FAILS = 3         # >=3 distinct endpoints fail in window -> platform event

# ---- v1.1 freshness / protocol constants ----
TTL_SECONDS_DEFAULT = 300    # state snapshot freshness TTL for readers
HEARTBEAT_TTL = 120          # cluster heartbeat lease TTL
FAIL_PUNISH = 0.5            # trail multiplier on fail

# ---- v1.2 canary/revival constants ----
CANARY_REVIVE_TRAIL_RATIO = 0.1  # revival restart trail = 10% of mean(active)

# ---- v1.3 fail-reason classification ----
FAIL_REASONS = ["channel", "task", "compliance"]

# ---- v1.5 provenance / quality / herd / cc-dual-track constants ----
PROVS = ["real", "replay", "synthetic"]
EVIDENCE_LEVELS = {"L0": "unattributed", "L1": "synthetic", "L2": "replay",
                   "L3": "real", "L4": "reviewed_real"}
QUALITY_SRCS = ["blind_review", "auto", "manual"]
HERD_WINDOW = 20          # last N selects examined for herd share
HERD_THRESHOLD = 0.6      # >60% share -> herd risk / damping
HERD_DISCOUNT = 0.5       # temporary weight discount when damped
CC_KINDS = ["cc_supplier", "cc_environment"]
BUS_CLIENT_PATH = "/mnt/agents/output/runs_r99/slime_bus/slime_bus.py"

# Self-describing protocol section persisted into every state snapshot so a
# reader can interpret the fields without an external README.
PROTOCOL = {
    "version": "1.5",
    "fail_reasons": list(FAIL_REASONS),
    "provs": list(PROVS),
    "evidence_levels": dict(EVIDENCE_LEVELS),
    "quality_srcs": list(QUALITY_SRCS),
    "herd_window": HERD_WINDOW,
    "herd_threshold": HERD_THRESHOLD,
    "herd_discount": HERD_DISCOUNT,
    "cc_kinds": list(CC_KINDS),
    "bus_direct": True,
    "eta": ETA_DEFAULT,
    "z_explore": Z_EXPLORE,
    "decay": DECAY_DEFAULT,
    "dorm_streak": DORM_STREAK,
    "dorm_share": DORM_SHARE,
    "fail_punish": FAIL_PUNISH,
    "cc_window_s": CC_WINDOW_S,
    "cc_min_eps": CC_MIN_FAILS,
    "canary_revival_trail_ratio": CANARY_REVIVE_TRAIL_RATIO,
}

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")


def _now():
    return time.time()


class CCFrozen(dict):
    """status view of common_cause_frozen: an object {active, kind} whose
    truthiness follows "active" (keeps v1.4-era truthy/falsy checks valid)."""

    def __bool__(self):
        return bool(self.get("active"))


def _norm_frozen(val):
    """Normalise common_cause_frozen to the v1.5 object form."""
    if isinstance(val, dict):
        return {"active": bool(val.get("active")), "kind": val.get("kind")}
    # legacy bool
    return {"active": bool(val), "kind": "cc_supplier" if val else None}


def verify_event_chain(path):
    """Verify the sha256 prev_hash chain of an events.jsonl file.
    Returns (ok, bad_line_index_or_None). First line must anchor GENESIS."""
    prev = "GENESIS"
    if not os.path.exists(path):
        return True, None
    with open(path, "rb") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                return False, i
            if rec.get("prev_hash") != prev:
                return False, i
            prev = hashlib.sha256(line).hexdigest()
    return True, None


class Router:
    """Core router; time and RNG injectable for deterministic tests."""

    def __init__(self, state_dir=STATE_DIR, rng=None, now_fn=None):
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)
        self.rng = rng or random.Random()
        self.now_fn = now_fn or _now

    # ---------- persistence ----------
    def _path(self, pool):
        return os.path.join(self.state_dir, "%s.json" % pool)

    def _events_path(self, pool):
        return os.path.join(self.state_dir, "%s.events.jsonl" % pool)

    def _heartbeat_path(self, pool):
        return os.path.join(self.state_dir, "%s.heartbeat.json" % pool)

    @staticmethod
    def _default_state(pool):
        return {"pool": pool, "common_cause_frozen": False,
                "recent_fails": [], "endpoints": {}}

    @staticmethod
    def _backfill(st):
        """v1.1 backward compatibility: default any missing new fields."""
        st.setdefault("ttl_seconds", TTL_SECONDS_DEFAULT)
        st.setdefault("ts_written", None)  # unknown age for legacy snapshots
        st.setdefault("frozen_targets", [])  # v1.3 pool-level target freeze
        st.setdefault("recent_selects", [])  # v1.5 herd damping window
        st["common_cause_frozen"] = _norm_frozen(
            st.get("common_cause_frozen", False))
        for v in st.get("endpoints", {}).values():
            v.setdefault("task_fail_count", 0)
            v.setdefault("compliance_count", 0)
            tbp = v.setdefault("trail_by_prov", {})
            for p_ in PROVS:
                tbp.setdefault(p_, 0.0)
        proto = dict(PROTOCOL)
        proto.update(st.get("protocol") or {})
        st["protocol"] = proto
        return st

    def _load(self, pool):
        p = self._path(pool)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return self._backfill(json.load(f))
            except (ValueError, OSError):
                # half-write / corruption guard: fall back to last backup
                bak = p + ".bak"
                if os.path.exists(bak):
                    with open(bak, "r", encoding="utf-8") as f:
                        return self._backfill(json.load(f))
                raise
        return self._backfill(self._default_state(pool))

    def _save(self, pool, st):
        p = self._path(pool)
        st["ts_written"] = self.now_fn()
        st.setdefault("ttl_seconds", TTL_SECONDS_DEFAULT)
        proto = dict(PROTOCOL)
        proto.update(st.get("protocol") or {})
        st["protocol"] = proto
        # keep a backup of the previous good version before overwriting
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    old = f.read()
                with open(p + ".bak", "w", encoding="utf-8") as f:
                    f.write(old)
            except OSError:
                pass
        # atomic write: tmp file + os.replace (no torn reads)
        tmp = p + ".tmp.%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)

    def _log(self, pool, event, **kw):
        rec = {"ts": self.now_fn(), "event": event}
        rec.update(kw)
        p = self._events_path(pool)
        # v1.5 tamper-evident chain: prev_hash = sha256 of the previous raw
        # line (including its newline); first line anchored to "GENESIS".
        prev = "GENESIS"
        if os.path.exists(p):
            last = None
            with open(p, "rb") as f:
                for line in f:
                    if line.strip():
                        last = line
            if last is not None:
                prev = hashlib.sha256(last).hexdigest()
        rec["prev_hash"] = prev
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    # ---------- helpers ----------
    @staticmethod
    def _fail_rate(ep):
        tot = ep["ok_count"] + ep["fail_count"]
        return (ep["fail_count"] / tot) if tot else 0.0

    @staticmethod
    def _shares(st, active_only=True):
        eps = st["endpoints"]
        cand = {k: v for k, v in eps.items()
                if (v["status"] == "active" or not active_only)}
        tot = sum(max(v["trail"], 0.0) for v in cand.values())
        return {k: (max(v["trail"], 0.0) / tot if tot > 0 else 0.0)
                for k, v in cand.items()}

    # ---------- register ----------
    def register(self, pool, endpoint, cost=1.0, platform="default"):
        st = self._load(pool)
        eps = st["endpoints"]
        if endpoint not in eps:
            eps[endpoint] = {"trail": 1.0, "cost": float(cost),
                             "platform": platform, "status": "active",
                             "ok_count": 0, "fail_count": 0,
                             "task_fail_count": 0, "compliance_count": 0,
                             "below_streak": 0, "reports": 0,
                             "trail_by_prov": {"real": 1.0, "replay": 0.0,
                                               "synthetic": 0.0},
                             "events": {}}
            self._log(pool, "register", endpoint=endpoint, cost=cost,
                      platform=platform)
        else:
            eps[endpoint]["cost"] = float(cost)
            eps[endpoint]["platform"] = platform
        self._save(pool, st)
        return eps[endpoint]

    # ---------- select ----------
    def select(self, pool, eta=ETA_DEFAULT):
        st = self._load(pool)
        eps = st["endpoints"]
        active = [k for k, v in eps.items() if v["status"] == "active"]
        dormant = [k for k, v in eps.items() if v["status"] == "dormant"]

        # D2 circuit-breaker: <2 active -> wake dormant with lowest fail_rate
        if len(active) < 2 and dormant:
            wake = min(dormant, key=lambda k: (self._fail_rate(eps[k]), k))
            eps[wake]["status"] = "active"
            eps[wake]["below_streak"] = 0
            self._log(pool, "reactivation", endpoint=wake,
                      fail_rate=self._fail_rate(eps[wake]),
                      active_before=len(active))
            active.append(wake)
            self._save(pool, st)

        if not active:
            self._save(pool, st)
            return None

        # common-cause freeze: prefer a different platform than the failed
        # one -- only for cc_supplier (v1.5 dual-track); cc_environment
        # freezes decay only and does NOT exclude any platform.
        candidates = list(active)
        ccf = _norm_frozen(st.get("common_cause_frozen"))
        if ccf["active"] and ccf["kind"] == "cc_supplier" \
                and st["recent_fails"]:
            last_fail = st["recent_fails"][-1]["endpoint"]
            bad_plat = eps.get(last_fail, {}).get("platform")
            others = [k for k in candidates
                      if eps[k]["platform"] != bad_plat]
            if others:
                candidates = others

        # z exploration floor: uniform random over active+dormant (v1.2).
        # Picking a dormant port is a legal "canary probe": the selection
        # returns normally and a canary event is logged, so exploration
        # traffic can rediscover dormant ports (previously D2-only).
        if self.rng.random() < Z_EXPLORE:
            explore_pool = candidates + [k for k in dormant
                                         if k not in candidates]
            choice = self.rng.choice(explore_pool)
            if eps[choice]["status"] == "dormant":
                self._log(pool, "canary", endpoint=choice,
                          active=len(active), dormant=len(dormant))
        else:
            # v1.5 provenance: route on the real book only; fall back to
            # the total book when no real data exists (low_real mode).
            base = {k: max(eps[k]["trail_by_prov"].get("real", 0.0), 0.0)
                    for k in candidates}
            if sum(base.values()) <= 0:
                base = {k: max(eps[k]["trail"], 0.0) for k in candidates}
            # v1.5 herd damping: an endpoint with >60% of the last
            # HERD_WINDOW selects gets a temporary x0.5 weight discount.
            recent = st.get("recent_selects", [])[-HERD_WINDOW:]
            damped = set()
            if recent:
                for k in candidates:
                    share = recent.count(k) / float(len(recent))
                    if share > HERD_THRESHOLD:
                        damped.add(k)
            weights = [(base[k] * (HERD_DISCOUNT if k in damped else 1.0))
                       ** eta for k in candidates]
            for k in sorted(damped):
                self._log(pool, "damping", endpoint=k,
                          herd_share=recent.count(k) / float(len(recent)),
                          discount=HERD_DISCOUNT)
            tot = sum(weights)
            if tot <= 0:
                choice = self.rng.choice(candidates)
            else:
                r = self.rng.random() * tot
                acc = 0.0
                choice = candidates[-1]
                for k, w in zip(candidates, weights):
                    acc += w
                    if r <= acc:
                        choice = k
                        break
        # v1.5: track recent selections for herd damping / herd_risk
        recent = st.setdefault("recent_selects", [])
        recent.append(choice)
        del recent[:-HERD_WINDOW]
        self._save(pool, st)
        return choice

    # ---------- report ----------
    def report(self, pool, endpoint, ok, latency_ms=None, cost_units=None,
               decay=DECAY_DEFAULT, reason="channel", target=None,
               prov="real", quality=None, quality_src=None):
        if reason not in FAIL_REASONS:
            raise ValueError("unknown fail reason: %r (want one of %s)"
                             % (reason, FAIL_REASONS))
        if prov not in PROVS:
            raise ValueError("unknown provenance: %r (want one of %s)"
                             % (prov, PROVS))
        if quality is not None and not (0.0 <= float(quality) <= 10.0):
            raise ValueError("quality must be in [0, 10], got %r" % quality)
        if quality_src is not None and quality_src not in QUALITY_SRCS:
            raise ValueError("unknown quality_src: %r (want one of %s)"
                             % (quality_src, QUALITY_SRCS))
        st = self._load(pool)
        eps = st["endpoints"]
        if endpoint not in eps:
            self.register(pool, endpoint)
            st = self._load(pool)
            eps = st["endpoints"]
        ep = eps[endpoint]
        now = self.now_fn()
        frozen_now = False

        # ---- common-cause detection (before decay) ----
        # Only channel-class fails are real channel failures: task fails are
        # unsolvable tasks and compliance fails are prohibited targets, so
        # neither feeds the common-cause window (channel is blameless).
        channel_fail = (not ok) and reason == "channel"
        ccf = _norm_frozen(st.get("common_cause_frozen"))
        win = [f for f in st["recent_fails"] if now - f["ts"] <= CC_WINDOW_S]
        if channel_fail:
            win.append({"endpoint": endpoint, "ts": now})
            distinct = {f["endpoint"] for f in win}
            if len(distinct) >= CC_MIN_FAILS and not ccf["active"]:
                # v1.5 dual-track classification: identical platforms across
                # the failing endpoints -> supplier-side common cause
                # (platform exclusion applies); differing platforms ->
                # environment-side (decay freeze only, no exclusion).
                plats = {eps.get(f["endpoint"], {}).get("platform")
                         for f in win}
                kind = "cc_supplier" if len(plats) == 1 else "cc_environment"
                ccf = {"active": True, "kind": kind}
                st["common_cause_frozen"] = ccf
                frozen_now = True
                self._log(pool, "common_cause", endpoints=sorted(distinct),
                          kind=kind, platforms=sorted(p for p in plats
                                                      if p is not None))
        else:
            # window clean and an ok arrived -> clear platform freeze
            if not win and ccf["active"]:
                st["common_cause_frozen"] = {"active": False, "kind": None}
                self._log(pool, "common_cause_cleared", endpoint=endpoint)
        st["recent_fails"] = win

        # ---- deposit / penalty ----
        dormant_before = ep["status"] == "dormant"
        if ok:
            if dormant_before:
                # v1.2 revival: canary probe succeeded -> back to active with
                # a small restart trail (10% of mean active trail) so its
                # trail^ETA does not instantly monopolise routing.
                act = [v for k, v in eps.items()
                       if k != endpoint and v["status"] == "active"]
                mean_active = (sum(max(v["trail"], 0.0) for v in act)
                               / len(act)) if act else DEP_BASE
                ep["trail"] = CANARY_REVIVE_TRAIL_RATIO * mean_active
                ep["trail_by_prov"][prov] = \
                    ep["trail_by_prov"].get(prov, 0.0) + ep["trail"]
                ep["status"] = "active"
                ep["below_streak"] = 0
                self._log(pool, "revival", endpoint=endpoint,
                          trail=ep["trail"], mean_active_trail=mean_active,
                          prov=prov)
            else:
                dep = DEP_BASE
                if cost_units:
                    dep *= 1.0 / max(float(cost_units), 1e-9)
                if latency_ms is not None:
                    dep *= 1000.0 / max(float(latency_ms), 1.0)
                if quality is not None:
                    # v1.5 quality-weighted deposit (x0.5 .. x1.5)
                    dep *= 0.5 + float(quality) / 10.0
                ep["trail"] += dep
                ep["trail_by_prov"][prov] = \
                    ep["trail_by_prov"].get(prov, 0.0) + dep
                if quality is not None:
                    self._log(pool, "deposit", endpoint=endpoint, prov=prov,
                              quality=float(quality),
                              quality_src=quality_src, dep=dep)
            ep["ok_count"] += 1
        elif reason == "task":
            # v1.3 task fail: task-layer unsolvable; channel is blameless.
            ep["task_fail_count"] += 1
            self._log(pool, "task_fail", endpoint=endpoint)
        elif reason == "compliance":
            # v1.3 compliance fail: prohibited by compliance; channel is
            # blameless and the target (if given) is frozen pool-wide.
            ep["compliance_count"] += 1
            self._log(pool, "compliance_fail", endpoint=endpoint,
                      target=target)
            if target:
                frozen = st.setdefault("frozen_targets", [])
                if target not in frozen:
                    frozen.append(target)
                    self._log(pool, "frozen_target", endpoint=endpoint,
                              target=target)
        else:
            ep["trail"] *= FAIL_PUNISH
            ep["fail_count"] += 1
            if dormant_before:
                # canary probe failed: stay dormant, streak reset
                ep["below_streak"] = 0
        ep["reports"] += 1

        # ---- pool-wide decay (frozen once on common-cause) ----
        if not frozen_now:
            for v in eps.values():
                v["trail"] *= decay
                tbp = v.get("trail_by_prov")
                if tbp:
                    for p_ in PROVS:
                        tbp[p_] = tbp.get(p_, 0.0) * decay

        # ---- dormancy judgement (S1-S5 v2 + Amendment B) ----
        shares = self._shares(st, active_only=True)
        n_active = sum(1 for v in eps.values() if v["status"] == "active")
        for name, v in eps.items():
            if v["status"] != "active":
                continue
            thr = DORM_SHARE_AMEND_B if self._fail_rate(v) > FAIL_RATE_AMEND_B \
                else DORM_SHARE
            share = shares.get(name, 0.0)
            if share < thr:
                v["below_streak"] += 1
            else:
                v["below_streak"] = 0
            if v["below_streak"] >= DORM_STREAK and n_active > 2:
                v["status"] = "dormant"
                n_active -= 1
                self._log(pool, "dormancy", endpoint=name,
                          share=share, fail_rate=self._fail_rate(v),
                          streak=v["below_streak"])

        self._save(pool, st)
        # v1.5 bus-direct: publish the report event to <pool>.events if a
        # bus socket is configured; failure degrades silently (the file
        # event log above is the fallback) and never blocks the report.
        self._bus_publish(pool, {"event": "report", "pool": pool,
                                 "endpoint": endpoint, "ok": bool(ok),
                                 "prov": prov, "reason": reason,
                                 "target": target, "ts": now})
        return st

    # ---------- v1.5 bus-direct publish ----------
    _bus_mod = None
    _bus_tried = False

    def _bus_publish(self, pool, payload):
        sock = os.environ.get("SLIME_BUS_SOCK")
        if not sock or not os.path.exists(sock):
            return False
        try:
            if not Router._bus_tried:
                Router._bus_tried = True
                try:
                    import slime_bus as _m
                    Router._bus_mod = _m
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "slime_bus", BUS_CLIENT_PATH)
                    _m = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(_m)
                    Router._bus_mod = _m
            if Router._bus_mod is None:
                return False
            Router._bus_mod.publish(sock, "%s.events" % pool, payload)
            return True
        except Exception:
            return False

    # ---------- v1.5 snapshot / rollback ----------
    def snapshot(self, pool):
        """Copy the full state to state/<pool>.snap.<ts>.json."""
        st = self._load(pool)
        self._save(pool, st)  # persist pending backfills before copying
        ts = int(self.now_fn())
        snap = os.path.join(self.state_dir, "%s.snap.%d.json" % (pool, ts))
        n = 0
        while os.path.exists(snap):  # same-second collision guard
            n += 1
            snap = os.path.join(self.state_dir,
                                "%s.snap.%d.%d.json" % (pool, ts, n))
        with open(self._path(pool), "rb") as f:
            data = f.read()
        tmp = snap + ".tmp.%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, snap)
        self._log(pool, "snapshot", snapfile=os.path.basename(snap))
        return snap

    def rollback(self, pool, snapfile):
        """Restore state from a snapshot file and log a rollback event."""
        if not os.path.exists(snapfile):
            raise FileNotFoundError("snapshot not found: %s" % snapfile)
        with open(snapfile, "r", encoding="utf-8") as f:
            st = json.load(f)
        st = self._backfill(st)
        st["pool"] = pool
        self._log(pool, "rollback", snapfile=os.path.basename(snapfile))
        self._save(pool, st)
        return st

    # ---------- unfreeze (v1.4 manual adjudication) ----------
    def unfreeze(self, pool, target):
        """Remove target from pool-level frozen_targets (human adjudication).

        Returns True and logs an "unfrozen" event (source=manual) on success;
        returns False without any disk write if the target is not frozen.
        """
        st = self._load(pool)
        frozen = st.setdefault("frozen_targets", [])
        if target not in frozen:
            return False
        frozen.remove(target)
        self._log(pool, "unfrozen", target=target, source="manual")
        self._save(pool, st)
        return True

    # ---------- heartbeat (cluster liveness lease) ----------
    def heartbeat(self, pool, cluster_id):
        hb = {"cluster_id": cluster_id, "ts": self.now_fn(),
              "ttl": HEARTBEAT_TTL}
        p = self._heartbeat_path(pool)
        clusters = {}
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    clusters = json.load(f).get("clusters", {})
            except (ValueError, OSError):
                clusters = {}
        clusters[cluster_id] = hb
        tmp = p + ".tmp.%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"pool": pool, "clusters": clusters}, f,
                      indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        return hb

    def _cluster_status(self, pool):
        now = self.now_fn()
        out = {}
        p = self._heartbeat_path(pool)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    clusters = json.load(f).get("clusters", {})
            except (ValueError, OSError):
                clusters = {}
            for cid, hb in sorted(clusters.items()):
                ttl = hb.get("ttl", HEARTBEAT_TTL)
                age = now - hb.get("ts", 0.0)
                out[cid] = {"age_seconds": age,
                            "ttl": ttl,
                            "liveness": "dead" if age > ttl else "alive"}
        return out

    # ---------- status ----------
    def status(self, pool):
        st = self._load(pool)
        eps = st["endpoints"]
        shares_all = self._shares(st, active_only=False)
        out_eps = {}
        for name, v in sorted(eps.items()):
            fr = self._fail_rate(v)
            out_eps[name] = {
                "trail": v["trail"],
                "share": shares_all.get(name, 0.0),
                "status": v["status"],
                "fail_rate": fr,  # == fail_rate_channel (kept for compat)
                "fail_rate_channel": fr,
                "task_fail_count": v.get("task_fail_count", 0),
                "compliance_count": v.get("compliance_count", 0),
                "cost": v["cost"],
                "platform": v["platform"],
                "ok_count": v["ok_count"],
                "fail_count": v["fail_count"],
                # Amendment A: cost-awareness enters dormancy only,
                # efficiency score = trail / cost
                "efficiency": (v["trail"] / v["cost"]) if v["cost"] else None,
                # v1.5 provenance books, listed separately
                "trail_by_prov": {p_: v.get("trail_by_prov", {}).get(p_, 0.0)
                                  for p_ in PROVS},
                "events": self._event_counts(pool, name),
            }
        ts_written = st.get("ts_written")
        ttl = st.get("ttl_seconds", TTL_SECONDS_DEFAULT)
        age = (self.now_fn() - ts_written) if ts_written is not None else None
        # v1.5: low_real when no real-book data exists anywhere (select
        # then degrades to the total book); herd_risk from recent selects.
        low_real = all(v.get("trail_by_prov", {}).get("real", 0.0) <= 0.0
                       for v in eps.values())
        recent = st.get("recent_selects", [])[-HERD_WINDOW:]
        herd_risk = bool(recent) and any(
            recent.count(k) / float(len(recent)) > HERD_THRESHOLD
            for k in set(recent))
        return {"pool": pool,
                "common_cause_frozen": CCFrozen(
                    _norm_frozen(st.get("common_cause_frozen"))),
                "low_real": low_real,
                "herd_risk": herd_risk,
                "ts_written": ts_written,
                "ttl_seconds": ttl,
                "age_seconds": age,
                "stale": (age is None) or (age > ttl),
                "protocol": st.get("protocol", dict(PROTOCOL)),
                "clusters": self._cluster_status(pool),
                "frozen_targets": list(st.get("frozen_targets", [])),
                "endpoints": out_eps}

    def _event_counts(self, pool, endpoint=None):
        counts = {}
        p = self._events_path(pool)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if endpoint is None or rec.get("endpoint") == endpoint \
                            or rec["event"] in ("common_cause",
                                                "common_cause_cleared"):
                        counts[rec["event"]] = counts.get(rec["event"], 0) + 1
        return counts


# ---------- CLI ----------
def main(argv=None):
    ap = argparse.ArgumentParser(prog="slime_router",
                                 description="K3 slime v1.2 trail-weighted router")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register")
    p.add_argument("pool"); p.add_argument("endpoint")
    p.add_argument("--cost", type=float, default=1.0)
    p.add_argument("--platform", default="default")

    p = sub.add_parser("select")
    p.add_argument("pool")
    p.add_argument("--eta", type=float, default=ETA_DEFAULT)

    p = sub.add_parser("report")
    p.add_argument("pool"); p.add_argument("endpoint")
    p.add_argument("result", choices=["ok", "fail"])
    p.add_argument("--latency_ms", type=float, default=None)
    p.add_argument("--cost_units", type=float, default=None)
    p.add_argument("--decay", type=float, default=DECAY_DEFAULT)
    p.add_argument("--reason", choices=FAIL_REASONS, default="channel")
    p.add_argument("--target", default=None)
    p.add_argument("--prov", choices=PROVS, default="real")
    p.add_argument("--quality", type=float, default=None)
    p.add_argument("--quality-src", choices=QUALITY_SRCS, default=None)

    p = sub.add_parser("snapshot")
    p.add_argument("pool")

    p = sub.add_parser("rollback")
    p.add_argument("pool")
    p.add_argument("--to", required=True, help="snapshot file to restore")

    p = sub.add_parser("unfreeze")
    p.add_argument("pool")
    p.add_argument("--target", required=True)

    p = sub.add_parser("status")
    p.add_argument("pool")

    p = sub.add_parser("heartbeat")
    p.add_argument("pool")
    p.add_argument("--cluster", required=True)

    args = ap.parse_args(argv)
    r = Router()
    if args.cmd == "register":
        r.register(args.pool, args.endpoint, cost=args.cost,
                   platform=args.platform)
        print("registered %s -> %s" % (args.endpoint, args.pool))
    elif args.cmd == "select":
        ep = r.select(args.pool, eta=args.eta)
        if ep is None:
            print("no active endpoints", file=sys.stderr)
            return 1
        print(ep)
    elif args.cmd == "report":
        r.report(args.pool, args.endpoint, args.result == "ok",
                 latency_ms=args.latency_ms, cost_units=args.cost_units,
                 decay=args.decay, reason=args.reason, target=args.target,
                 prov=args.prov, quality=args.quality,
                 quality_src=args.quality_src)
        print("reported")
    elif args.cmd == "snapshot":
        print(r.snapshot(args.pool))
    elif args.cmd == "rollback":
        r.rollback(args.pool, args.to)
        print("rolled back %s <- %s" % (args.pool, args.to))
    elif args.cmd == "heartbeat":
        r.heartbeat(args.pool, args.cluster)
        print("heartbeat %s -> %s" % (args.cluster, args.pool))
    elif args.cmd == "unfreeze":
        if not r.unfreeze(args.pool, args.target):
            print("target not frozen in pool %s: %s"
                  % (args.pool, args.target), file=sys.stderr)
            return 1
        print("unfrozen %s in %s" % (args.target, args.pool))
    elif args.cmd == "status":
        out = r.status(args.pool)
        # CCFrozen is a dict subclass; the json C encoder skips subclass
        # contents when indent is used -- serialise it as a plain dict.
        out["common_cause_frozen"] = dict(out["common_cause_frozen"])
        print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
