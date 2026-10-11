"""Configure the official read-only Neon MCP and delegate OAuth to Codex."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import tomllib

from connect_wps_supabase_ima import BJT, protect
from supabase_oauth_connect import monitored

SERVER = "neon-readonly"
ENDPOINT = "https://mcp.neon.tech/mcp?readonly=true&category=projects&category=branches&category=schema&category=querying"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--receipt-name", default="neon_oauth_setup.json")
    args = parser.parse_args()
    if Path(args.receipt_name).name != args.receipt_name:
        raise RuntimeError("Receipt must be a file name")
    args.run.mkdir(parents=True, exist_ok=True)
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = config.read_bytes()
    baseline = tomllib.loads(before.decode("utf-8-sig"))
    existing = baseline.get("mcp_servers", {}).get(SERVER)
    if existing and existing.get("url") != ENDPOINT:
        raise RuntimeError("Existing Neon configuration retained because endpoint differs")
    native = Path.home() / "AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
    version = subprocess.run([str(native), "--version"], capture_output=True, timeout=10)
    if version.returncode or version.stdout.decode("utf-8", "replace").strip() != "codex-cli 0.160.0":
        raise RuntimeError("Inspected Codex runtime version differs")
    commands = []
    if not existing:
        private = args.run / "config_backup_private"
        private.mkdir(exist_ok=True)
        with (private / "codex-config-before-neon.toml.dpapi").open("xb") as out:
            out.write(protect(before))
        commands.append(monitored([str(native), "mcp", "add", SERVER, "--url", ENDPOINT], 30))
    after = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    registered = after.get("mcp_servers", {}).get(SERVER, {}).get("url") == ENDPOINT
    compare = json.loads(json.dumps(after))
    if not existing:
        compare.get("mcp_servers", {}).pop(SERVER, None)
    for name, entry in baseline.get("mcp_servers", {}).items():
        if entry.get("args") == [] and "args" not in compare.get("mcp_servers", {}).get(name, {}):
            entry.pop("args")
    unchanged = compare == baseline
    if not registered or not unchanged:
        raise RuntimeError("Neon registration could not be verified")
    if args.login:
        print(json.dumps({"state": "neon_official_oauth_started", "server": SERVER,
                          "raw_cli_output_suppressed": True}), flush=True)
        commands.append(monitored([str(native), "mcp", "login", SERVER], 600))
    receipt = {"checked_at_bjt": datetime.now(BJT).isoformat(), "server": SERVER,
               "endpoint": ENDPOINT, "configured": registered,
               "unrelated_config_preserved": unchanged, "read_only": True,
               "commands": commands,
               "oauth_success_reported": any("oauth_success_reported_by_codex" in c["observed_states"] for c in commands),
               "project_read_verified": False, "auth_urls_or_tokens_saved": False}
    with (args.run / args.receipt_name).open("x", encoding="utf-8") as out:
        json.dump(receipt, out, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error_type": type(error).__name__, "raw_error_suppressed": True}), flush=True)
        raise SystemExit(1)
