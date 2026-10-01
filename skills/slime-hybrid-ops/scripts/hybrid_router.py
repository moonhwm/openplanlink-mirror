#!/usr/bin/env python3
"""hybrid_router.py -- slime_router v1.6p2 core + optional hybrid mechanisms.

Routing core (identical to the BASE variant of hybrid_bench.py, itself a
faithful simplification of slime_router v1.6p2 select/report semantics):
  select : trail^ETA (ETA=2.0) weighted random over ACTIVE endpoints; with
           probability z (=0.03) exploration branch draws uniformly from
           active+dormant (dormant pick = canary probe).
  report ok   : trail += 1.0 ; dormant ok -> revival (trail = 0.1 *
                mean(active trails), status -> active).
  report fail : trail *= 0.5, fail_count += 1 (channel-class).
  after every report: pool-wide trail *= 0.97.
  dormancy: active endpoint whose trail share (active pool) stays < 5% for
            10 consecutive reports goes dormant.

Optional switches (sticky: once passed on any select/report call for a pool
they are persisted into the pool state and apply to later calls):
  --typed-decay   H1: per-endpoint decay by fail rate over its last 20
                  reports: fr<0.10 -> half-life 400, fr<0.25 -> 100,
                  else 25; multiplier per report = 0.5**(1/half_life).
  --adaptive-z    H2: z = clip(0.03*(1 + 2*pool_fail_rate_last20
                  + herd_excess), 0.03, 0.25),
                  herd_excess = max(0, max share in last 20 selects - 0.6).
  --levy-jump     H4: inside the exploration branch, 20% of the time pick
                  the endpoint with the fewest historical reports
                  (active+dormant; ties uniform) instead of uniform.

Rollback guarantee: with no switches ever enabled, select/report behaviour
is exactly the BASE semantics above (same constants, same order of ops).

Subcommands (CLI-compatible with slime_router.py for these verbs):
  register <pool> <endpoint> [--cost C] [--platform P]
  select    <pool> [--eta ETA] [--typed-decay] [--adaptive-z] [--levy-jump]
  report    <pool> <endpoint> <ok|fail> [--decay D] [switches...]
  status    <pool>
State: state/<pool>.json (atomic tmp+replace, .bak fallback);
       events: state/<pool>.events.jsonl (append-only).
Stdlib only, single file, no network.
"""

import argparse
import json
import os
import random
import sys
import time

# ---- core constants (slime_router v1.6p2) ----
ETA_DEFAULT = 2.0
Z_EXPLORE = 0.03
DECAY_DEFAULT = 0.97
DEP_BASE = 1.0
FAIL_PUNISH = 0.5
DORM_STREAK = 10
DORM_SHARE = 0.05
CANARY_REVIVE_TRAIL_RATIO = 0.1

# ---- hybrid constants ----
TYPED_WINDOW = 20
TYPED_BINS = ((0.10, 400.0), (0.25, 100.0), (1.01, 25.0))
ADAPT_WINDOW = 20
ADAPT_MIN, ADAPT_MAX = 0.03, 0.25
HERD_THRESHOLD = 0.6
LEVY_P = 0.2

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")

FEATURES = ("typed_decay", "adaptive_z", "levy_jump")


def _now():
    return time.time()


def _typed_multiplier(last):
    """last: list of bool ok outcomes (oldest..newest, <= TYPED_WINDOW)."""
    fr = (sum(1 for ok in last if not ok) / float(len(last))) if last else 0.0
    for upper, half_life in TYPED_BINS:
        if fr < upper:
            return 0.5 ** (1.0 / half_life)
    return 0.5 ** (1.0 / TYPED_BINS[-1][1])


