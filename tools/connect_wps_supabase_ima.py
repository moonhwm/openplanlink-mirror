"""Bounded integration probes. Credentials and raw provider responses stay private."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone, timedelta
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import queue
import subprocess
import sys
import threading
import time
import tomllib
import urllib.request
from zipfile import ZipFile

BJT = timezone(timedelta(hours=8))
WPS = Path.home() / ".local/bin/wps365-cli.exe"
CODEX = Path.home() / "AppData/Roaming/npm/codex.ps1"
PS = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
IMA_PACKAGE = "https://app-dl.ima.qq.com/skills/ima-skills-1.1.10.zip"
SUPABASE_URL = "https://mcp.supabase.com/mcp?read_only=true&features=account,database,docs"


def save(run: Path, name: str, value: dict) -> None:
    with (run / name).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def protect(data: bytes, description: str = "OpenPlanLink MCP config backup",
            entropy: bytes = b"OpenPlanLink MCP config backup v1") -> bytes:
    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR,
                                      ctypes.POINTER(Blob), ctypes.c_void_p,
                                      ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt.CryptProtectData.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    source_buffer = ctypes.create_string_buffer(data)
    entropy_buffer = ctypes.create_string_buffer(entropy)
    source = Blob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    extra = Blob(len(entropy), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    if not crypt.CryptProtectData(ctypes.byref(source), description,
                                  ctypes.byref(extra), None, None, 1, ctypes.byref(result)):
        raise RuntimeError("Current-user config backup failed")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.memset(result.pbData, 0, result.cbData)
        kernel.LocalFree(result.pbData)


def configure_wps(run: Path) -> dict:
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = config.read_bytes() if config.exists() else b""
    parsed = tomllib.loads(before.decode("utf-8-sig")) if before else {}
    expected = {"command": str(WPS), "args": ["mcp", "serve", "--domains", "airpage,drive,user"]}
    existing = parsed.get("mcp_servers", {}).get("wps365")
    if existing is not None:
        if existing.get("command") != expected["command"] or existing.get("args") != expected["args"]:
            raise RuntimeError("An existing WPS MCP configuration differs; retained")
        changed = False
    else:
        private = run / "config_backup_private"
        private.mkdir(exist_ok=False)
        (private / "codex-config.toml.dpapi").write_bytes(protect(before))
        if config.exists() and config.read_bytes() != before:
            raise RuntimeError("Codex configuration changed before registration")
        result = subprocess.run([str(PS), "-NoProfile", "-File", str(CODEX), "mcp", "add",
                                 "wps365", "--", str(WPS), *expected["args"]],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode:
            raise RuntimeError("Codex WPS registration failed; command output suppressed")
        after = tomllib.loads(config.read_text(encoding="utf-8-sig"))
        registered = after.get("mcp_servers", {}).get("wps365", {})
        if registered.get("command") != expected["command"] or registered.get("args") != expected["args"]:
            raise RuntimeError("Registered WPS command differs")
        changed = True
    original_backup = run / "config_backup_private" / "codex-config.toml.dpapi"
    normalized_empty_args = []
    if original_backup.exists():
        from snapshot_source_refresh import unprotect
        original = unprotect(original_backup.read_bytes(), b"OpenPlanLink MCP config backup v1")
        original_config = tomllib.loads(original.decode("utf-8-sig")) if original else {}
        current_config = tomllib.loads(config.read_text(encoding="utf-8-sig"))
        current_config.get("mcp_servers", {}).pop("wps365", None)
        original_config.setdefault("mcp_servers", {})
        for name, server in original_config["mcp_servers"].items():
            current = current_config.get("mcp_servers", {}).get(name, {})
            if server.get("args") == [] and "args" not in current:
                server.pop("args")
                normalized_empty_args.append(name)
        if current_config != original_config:
            raise RuntimeError("Unrelated Codex configuration changed during registration")
    receipt = {"checked_at_bjt": datetime.now(BJT).isoformat(), "server": "wps365",
               "transport": "stdio", "command": str(WPS), "args": expected["args"],
               "configured": True, "configuration_changed": changed,
               "unrelated_config_preserved": True, "credentials_in_mcp_config": False,
               "cli_normalized_empty_argument_arrays": normalized_empty_args,
               "raw_config_or_credentials_saved": False,
               "encrypted_private_backup": str(run / "config_backup_private") if changed else None}
    save(run, "wps_mcp_registration.json", receipt)
    return receipt


class StdioMCP:
    def __init__(self, command: list[str]):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.messages: queue.Queue = queue.Queue()
        self.sequence = 0
        def read():
            for line in self.process.stdout:
                if len(line) > 12_000_000:
                    self.messages.put({"read_error": "oversized_response"})
                    return
                try:
                    self.messages.put(json.loads(line))
                except json.JSONDecodeError:
                    self.messages.put({"read_error": "non_json_protocol_output"})
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def send(self, method: str, params: dict | None = None, notification: bool = False) -> dict:
        request = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = params
        if not notification:
            self.sequence += 1
            request["id"] = self.sequence
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        if notification:
            return {}
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if message.get("read_error"):
                raise RuntimeError(message["read_error"])
            if message.get("id") == request["id"]:
                return message
        raise TimeoutError("MCP response deadline")

    def close(self):
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)


def wps_probe(run: Path) -> dict:
    client = StdioMCP([str(WPS), "mcp", "serve", "--domains", "airpage,drive,user"])
    try:
        initial = client.send("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "OpenPlanLink connection verifier", "version": "1.0"}})
        if "error" in initial:
            raise RuntimeError("WPS MCP initialize failed")
        client.send("notifications/initialized", notification=True)
        catalog = client.send("tools/list").get("result", {}).get("tools", [])
        names = [tool["name"] for tool in catalog]
        if "user_me" not in names:
            raise RuntimeError("WPS MCP user tool missing")
        response = client.send("tools/call", {"name": "user_me", "arguments": {"token_type": "delegated"}})
        result = response.get("result", {})
        payloads = []
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    payloads.append(json.loads(block["text"]))
                except (json.JSONDecodeError, KeyError):
                    pass
        successful = any(isinstance(p, dict) and p.get("code") == 0 and
                         isinstance(p.get("data"), dict) and bool(p["data"].get("id")) for p in payloads)
        safe = {"checked_at_bjt": datetime.now(BJT).isoformat(), "server": "wps365",
                "initialize_ok": True, "protocol_version": initial["result"].get("protocolVersion"),
                "server_info": initial["result"].get("serverInfo"), "tool_count": len(catalog),
                "tools": [{"name": t["name"], "inputSchema": t.get("inputSchema", {})} for t in catalog],
                "user_me_tool_called": True, "provider_identity_verified": successful,
                "tool_is_error": bool(result.get("isError")), "raw_provider_response_saved": False,
                "stdio_process_stopped_after_probe": True}
        save(run, "wps_mcp_probe.json", safe)
        return {key: value for key, value in safe.items() if key != "tools"}
    finally:
        client.close()


def download_ima(run: Path) -> dict:
    with urllib.request.urlopen(IMA_PACKAGE, timeout=25) as response:
        package = response.read(20_000_001)
    if len(package) > 20_000_000:
        raise RuntimeError("Official IMA archive exceeds size limit")
    destination = run / "ima_official_package"
    destination.mkdir(exist_ok=False)
    entries = []
    with ZipFile(BytesIO(package)) as archive:
        if archive.testzip() is not None or len(archive.infolist()) > 500:
            raise RuntimeError("Official IMA archive validation failed")
        if sum(item.file_size for item in archive.infolist()) > 50_000_000:
            raise RuntimeError("IMA archive exceeds expanded size limit")
        for item in archive.infolist():
            relative = PurePosixPath(item.filename.replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts or any(":" in part for part in relative.parts):
                raise RuntimeError("Unsafe IMA archive path")
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("IMA archive contains a symlink")
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise RuntimeError("IMA extraction escaped destination")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                data = archive.read(item)
                with target.open("xb") as handle:
                    handle.write(data)
                entries.append({"path": item.filename, "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest()})
    receipt = {"checked_at_bjt": datetime.now(BJT).isoformat(), "official_page": "https://ima.qq.com/agent-interface",
               "download": IMA_PACKAGE, "sha256": hashlib.sha256(package).hexdigest(),
               "extracted_to": str(destination), "entries": entries, "executed_downloaded_code": False,
               "credential_files_read": False}
    save(run, "ima_official_package.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["wps-config", "wps-probe", "ima-download"])
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    args.run.mkdir(parents=True, exist_ok=True)
    action = {"wps-config": configure_wps, "wps-probe": wps_probe, "ima-download": download_ima}[args.action]
    try:
        result = action(args.run)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        failure = {"action": args.action, "error_type": type(exc).__name__,
                   "raw_error_suppressed": True, "checked_at_bjt": datetime.now(BJT).isoformat()}
        name = args.action + "_failure_" + datetime.now(BJT).strftime("%H%M%S%f") + ".json"
        save(args.run, name, failure)
        print(json.dumps(failure))
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
