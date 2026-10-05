"""Let the official Codex CLI handle Supabase OAuth; never surface auth URLs/tokens."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tomllib

from connect_wps_supabase_ima import CODEX, PS, SUPABASE_URL, protect

BJT = timezone(timedelta(hours=8))


def monitored(command, deadline_seconds=600):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    messages = queue.Queue()
    def read(stream):
        for line in stream:
            messages.put(line)
    readers = [threading.Thread(target=read, args=(stream,), daemon=True)
               for stream in (process.stdout, process.stderr)]
    for reader in readers:
        reader.start()
    states = set()
    deadline = time.monotonic() + deadline_seconds
    timed_out = False
    while process.poll() is None or not messages.empty():
        if time.monotonic() > deadline:
            timed_out = True
            process.terminate()
            break
        try:
            line = messages.get(timeout=0.2)
        except queue.Empty:
            continue
        lowered = line.lower()
        state = None
        if "added" in lowered and "mcp" in lowered:
            state = "configuration_registered"
        elif "successfully logged in" in lowered or "successfully authenticated" in lowered:
            state = "oauth_success_reported_by_codex"
        elif "authorize" in lowered or "authorization" in lowered or "opening" in lowered and "browser" in lowered:
            state = "oauth_browser_authorization_pending"
        elif "no oauth support" in lowered:
            state = "oauth_unsupported"
        elif "timed out" in lowered:
            state = "provider_timeout"
        if state and state not in states:
            states.add(state)
            print(json.dumps({"state": state, "raw_cli_output_suppressed": True}), flush=True)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    for reader in readers:
        reader.join(timeout=1)
    return {"exit": process.returncode, "timed_out": timed_out, "observed_states": sorted(states)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--receipt-name")
    args = parser.parse_args()
    run = args.run
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = config.read_bytes()
    parsed_before = tomllib.loads(before.decode("utf-8-sig"))
    existing = parsed_before.get("mcp_servers", {}).get("supabase-readonly")
    if existing and existing.get("url") != SUPABASE_URL:
        raise RuntimeError("Existing Supabase server retained because endpoint differs")
    commands = []
    if not existing:
        private = run / "config_backup_private"
        private.mkdir(exist_ok=True)
        with (private / "codex-config-before-supabase.toml.dpapi").open("xb") as handle:
            handle.write(protect(before))
        print(json.dumps({"state": "supabase_official_connection_setup_started", "read_only": True}), flush=True)
        commands.append(monitored([str(PS), "-NoProfile", "-File", str(CODEX), "mcp", "add",
                                   "supabase-readonly", "--url", SUPABASE_URL]))
    if args.login:
        native = Path.home() / "AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
        if not native.is_file():
            raise RuntimeError("Verified native Codex CLI is unavailable")
        version = subprocess.run([str(native), "--version"], capture_output=True, timeout=10)
        if version.returncode or version.stdout.decode("utf-8", "replace").strip() != "codex-cli 0.160.0":
            raise RuntimeError("Native Codex version differs from inspected protocol")
        print(json.dumps({"state": "official_oauth_flow_started", "raw_cli_output_suppressed": True}), flush=True)
        commands.append(monitored([str(native), "mcp", "login", "supabase-readonly"]))
    parsed_after = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    registered = parsed_after.get("mcp_servers", {}).get("supabase-readonly", {}).get("url") == SUPABASE_URL
    compare = json.loads(json.dumps(parsed_after))
    if not existing:
        compare.get("mcp_servers", {}).pop("supabase-readonly", None)
    for name, entry in parsed_before.get("mcp_servers", {}).items():
        if entry.get("args") == [] and "args" not in compare.get("mcp_servers", {}).get(name, {}):
            entry.pop("args")
    receipt = {"checked_at_bjt": datetime.now(BJT).isoformat(), "server": "supabase-readonly",
               "endpoint": SUPABASE_URL, "configured": registered,
               "unrelated_config_preserved": compare == parsed_before,
               "commands": commands, "oauth_success_reported": any(
                   "oauth_success_reported_by_codex" in item["observed_states"] for item in commands),
               "database_read_verified": False, "auth_urls_or_tokens_saved": False,
               "raw_cli_output_saved": False}
    receipt_name = args.receipt_name or ("supabase_oauth_login.json" if args.login else "supabase_oauth_setup.json")
    if Path(receipt_name).name != receipt_name:
        raise RuntimeError("Receipt must be a file name")
    with (run / receipt_name).open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "raw_error_suppressed": True}), flush=True)
        raise SystemExit(1)
