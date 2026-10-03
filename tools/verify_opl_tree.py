#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 Git 暂存区逐文件复算 OPL SHA3-512 树；不验证 HMAC。"""

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

SCHEMA = "opl-hmac-sha3-512-tree/1"
TREE_ALGORITHM = "sha3-512"
MAC_ALGORITHM = "hmac-sha3-512"
LEAF_ENCODING = "0x00 || uint32be(path_utf8_len) || path_utf8 || uint64be(size) || sha3_512(content)"
NODE_ENCODING = "0x01 || left_digest || right_digest; duplicate odd right node"
MAC_ENCODING = "UTF8(OpenPlanLink-A2A-Merkle-v1\\0) || root_digest || uint64be(file_count) || uint16be(key_id_utf8_len) || key_id_utf8 || uint16be(generated_at_utf8_len) || generated_at_utf8"
DEFAULT_MANIFEST = "attest-hmac-sha3-512.json"
HEX_512 = re.compile(r"^[0-9a-f]{128}$")
KEY_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
MAX_SAFE_INTEGER = 2**53 - 1
MANIFEST_KEYS = {
    "schema",
    "generated_at",
    "tree_algorithm",
    "mac_algorithm",
    "leaf_encoding",
    "node_encoding",
    "mac_encoding",
    "key_id",
    "file_count",
    "merkle_root_sha3_512",
    "hmac_sha3_512",
    "files",
}


def fail(message):
    raise ValueError(message)


def git_environment():
    environment = os.environ.copy()
    for name in list(environment):
        if name.upper() in {"OPL_A2A_HMAC_KEY_B64", "OPL_A2A_HMAC_KEY_DPAPI_B64"}:
            del environment[name]
    return environment


def run_git(root, *args, input_bytes=None):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        check=True,
        env=git_environment(),
    ).stdout


def repository_root():
    root_text = run_git(Path.cwd(), "rev-parse", "--show-toplevel").decode("utf-8", "strict")
    root_text = root_text.rstrip("\r\n")
    if not root_text or "\r" in root_text or "\n" in root_text:
        fail("invalid Git repository root")
    root = Path(root_text).resolve(strict=True)
    cwd = Path.cwd().resolve(strict=True)
    same = os.path.normcase(str(root)) == os.path.normcase(str(cwd))
    if not same:
        fail("run from the Git repository root")
    return root


def normalize_path(file_path):
    if not isinstance(file_path, str) or not file_path or file_path.startswith("/") or "\x00" in file_path:
        fail(f"unsafe path: {file_path}")
    segments = file_path.split("/")
    if any(not segment or segment in {".", ".."} for segment in segments):
        fail(f"unsafe path: {file_path}")
    return file_path


def index_records(root):
    raw = run_git(root, "ls-files", "--stage", "-z", "--cached")
    records = []
    for record in raw.rstrip(b"\0").split(b"\0") if raw else []:
        metadata, separator, path_bytes = record.partition(b"\t")
        if not separator:
            fail("invalid git index record")
        try:
            mode, object_id, stage = metadata.decode("ascii").split(" ")
            file_path = path_bytes.decode("utf-8", "strict")
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("invalid git index record") from error
        if file_path.encode("utf-8") != path_bytes:
            fail("git path is not canonical UTF-8")
        normalize_path(file_path)
        if stage != "0":
            fail(f"unmerged index entry: {file_path}")
        if mode not in {"100644", "100755"}:
            fail(f"unsupported git mode {mode}: {file_path}")
        if not re.fullmatch(r"[0-9a-f]+", object_id):
            fail(f"invalid git object id: {file_path}")
        records.append((file_path, object_id))
    records.sort(key=lambda item: item[0].encode("utf-8"))
    return records


