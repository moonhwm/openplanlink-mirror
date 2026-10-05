#!/usr/bin/env python3
"""Read outgoing Git objects, without printing matched content or secret fragments."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

MAX_OBJECTS = 100_000
MAX_BYTES = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_MEMBERS = 1000
MAX_DEPTH = 3
MAX_HITS = 2000
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
RULES = (
    ("llm_key", r"\bs" + r"k-[A-Za-z0-9_-]{24,}"),
    ("github_token", r"\bgh" + r"[pousr]_[A-Za-z0-9]{20,}"),
    ("github_fine_token", r"\bgithub_" + r"pat_[A-Za-z0-9_]{30,}"),
    ("aws_access", r"\bAK" + r"IA[0-9A-Z]{16}\b"),
    ("cloud_access", r"\b(?:AK" + r"ID[A-Za-z0-9]{13,40}|LTAI[A-Za-z0-9]{12,24})\b"),
    ("send_key", r"\bS" + r"CT[A-Za-z0-9_-]{20,}"),
    ("bearer", r"\bBearer\s+[A-Za-z0-9_.=+-]{24,}"),
    ("url_auth", r"://[^/\s:@]+:[^/\s@]{6,}@"),
    ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRI" + r"VATE KEY-----"),
    ("signed_query", r"(?i)[?&](?:token|access[_-]?token|api[_-]?key|q-signature|q-ak|signature|x-amz-signature)=[^&\s<>\"']{12,}"),
    ("assigned_secret", r"(?i)\b(?:api[_-]?key|access[_-]?token|sendkey|client[_-]?secret)\s*[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_+/=-]{24,}[\"']"),
)
COMPILED = tuple((code, re.compile(pattern)) for code, pattern in RULES)


class GateError(Exception):
    """A fixed diagnostic code; Git stderr is never copied into reports."""


class Git:
    def __init__(self, repo: Path):
        self.repo = repo
        self.env = os.environ.copy()
        for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                     'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                     'GIT_NAMESPACE', 'GIT_SHALLOW_FILE'):
            self.env.pop(name, None)
        self.env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                        GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")

    def run(self, *args: str, data: bytes | None = None, optional: bool = False) -> bytes:
        try:
            r = subprocess.run(["git", "--no-replace-objects", "-C", str(self.repo), *args],
                               input=data, capture_output=True, env=self.env, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            raise GateError("git_unavailable_or_timeout") from None
        if r.returncode and not optional:
            raise GateError("git_object_read_failed")
        return b"" if r.returncode else r.stdout

    def validate_repository(self) -> None:
        if self.run("rev-parse", "--is-shallow-repository").strip() == b"true":
            raise GateError("shallow_history")
        if self.run("config", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$", optional=True):
            raise GateError("partial_clone")
        grafts = self.run("rev-parse", "--git-path", "info/grafts").decode("utf-8").strip()
        graft_path = Path(grafts)
        if not graft_path.is_absolute():
            graft_path = self.repo / graft_path
        if graft_path.exists():
            raise GateError("history_grafts")

    def resolve(self, ref: str) -> str:
        if ref.startswith("-") or any(c in ref for c in "\r\n\x00"):
            raise GateError("invalid_revision")
        value = self.run("rev-parse", "--verify", "--end-of-options", ref).strip().decode("ascii")
        if not OID.fullmatch(value):
            raise GateError("invalid_oid")
        return value


def updates_from_stdin(value: str) -> list[tuple[str, str]]:
    if len(value) > 262_144:
        raise GateError("update_input_limit")
    updates = []
    for line in value.splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise GateError("invalid_update_input")
        _, new, _, old = fields
        if not OID.fullmatch(new) or not OID.fullmatch(old) or len(new) != len(old):
            raise GateError("invalid_update_oid")
        updates.append((new, old))
    return updates


class Inspector:
    def __init__(self):
        self.hits: list[dict] = []
        self.incomplete: list[dict] = []
        self.expanded_bytes = 0
        self.members = 0
        self.text_parts = 0
        self.containers = 0

    def problem(self, oid: str, code: str, part: str = "body") -> None:
        entry = {"object": oid, "code": code, "part": part}
        if entry not in self.incomplete and len(self.incomplete) < MAX_HITS:
            self.incomplete.append(entry)

    def text(self, text: str, oid: str, part: str) -> None:
        self.text_parts += 1
        for code, pattern in COMPILED:
            for match in pattern.finditer(text):
                if len(self.hits) >= MAX_HITS:
                    self.problem(oid, "finding_limit")
                    return
                self.hits.append({"object": oid, "code": code, "part": part,
                                  "line": text.count("\n", 0, match.start()) + 1})

    def content(self, data: bytes, oid: str, part: str = "body", depth: int = 0,
                xml_expected: bool = False) -> None:
        if len(data) > MAX_BYTES:
            self.problem(oid, "part_size_limit", part)
            return
        if data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            if depth >= MAX_DEPTH:
                self.problem(oid, "archive_depth_limit", part)
                return
            self.containers += 1
            try:
                with ZipFile(BytesIO(data)) as archive:
                    for number, member in enumerate(archive.infolist(), 1):
                        if member.is_dir():
                            continue
                        self.members += 1
                        subpart = f"{part}/member-{number}"
                        self.text(member.filename, oid, subpart + "/name")
                        if self.members > MAX_MEMBERS:
                            self.problem(oid, "archive_member_limit", subpart)
                            break
                        self.expanded_bytes += member.file_size
                        if member.file_size > MAX_BYTES or self.expanded_bytes > MAX_TOTAL:
                            self.problem(oid, "archive_size_limit", subpart)
                            continue
                        if member.flag_bits & 1:
                            self.problem(oid, "archive_encrypted", subpart)
                            continue
                        # No extraction: member names cannot redirect writes or appear in reports.
                        self.content(archive.read(member), oid, subpart, depth + 1,
                                     member.filename.lower().endswith((".xml", ".rels")))
            except (BadZipFile, RuntimeError, OSError, ValueError, NotImplementedError):
                self.problem(oid, "archive_unreadable", part)
            return
        try:
            if data.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = data.decode("utf-16")
            else:
                text = data.decode("utf-8-sig")
                if "\x00" in text:
                    raise UnicodeError()
        except UnicodeError:
            # Inspect printable ASCII too; this does not clear unknown binary content.
            self.text(data.decode("ascii", "replace"), oid, part)
            self.problem(oid, "opaque_binary", part)
            return
        self.text(text, oid, part)
        if text.startswith("version https://git-lfs.github.com/spec/v1\n"):
            self.problem(oid, "lfs_content_unchecked", part)
        if xml_expected or text.lstrip().startswith("<"):
            try:
                xml = ET.fromstring(text)
            except ET.ParseError:
                if xml_expected:
                    self.problem(oid, "xml_unreadable", part)
                return
            # Join split OOXML runs as well as scanning raw attributes above.
            self.text("".join(xml.itertext()), oid, part + "/xml-text")

    def tree(self, data: bytes, oid: str) -> None:
        width = len(oid) // 2
        pos = 0
        while pos < len(data):
            end = data.find(b"\x00", pos)
            if end < 0 or b" " not in data[pos:end] or end + 1 + width > len(data):
                self.problem(oid, "tree_unreadable")
                return
            _, name = data[pos:end].split(b" ", 1)
            self.text(name.decode("utf-8", "replace"), oid, "tree/name")
            pos = end + 1 + width


def audit(repo: Path, updates: list[tuple[str, str]],
          signed_updates: list[tuple[str, str]] | None = None) -> dict:
    report = {"schema": "openplanlink.git-upload-gate/1", "status": "incomplete",
              "checked_at": datetime.now(timezone.utc).isoformat(), "updates": len(updates),
              "objects": 0, "scanned_objects": 0, "findings": [], "incomplete": [],
              "signature_failures": [],
              "limits": ["Known credential patterns only; no formal security clearance.",
                         "No matched text, path names or Git error text are included.",
                         "A local hook cannot prevent uploads that bypass Git or disable hooks."]}
    inspector = Inspector()
    try:
        git = Git(repo)
        git.validate_repository()
        if signed_updates:
            for new, old in signed_updates:
                if not new.strip("0"):
                    continue
                revisions = new + "\n"
                if old.strip("0"):
                    info = git.run("cat-file", "--batch-check", data=(old + "\n").encode()).split()
                    if len(info) == 3 and info[0].decode("ascii") == old:
                        revisions += "^" + old + "\n"
                commits = git.run("rev-list", "--stdin", data=revisions.encode()).decode("ascii").splitlines()
                if len(commits) > MAX_OBJECTS or any(not OID.fullmatch(x) for x in commits):
                    raise GateError("signature_enumeration_limit_or_format")
                for commit in commits:
                    status = git.run("log", "-1", "--format=%G?", commit).strip()
                    if status != b"G":
                        report["signature_failures"].append({"object": commit, "code": "main_signature_not_trusted"})
        positive, negative = set(), set()
        for new, old in updates:
            if not OID.fullmatch(new) or not OID.fullmatch(old) or len(new) != len(old):
                raise GateError("invalid_update_oid")
            if not new.strip("0"):
                continue
            positive.add(new)
            if old.strip("0"):
                info = git.run("cat-file", "--batch-check", data=(old + "\n").encode()).split()
                if len(info) == 3 and info[0].decode("ascii") == old:
                    negative.add(old)
        if positive:
            revisions = "\n".join(sorted(positive) + ["^" + x for x in sorted(negative)]) + "\n"
            object_ids = list(dict.fromkeys(git.run("rev-list", "--objects", "--no-object-names", "--stdin",
                                                   data=revisions.encode()).decode("ascii").splitlines()))
            if len(object_ids) > MAX_OBJECTS or any(not OID.fullmatch(x) for x in object_ids):
                raise GateError("object_enumeration_limit_or_format")
            report["objects"] = len(object_ids)
            if object_ids:
                request = ("\n".join(object_ids) + "\n").encode()
                metadata = git.run("cat-file", "--batch-check", data=request).splitlines()
                if len(metadata) != len(object_ids):
                    raise GateError("object_metadata_incomplete")
                accepted = []
                budget = 0
                for expected, line in zip(object_ids, metadata):
                    fields = line.split()
                    if len(fields) != 3 or fields[0].decode("ascii") != expected:
                        raise GateError("object_metadata_invalid")
                    kind = fields[1].decode("ascii")
                    if kind not in ("blob", "commit", "tag", "tree"):
                        raise GateError("object_type_unknown")
                    size = int(fields[2])
                    budget += size
                    if size > MAX_BYTES or budget > MAX_TOTAL:
                        inspector.problem(expected, "object_size_limit")
                    else:
                        accepted.append((expected, kind, size))
                if accepted:
                    body = git.run("cat-file", "--batch", data=("\n".join(x[0] for x in accepted) + "\n").encode())
                    stream = BytesIO(body)
                    for expected, kind, size in accepted:
                        header = stream.readline().decode("ascii").strip().split()
                        if header != [expected, kind, str(size)]:
                            raise GateError("object_content_header")
                        data = stream.read(size)
                        if len(data) != size or stream.read(1) != b"\n":
                            raise GateError("object_content_truncated")
                        if kind == "tree":
                            inspector.tree(data, expected)
                        else:
                            inspector.content(data, expected)
                        report["scanned_objects"] += 1
                    if stream.read(1):
                        raise GateError("object_content_trailing")
    except (GateError, OSError, UnicodeError, ValueError) as error:
        inspector.problem("unavailable", str(error) if isinstance(error, GateError) else "inspection_failed")
    report.update(findings=inspector.hits, incomplete=inspector.incomplete,
                  text_parts=inspector.text_parts, containers=inspector.containers)
    report["status"] = ("blocked_credentials" if inspector.hits else
                        "incomplete" if inspector.incomplete else
                        "blocked_signature" if report["signature_failures"] else "pass")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--pre-push", action="store_true")
    choice.add_argument("--range", nargs=2, metavar=("BASE", "HEAD"))
    choice.add_argument("--tip", metavar="REF")
    parser.add_argument("--require-signed-main", action="store_true",
                        help="With --pre-push, require trusted signatures on outgoing main commits.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.pre_push:
            value = sys.stdin.read(262_145)
            updates = updates_from_stdin(value)
            main_updates = [(f[1], f[3]) for f in (line.split() for line in value.splitlines())
                            if f[2] == "refs/heads/main"] if args.require_signed_main else None
        else:
            git = Git(args.repo)
            new = git.resolve(args.range[1] if args.range else args.tip)
            old = git.resolve(args.range[0]) if args.range else "0" * len(new)
            updates = [(new, old)]
            main_updates = None
        result = audit(args.repo, updates, signed_updates=main_updates)
    except (GateError, OSError, UnicodeError, ValueError) as error:
        result = {"schema": "openplanlink.git-upload-gate/1", "status": "incomplete",
                  "incomplete": [{"code": str(error) if isinstance(error, GateError) else "inspection_failed"}]}
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(encoded + "\n")
        except OSError:
            print('{"status":"incomplete","code":"report_write_failed"}')
            return 2
    print(encoded)
    return {"pass": 0, "blocked_credentials": 1, "blocked_signature": 1, "incomplete": 2}[result["status"]]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