class Router(object):
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

    @staticmethod
    def _default_state(pool):
        return {"pool": pool, "endpoints": {},
                "recent_selects": [], "recent_outcomes": [],
                "features": {k: False for k in FEATURES}}

    @staticmethod
    def _backfill(st):
        st.setdefault("recent_selects", [])
        st.setdefault("recent_outcomes", [])
        feats = st.setdefault("features", {})
        for k in FEATURES:
            feats.setdefault(k, False)
        for v in st.get("endpoints", {}).values():
            v.setdefault("ok_count", 0)
            v.setdefault("fail_count", 0)
            v.setdefault("below_streak", 0)
            v.setdefault("reports", 0)
            v.setdefault("last_outcomes", [])
        return st

    def _load(self, pool):
        p = self._path(pool)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return self._backfill(json.load(f))
            except (ValueError, OSError):
                bak = p + ".bak"
                if os.path.exists(bak):
                    with open(bak, "r", encoding="utf-8") as f:
                        return self._backfill(json.load(f))
                raise
        return self._backfill(self._default_state(pool))

    def _save(self, pool, st):
        p = self._path(pool)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    old = f.read()
                with open(p + ".bak", "w", encoding="utf-8") as f:
                    f.write(old)
            except OSError:
                pass
        tmp = p + ".tmp.%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)

    def _log(self, pool, event, **kw):
        rec = {"ts": self.now_fn(), "event": event}
        rec.update(kw)
        with open(self._events_path(pool), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    # ---------- helpers ----------
    def _apply_feature_flags(self, st, args):
        changed = False
        for k in FEATURES:
            if getattr(args, k, False) and not st["features"].get(k):
                st["features"][k] = True
                changed = True
        return changed

    # ---------- register ----------
    def register(self, pool, endpoint, cost=1.0, platform="default"):
        st = self._load(pool)
        eps = st["endpoints"]
        if endpoint not in eps:
            eps[endpoint] = {"trail": 1.0, "cost": float(cost),
                             "platform": platform, "status": "active",
                             "ok_count": 0, "fail_count": 0,
                             "below_streak": 0, "reports": 0,
                             "last_outcomes": []}
            self._log(pool, "register", endpoint=endpoint, cost=cost,
                      platform=platform)
        else:
            eps[endpoint]["cost"] = float(cost)
            eps[endpoint]["platform"] = platform
        self._save(pool, st)
        return eps[endpoint]

    # ---------- select ----------
    def _z(self, st):
        if not st["features"].get("adaptive_z"):
            return Z_EXPLORE
        out = st["recent_outcomes"][-ADAPT_WINDOW:]
        fr = (sum(1 for ok in out if not ok) / float(len(out))) if out else 0.0
        herd_excess = 0.0
        recent = st["recent_selects"][-ADAPT_WINDOW:]
        if recent:
            top = max(recent.count(k) for k in set(recent)) / float(len(recent))
            herd_excess = max(0.0, top - HERD_THRESHOLD)
        return min(ADAPT_MAX, max(ADAPT_MIN,
                                  Z_EXPLORE * (1.0 + 2.0 * fr + herd_excess)))

    def select(self, pool, eta=ETA_DEFAULT, args=None):
        st = self._load(pool)
        if args is not None:
            self._apply_feature_flags(st, args)
        eps = st["endpoints"]
        active = [k for k, v in eps.items() if v["status"] == "active"]
        dormant = [k for k, v in eps.items() if v["status"] == "dormant"]
        if not active and not dormant:
            self._save(pool, st)
            return None
        if not active:
            choice = self.rng.choice(dormant)
        elif self.rng.random() < self._z(st):
            exp_pool = active + dormant
            if st["features"].get("levy_jump") and self.rng.random() < LEVY_P:
                least = min(eps[k]["reports"] for k in exp_pool)
                ties = [k for k in exp_pool if eps[k]["reports"] == least]
                choice = self.rng.choice(ties)
                self._log(pool, "levy_jump", endpoint=choice,
                          reports=eps[choice]["reports"])
            else:
                choice = self.rng.choice(exp_pool)
            if eps[choice]["status"] == "dormant":
                self._log(pool, "canary", endpoint=choice,
                          active=len(active), dormant=len(dormant))
        else:
            weights = [max(eps[k]["trail"], 0.0) ** eta for k in active]
            tot = sum(weights)
            if tot <= 0.0:
                choice = self.rng.choice(active)
            else:
                r = self.rng.random() * tot
                acc = 0.0
                choice = active[-1]
                for k, w in zip(active, weights):
                    acc += w
                    if r <= acc:
                        choice = k
                        break
        recent = st.setdefault("recent_selects", [])
        recent.append(choice)
        del recent[:-ADAPT_WINDOW]
        self._save(pool, st)
        return choice

    # ---------- report ----------
    def report(self, pool, endpoint, ok, decay=DECAY_DEFAULT, args=None):
        st = self._load(pool)
        if args is not None:
            self._apply_feature_flags(st, args)
        eps = st["endpoints"]
        if endpoint not in eps:
            self.register(pool, endpoint)
            st = self._load(pool)
            if args is not None:
                self._apply_feature_flags(st, args)
            eps = st["endpoints"]
        ep = eps[endpoint]
        ep["reports"] += 1
        last = ep.setdefault("last_outcomes", [])
        last.append(bool(ok))
        del last[:-TYPED_WINDOW]
        out = st.setdefault("recent_outcomes", [])
        out.append(bool(ok))
        del out[:-ADAPT_WINDOW]

        dormant_before = ep["status"] == "dormant"
        if ok:
            if dormant_before:
                act = [v for k, v in eps.items()
                       if k != endpoint and v["status"] == "active"]
                mean_active = (sum(max(v["trail"], 0.0) for v in act)
                               / len(act)) if act else DEP_BASE
                ep["trail"] = CANARY_REVIVE_TRAIL_RATIO * mean_active
                ep["status"] = "active"
                ep["below_streak"] = 0
                self._log(pool, "revival", endpoint=endpoint,
                          trail=ep["trail"], mean_active_trail=mean_active)
            else:
                ep["trail"] += DEP_BASE
            ep["ok_count"] += 1
        else:
            ep["trail"] *= FAIL_PUNISH
            ep["fail_count"] += 1
            if dormant_before:
                ep["below_streak"] = 0

        # pool-wide decay: uniform (BASE) or typed half-life (H1)
        if st["features"].get("typed_decay"):
            for v in eps.values():
                v["trail"] *= _typed_multiplier(v.get("last_outcomes", []))
        else:
            for v in eps.values():
                v["trail"] *= decay

        # dormancy judgement (shares over active pool)
        act = {k: v for k, v in eps.items() if v["status"] == "active"}
        tot = sum(max(v["trail"], 0.0) for v in act.values())
        for name, v in act.items():
            share = (max(v["trail"], 0.0) / tot) if tot > 0 else 0.0
            if share < DORM_SHARE:
                v["below_streak"] += 1
            else:
                v["below_streak"] = 0
            if v["below_streak"] >= DORM_STREAK:
                v["status"] = "dormant"
                self._log(pool, "dormancy", endpoint=name, share=share,
                          streak=v["below_streak"])

        self._save(pool, st)
        return st

    # ---------- status ----------
    def status(self, pool):
        st = self._load(pool)
        eps = st["endpoints"]
        tot = sum(max(v["trail"], 0.0) for v in eps.values())
        out_eps = {}
        for name, v in sorted(eps.items()):
            n = v["ok_count"] + v["fail_count"]
            out_eps[name] = {
                "trail": v["trail"],
                "share": (max(v["trail"], 0.0) / tot) if tot > 0 else 0.0,
                "status": v["status"],
                "fail_rate": (v["fail_count"] / n) if n else 0.0,
                "cost": v["cost"],
                "platform": v["platform"],
                "ok_count": v["ok_count"],
                "fail_count": v["fail_count"],
                "reports": v["reports"],
            }
        return {"pool": pool,
                "features": dict(st.get("features", {})),
                "endpoints": out_eps}


# ---------- CLI ----------
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="hybrid_router",
        description="slime_router v1.6p2 core + optional hybrid switches")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register")
    p.add_argument("pool"); p.add_argument("endpoint")
    p.add_argument("--cost", type=float, default=1.0)
    p.add_argument("--platform", default="default")

    def add_switches(p_):
        p_.add_argument("--typed-decay", dest="typed_decay",
                        action="store_true",
                        help="H1 per-endpoint half-life decay (sticky)")
        p_.add_argument("--adaptive-z", dest="adaptive_z",
                        action="store_true",
                        help="H2 adaptive exploration floor (sticky)")
        p_.add_argument("--levy-jump", dest="levy_jump",
                        action="store_true",
                        help="H4 least-reports long-jump exploration (sticky)")

    p = sub.add_parser("select")
    p.add_argument("pool")
    p.add_argument("--eta", type=float, default=ETA_DEFAULT)
    add_switches(p)

    p = sub.add_parser("report")
    p.add_argument("pool"); p.add_argument("endpoint")
    p.add_argument("result", choices=["ok", "fail"])
    p.add_argument("--decay", type=float, default=DECAY_DEFAULT)
    add_switches(p)

    p = sub.add_parser("status")
    p.add_argument("pool")

    args = ap.parse_args(argv)
    r = Router()
    if args.cmd == "register":
        r.register(args.pool, args.endpoint, cost=args.cost,
                   platform=args.platform)
        print("registered %s -> %s" % (args.endpoint, args.pool))
    elif args.cmd == "select":
        ep = r.select(args.pool, eta=args.eta, args=args)
        if ep is None:
            print("no endpoints", file=sys.stderr)
            return 1
        print(ep)
    elif args.cmd == "report":
        r.report(args.pool, args.endpoint, args.result == "ok",
                 decay=args.decay, args=args)
        print("reported")
    elif args.cmd == "status":
        print(json.dumps(r.status(args.pool), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