def read_index_blobs(root, records):
    if not records:
        return []
    request = ("\n".join(object_id for _, object_id in records) + "\n").encode("ascii")
    output = run_git(root, "cat-file", "--batch", input_bytes=request)
    offset = 0
    files = []
    for file_path, expected_id in records:
        newline = output.find(b"\n", offset)
        if newline < 0:
            fail("truncated git cat-file header")
        try:
            object_id, object_type, size_text = output[offset:newline].decode("ascii").split(" ")
            size = int(size_text)
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError(f"invalid git blob response: {file_path}") from error
        if object_id != expected_id or object_type != "blob" or size < 0 or size > MAX_SAFE_INTEGER:
            fail(f"invalid git blob response: {file_path}")
        start = newline + 1
        end = start + size
        if end >= len(output) or output[end] != 10:
            fail(f"truncated git blob: {file_path}")
        files.append((file_path, output[start:end]))
        offset = end + 1
    if offset != len(output):
        fail("unexpected trailing git cat-file output")
    return files


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest(root, records, manifest_name):
    matches = [record for record in records if record[0] == manifest_name]
    if len(matches) != 1:
        fail(f"manifest is not staged: {manifest_name}")
    manifest_bytes = read_index_blobs(root, matches)[0][1]
    try:
        return json.loads(
            manifest_bytes.decode("utf-8", "strict"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda value: fail(f"non-standard JSON constant: {value}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid manifest JSON") from error


def sha3(data):
    return hashlib.sha3_512(data).digest()


def leaf_for(file_path, content):
    path_bytes = normalize_path(file_path).encode("utf-8")
    content_hash = sha3(content)
    leaf_hash = sha3(
        b"\x00"
        + struct.pack(">I", len(path_bytes))
        + path_bytes
        + struct.pack(">Q", len(content))
        + content_hash
    )
    return {
        "path": file_path,
        "size": len(content),
        "content_sha3_512": content_hash.hex(),
        "leaf_sha3_512": leaf_hash.hex(),
    }


def merkle_root(entries):
    if not entries:
        fail("cannot build an empty tree")
    level = [bytes.fromhex(entry["leaf_sha3_512"]) for entry in entries]
    while len(level) > 1:
        next_level = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(sha3(b"\x01" + left + right))
        level = next_level
    return level[0].hex()


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        fail("manifest must be an object")
    if set(manifest) != MANIFEST_KEYS:
        fail("manifest field set mismatch")
    if manifest.get("schema") != SCHEMA:
        fail("schema mismatch")
    if manifest.get("tree_algorithm") != TREE_ALGORITHM or manifest.get("mac_algorithm") != MAC_ALGORITHM:
        fail("algorithm mismatch")
    if (
        manifest.get("leaf_encoding") != LEAF_ENCODING
        or manifest.get("node_encoding") != NODE_ENCODING
        or manifest.get("mac_encoding") != MAC_ENCODING
    ):
        fail("encoding contract mismatch")
    key_id = manifest.get("key_id")
    if not isinstance(key_id, str) or not KEY_ID.fullmatch(key_id):
        fail("invalid key_id")
    generated_at = manifest.get("generated_at")
    if not isinstance(generated_at, str) or not ISO_UTC.fullmatch(generated_at):
        fail("generated_at must be canonical UTC ISO-8601")
    try:
        datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as error:
        raise ValueError("generated_at must be canonical UTC ISO-8601") from error
    file_count = manifest.get("file_count")
    if isinstance(file_count, bool) or not isinstance(file_count, int) or not 1 <= file_count <= MAX_SAFE_INTEGER:
        fail("invalid file_count")
    root_digest = manifest.get("merkle_root_sha3_512")
    hmac_digest = manifest.get("hmac_sha3_512")
    if not isinstance(root_digest, str) or not HEX_512.fullmatch(root_digest):
        fail("invalid Merkle root encoding")
    if not isinstance(hmac_digest, str) or not HEX_512.fullmatch(hmac_digest):
        fail("invalid HMAC encoding")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != file_count:
        fail("file list mismatch")
    previous = None
    seen = set()
    expected_keys = {"path", "size", "content_sha3_512", "leaf_sha3_512"}
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != expected_keys:
            fail("invalid file entry")
        file_path = normalize_path(entry.get("path"))
        path_bytes = file_path.encode("utf-8")
        if previous is not None and previous >= path_bytes:
            fail("file paths are not strictly sorted")
        previous = path_bytes
        if file_path in seen:
            fail("duplicate file path")
        seen.add(file_path)
        size = entry.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_SAFE_INTEGER:
            fail(f"invalid file size: {file_path}")
        content_digest = entry.get("content_sha3_512")
        leaf_digest = entry.get("leaf_sha3_512")
        if not isinstance(content_digest, str) or not HEX_512.fullmatch(content_digest):
            fail(f"invalid content digest: {file_path}")
        if not isinstance(leaf_digest, str) or not HEX_512.fullmatch(leaf_digest):
            fail(f"invalid leaf digest: {file_path}")


def main():
    manifest_name = sys.argv[1] if len(sys.argv) == 2 else DEFAULT_MANIFEST
    if len(sys.argv) > 2 or Path(manifest_name).name != manifest_name or manifest_name in {".", ".."}:
        fail("usage: python tools/verify_opl_tree.py [root-manifest-name]")
    root = repository_root()
    records = index_records(root)
    if os.name == "nt":
        conflicts = [path for path, _ in records if path.lower() == manifest_name.lower() and path != manifest_name]
        if conflicts:
            fail(f"manifest path case conflict: {conflicts[0]}")
    manifest = load_manifest(root, records, manifest_name)
    validate_manifest(manifest)
    files = read_index_blobs(root, [record for record in records if record[0] != manifest_name])
    actual_entries = [leaf_for(file_path, content) for file_path, content in files]
    actual_root = merkle_root(actual_entries)
    if actual_entries != manifest["files"]:
        fail("staged file set or content does not match manifest")
    if actual_root != manifest["merkle_root_sha3_512"]:
        fail("Merkle root does not match staged content")
    print(f"verified staged content ({len(actual_entries)} files)")
    print(f"merkle_root_sha3_512={actual_root}")
    print("AUTHENTICATION=NOT_VERIFIED")
    print("VERDICT=MERKLE_ONLY_PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError, TypeError, ValueError) as error:
        print(f"verification failed: {error}", file=sys.stderr)
        print("VERDICT=BAD", file=sys.stderr)
        sys.exit(1)
