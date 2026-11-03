#!/usr/bin/env python3
"""Suno music via the 302.ai gateway: submit -> poll -> download mp3.

Security / honesty contract:
  * API key comes ONLY from the S302_API_KEY environment variable; it is never
    printed, logged, or embedded anywhere.
  * A live call costs real quota (~0.1 PTC per submission, 2 songs per call).
    ALWAYS run --dry-run first to inspect payloads.
  * This client has been DRY-RUN TESTED ONLY against documented shapes; the exact
    /suno/fetch parameter contract may vary, so polling tries POST then GET and
    reports what it saw. Treat first live use as a probe.
  * After download, prints the file's SHA3-256 for manifest sealing.

Usage:
  suno_music.py --prompt "lofi piano, moonlit night" --tags "ambient" \
                --mv chirp-crow --title "Moonlit" --instrumental \
                --out bgm.mp3 [--base https://api.302.ai]
  suno_music.py --dry-run --prompt "..."        # no network, no quota
  suno_music.py --status <task_id> [--out bgm.mp3]
"""
import argparse, hashlib, json, os, sys, time, urllib.request, urllib.error

BASES = {"global": "https://api.302.ai", "cn": "https://api.302ai.cn"}
POLL_INTERVAL_S = 15
POLL_TIMEOUT_S = 20 * 60


def sha3_256_file(path):
    h = hashlib.sha3_256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def key():
    k = os.environ.get("S302_API_KEY", "").strip()
    if not k:
        sys.exit("S302_API_KEY env var is not set; export it first (never hardcode).")
    return k


def req(method, url, payload, redact_key):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + redact_key)
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def submit(base, args, k):
    payload = {"prompt": args.prompt, "tags": args.tags or "", "mv": args.mv,
               "title": args.title or "", "make_instrumental": bool(args.instrumental)}
    if args.dry_run:
        print("[dry-run] POST", base + "/suno/submit/music")
        print("[dry-run] payload:", json.dumps(payload, ensure_ascii=False))
        print("[dry-run] auth: Bearer sk-***redacted*** (key present: %s)" % bool(k))
        return None
    out = req("POST", base + "/suno/submit/music", payload, k)
    print("submit response:", json.dumps(out, ensure_ascii=False)[:800])
    tid = out.get("task_id") or out.get("data", {}).get("task_id") or out.get("id")
    if not tid:
        sys.exit("could not find task_id in submit response; record the raw shape above")
    return tid


def poll(base, tid, args, k):
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        for method, url, payload in (
            ("POST", base + "/suno/fetch", {"task_id": tid}),
            ("GET", base + "/suno/fetch?task_id=" + tid, None),
        ):
            try:
                st = req(method, url, payload, k)
                break
            except urllib.error.HTTPError as e:
                print("poll attempt failed (%s %s): HTTP %s" % (method, url, e.code))
                st = None
        if st is None:
            time.sleep(POLL_INTERVAL_S)
            continue
        blob = json.dumps(st, ensure_ascii=False)
        status = st.get("status") or st.get("data", {}).get("status") or ""
        print("poll: status=%s" % status)
        if status == "SUCCESS" or "audio_url" in blob:
            urls = []
            for item in st.get("data", []) if isinstance(st.get("data"), list) else [st.get("data", st)]:
                if isinstance(item, dict) and item.get("audio_url"):
                    urls.append(item["audio_url"])
            return urls
        time.sleep(POLL_INTERVAL_S)
    sys.exit("poll timed out after %ds" % POLL_TIMEOUT_S)


def download(url, out):
    urllib.request.urlretrieve(url, out)
    fp = sha3_256_file(out)
    print("saved:", out)
    print("sha3-256:", fp)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--prompt"); p.add_argument("--tags"); p.add_argument("--title")
    p.add_argument("--mv", default="chirp-crow", help="model generation, e.g. chirp-crow (v5)")
    p.add_argument("--instrumental", action="store_true")
    p.add_argument("--out", default="suno_out.mp3")
    p.add_argument("--base", choices=list(BASES), default="global")
    p.add_argument("--status", metavar="TASK_ID", help="poll an existing task only")
    p.add_argument("--dry-run", action="store_true", help="print payloads, no network")
    args = p.parse_args()
    base = BASES[args.base]
    k = key() if not args.dry_run else os.environ.get("S302_API_KEY", "")
    tid = args.status or submit(base, args, k)
    if args.dry_run:
        print("[dry-run] would then poll /suno/fetch and download audio_url ->", args.out)
        return
    if not args.status:
        print("task_id:", tid)
    urls = poll(base, tid, args, k)
    if not urls:
        sys.exit("task SUCCESS but no audio_url found; inspect raw responses above")
    download(urls[0], args.out)
    if len(urls) > 1:
        print("note: %d tracks returned; downloaded the first. Remaining: %s" % (len(urls), urls[1:]))


if __name__ == "__main__":
    main()
