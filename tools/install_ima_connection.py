"""Install verified IMA documentation and the local read-only stdio adapter."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

from connect_wps_supabase_ima import BJT, CODEX, PS, protect

RUN = Path(r"A:\OPL_A2A\connections\20261006-three-apps-01")
SOURCE = RUN / "ima_official_package" / "ima-skill"
SKILL = Path(r"A:\OPL_A2A\skills\ima-skill-1.1.10")
CONNECTOR = Path(r"A:\OPL_A2A\connectors\ima-readonly\0.1.0")
NODE = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
GLOBAL_SKILL = Path.home() / ".agents/skills/ima-skill"


def main():
    package = json.loads((RUN / "ima_official_package.json").read_text(encoding="utf-8"))
    records = {item["path"]: item for item in package["entries"]}
    if SKILL.exists() or CONNECTOR.exists() or GLOBAL_SKILL.exists():
        raise RuntimeError("An installation destination exists; retained for explicit reconciliation")
    installed = []
    SKILL.mkdir(parents=True)
    for relative in ["SKILL.md", "ima_api.cjs", "meta.json", "knowledge-base/SKILL.md",
                     "knowledge-base/references/api.md", "knowledge-base/scripts/preflight-check.cjs",
                     "knowledge-base/scripts/cos-upload.cjs", "notes/SKILL.md", "notes/references/api.md",
                     "notes/scripts/note-images.cjs"]:
        data = (SOURCE / relative).read_bytes()
        expected = records["ima-skill/" + relative]["sha256"]
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError("Official IMA source differs from download receipt")
        repaired = False
        if relative in ("knowledge-base/SKILL.md", "notes/SKILL.md") and not data.startswith(b"---"):
            name = "ima-knowledge-base" if relative.startswith("knowledge-base") else "ima-notes"
            description = "ima 官方知识库接口模块，通过 ima-skill 总技能路由。" if relative.startswith("knowledge-base") else "ima 官方笔记接口模块，通过 ima-skill 总技能路由。"
            prefix = f"---\nname: {name}\ndescription: {description}\n---\n\n".encode("utf-8")
            data = prefix + data
            repaired = True
        destination = SKILL / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(data)
        if destination.read_bytes() != data:
            raise RuntimeError("Installed IMA file readback differs")
        installed.append({"path": relative, "upstream_sha256": expected,
                          "installed_sha256": hashlib.sha256(data).hexdigest(),
                          "loader_frontmatter_added": repaired})
    CONNECTOR.mkdir(parents=True)
    adapter_data = Path(__file__).with_name("ima_readonly_mcp.cjs").read_bytes()
    adapter = CONNECTOR / "server.cjs"
    with adapter.open("xb") as handle:
        handle.write(adapter_data)
    if adapter.read_bytes() != adapter_data:
        raise RuntimeError("Installed IMA adapter differs")
    GLOBAL_SKILL.parent.mkdir(parents=True, exist_ok=True)
    def ps_literal(value):
        return "'" + str(value).replace("'", "''") + "'"
    junction_command = "New-Item -ItemType Junction -Path " + ps_literal(GLOBAL_SKILL) + " -Target " + ps_literal(SKILL) + " | Out-Null"
    subprocess.run([str(PS), "-NoProfile", "-Command", junction_command],
                   capture_output=True, check=True, timeout=15)
    if GLOBAL_SKILL.resolve() != SKILL.resolve():
        raise RuntimeError("IMA global skill junction does not resolve to installation")
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = config.read_bytes()
    parsed_before = tomllib.loads(before.decode("utf-8-sig"))
    if "ima-readonly" in parsed_before.get("mcp_servers", {}):
        raise RuntimeError("Existing IMA server configuration retained")
    private = RUN / "config_backup_private"
    with (private / "codex-config-before-ima.toml.dpapi").open("xb") as handle:
        handle.write(protect(before))
    expected_args = [str(adapter), str(SKILL)]
    result = subprocess.run([str(PS), "-NoProfile", "-File", str(CODEX), "mcp", "add", "ima-readonly",
                             "--", str(NODE), *expected_args], capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Codex IMA registration failed; raw output suppressed")
    after = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    new_server = after.get("mcp_servers", {}).pop("ima-readonly", {})
    if new_server.get("command") != str(NODE) or new_server.get("args") != expected_args:
        raise RuntimeError("Registered IMA command differs")
    for name, entry in parsed_before.get("mcp_servers", {}).items():
        if entry.get("args") == [] and "args" not in after.get("mcp_servers", {}).get(name, {}):
            entry.pop("args")
    if after != parsed_before:
        raise RuntimeError("Unrelated Codex configuration changed")
    receipt = {"checked_at_bjt": datetime.now(BJT).isoformat(), "skill_version": "1.1.10",
               "local_loader_compatibility_revision": 1, "global_skill": str(GLOBAL_SKILL),
               "installed_skill": str(SKILL), "installed_files": installed,
               "server": "ima-readonly", "adapter": str(adapter),
               "adapter_sha256": hashlib.sha256(adapter_data).hexdigest(),
               "configured": True, "unrelated_config_preserved": True,
               "credential_values_copied": False, "native_ima_process_modified": False,
               "vendored_to_public_repository": False}
    with (RUN / "ima_installation.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    print(json.dumps({key: value for key, value in receipt.items() if key != "installed_files"}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "raw_error_suppressed": True}))
        raise SystemExit(1)
