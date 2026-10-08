"""OOXML 包内元数据可溯性门禁（SPEC-20261005-SELFVO-02 / PLAN-20261005-SELFVO-02）。

只读：不回写任何 OOXML 部件，不读环境变量，不做网络调用。
fail-closed：一切异常收敛为 BLOCK，绝不降级为 PASS / SKIP / WARN。
报告不含正文片段；作者标识只出指纹与长度；云存根只出字段名不出取值。
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 判据编号一经发布即冻结语义（宪法门禁 6）：新增判据只追加，放宽须升版本并在
# specs/002-ooxml-meta-traceability/tasks.md T009 登记。
GATE_VERSION = "1.0.0"

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}

CORE_PART = "docProps/core.xml"
APP_PART = "docProps/app.xml"
DOCUMENT_PART = "word/document.xml"

KIND_OOXML = "ooxml"
KIND_CLOUD_STUB = "cloud_stub"
KIND_PLAIN_TEXT = "plain_text"
KIND_UNKNOWN = "unknown"

# WPS 云指针存根的实测契约（2026-10-05 对真实在档件逐字节解出）：
#   magic "qonline\x00"(8B) + uint32 版本 + uint32 载荷偏移 + uint32 载荷容量
#   + uint32 保留 + UTF-16LE 载荷（NUL 补齐至容量），载荷为 & 分隔的 key=value。
# 载荷偏移按头部声明值取用，不硬编码——头部自描述即契约。
STUB_MAGIC = b"qonline\x00"
STUB_HEADER_STRUCT = "<4I"
STUB_HEADER_BYTES = 8 + 16
STUB_EXTENSION = ".wpsonline"

VERDICT_PASS = "PASS"
VERDICT_WARN = "WARN"
VERDICT_BLOCK = "BLOCK"
VERDICT_NOT_APPLICABLE = "NOT_APPLICABLE"

LEVEL_ERROR = "E"
LEVEL_WARN = "W"
LEVEL_INFO = "I"

# 全球时区偏移为 15 分钟的整数倍，范围 [-14, +14] 小时。
_TZ_CANDIDATE_HOURS = [round(i * 0.25, 2) for i in range(-56, 57)]
# mtime 在 XML 时间戳之后落盘，故允许数秒至数分钟残差；超出即非「整小时误标」。
_TZ_RESIDUAL_TOLERANCE_SECONDS = 300.0
# 声明时刻与文件系统 mtime 视为一致的容差。
_TZ_MATCH_TOLERANCE_SECONDS = 180.0


def _finding(code, level, reason, **evidence):
    f = {"code": code, "level": level, "reason": reason}
    f.update(evidence)
    return f


def _fingerprint(value):
    """作者类标识只出指纹与长度，不出字面值（AC-5）。"""
    if value is None:
        return {"present": False, "sha3_512_16": None, "chars": 0}
    return {
        "present": True,
        "sha3_512_16": hashlib.sha3_512(value.encode("utf-8")).hexdigest()[:16],
        "chars": len(value),
    }


def _text(root, prefixed_tag):
    prefix, _, local = prefixed_tag.partition(":")
    uri = NS.get(prefix)
    if uri is None:
        return None
    node = root.find("{%s}%s" % (uri, local))
    if node is None or node.text is None:
        return None
    return node.text.strip()


def _parse_ooxml_datetime(raw):
    """解析 OOXML 日期串。

    返回 (aware_or_naive_datetime, declared_utc)；不可解析返回 (None, None)。
    手工把尾缀 Z 换成 +00:00：Python 3.10 及更早的 fromisoformat 不认 Z，
    依赖版本差异会让门禁在不同机器上给出不同裁定。
    """
    if not raw:
        return None, None
    s = raw.strip()
    declared_utc = s.endswith("Z") or s.endswith("z")
    if declared_utc:
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None, None
    if dt.tzinfo is None and declared_utc:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt, declared_utc


def _int_or_none(raw):
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _classify(raw: bytes, path: Path) -> str:
    if raw[:2] == b"PK" and zipfile.is_zipfile(path):
        return KIND_OOXML
    if raw[:8] == STUB_MAGIC:
        return KIND_CLOUD_STUB
    if path.name.lower().endswith(STUB_EXTENSION):
        # 扩展名声明为云指针而魔数不符时仍按存根处置：「未取到正文」与
        # 「正文可溯」必须在台账上可区分，故绝不降级为可读文本。
        return KIND_CLOUD_STUB
    try:
        raw.decode("utf-8")
        return KIND_PLAIN_TEXT
    except UnicodeDecodeError:
        return KIND_UNKNOWN


def _parse_qonline_stub(raw: bytes) -> dict:
    """解出云指针存根的头部与键名。只返回键名，不返回取值（FR-3.3）。

    fileid / groupid 是可定位标识，随报告外流即等于公开该云件地址。
    """
    out = {
        "magic_match": raw[:8] == STUB_MAGIC,
        "stub_version": None, "payload_offset": None, "payload_capacity": None,
        "field_names": None, "field_count": None,
    }
    if not out["magic_match"] or len(raw) < STUB_HEADER_BYTES:
        return out
    version, offset, capacity, _reserved = struct.unpack(
        STUB_HEADER_STRUCT, raw[8:STUB_HEADER_BYTES])
    out["stub_version"] = version
    out["payload_offset"] = offset
    out["payload_capacity"] = capacity
    if not STUB_HEADER_BYTES <= offset <= len(raw):
        return out
    end = offset + capacity if capacity else len(raw)
    payload = raw[offset:min(end, len(raw))]
    payload = payload[: len(payload) - (len(payload) % 2)]
    text = payload.decode("utf-16-le", "replace").split("\x00", 1)[0]
    keys = [p.partition("=")[0] for p in text.split("&") if p.partition("=")[1]]
    out["field_count"] = len(keys)
    out["field_names"] = sorted(set(keys)) or None
    return out


def _recover_offset(declared: datetime, fs_utc: datetime):
    """判定「声明 Z 但内装本地墙钟」，并复原真实 UTC。

    返回 (status, offset_hours, recovered_utc)：
      status="match"       声明值与 fs mtime 的 UTC 一致（容差内）
      status="recovered"   偏移可解析为 15 分钟整数倍 → 本地墙钟误标 Z
      status="unresolvable" 偏移无法归因于任何合法时区 → 真实时钟异常
    """
    skew = (declared - fs_utc).total_seconds()
    if abs(skew) <= _TZ_MATCH_TOLERANCE_SECONDS:
        return "match", 0.0, declared
    best = min(_TZ_CANDIDATE_HOURS, key=lambda h: abs(skew - h * 3600.0))
    residual = abs(skew - best * 3600.0)
    if residual <= _TZ_RESIDUAL_TOLERANCE_SECONDS:
        return "recovered", best, declared - timedelta(hours=best)
    return "unresolvable", None, None


def extract(path) -> dict:
    """只读提取包内元数据与包级完整性（FR-1）。不含任何正文片段。"""
    p = Path(path)
    raw = p.read_bytes()
    st = p.stat()
    rec = {
        "path": str(p),
        "name": p.name,
        "kind": _classify(raw, p),
        "bytes": len(raw),
        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
        "fs_mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(st.st_mtime)),
        "sha3_512": hashlib.sha3_512(raw).hexdigest(),
        "sha3_512_16": hashlib.sha3_512(raw).hexdigest()[:16],
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if rec["kind"] == KIND_CLOUD_STUB:
        rec["stub"] = _parse_qonline_stub(raw)
        return rec
    if rec["kind"] != KIND_OOXML:
        return rec

    with zipfile.ZipFile(p) as z:
        rec["zip_crc"] = "pass" if z.testzip() is None else "fail"
        names = z.namelist()
        rec["parts"] = len(names)
        rec["media_parts"] = sum(1 for n in names if n.startswith("word/media/"))
        rec["has_core_part"] = CORE_PART in names
        rec["has_app_part"] = APP_PART in names
        doc = z.read(DOCUMENT_PART).decode("utf-8", "replace") if DOCUMENT_PART in names else ""
        rec["tracked_insertions"] = doc.count("<w:ins ")
        rec["tracked_deletions"] = doc.count("<w:del ")
        rec["nonempty_paras_wt"] = len(
            [s for s in doc.split("</w:p>") if "<w:t " in s or "<w:t>" in s]
        )

        core = ET.fromstring(z.read(CORE_PART)) if rec["has_core_part"] else None
        app = ET.fromstring(z.read(APP_PART)) if rec["has_app_part"] else None

    if core is not None:
        rec["meta_created_raw"] = _text(core, "dcterms:created")
        rec["meta_modified_raw"] = _text(core, "dcterms:modified")
        rec["meta_creator"] = _fingerprint(_text(core, "dc:creator"))
        rec["meta_last_modified_by"] = _fingerprint(_text(core, "cp:lastModifiedBy"))
        rec["meta_revision"] = _text(core, "cp:revision")
    else:
        rec["meta_created_raw"] = rec["meta_modified_raw"] = None
        rec["meta_creator"] = _fingerprint(None)
        rec["meta_last_modified_by"] = _fingerprint(None)
        rec["meta_revision"] = None

    if app is not None:
        rec["meta_application"] = _text(app, "ep:Application")
        rec["meta_total_time"] = _int_or_none(_text(app, "ep:TotalTime"))
        rec["meta_pages"] = _int_or_none(_text(app, "ep:Pages"))
        rec["meta_words"] = _int_or_none(_text(app, "ep:Words"))
        rec["meta_paragraphs"] = _int_or_none(_text(app, "ep:Paragraphs"))
    else:
        rec.update(
            meta_application=None, meta_total_time=None,
            meta_pages=None, meta_words=None, meta_paragraphs=None,
        )

    created, created_utc = _parse_ooxml_datetime(rec["meta_created_raw"])
    modified, modified_utc = _parse_ooxml_datetime(rec["meta_modified_raw"])
    rec["created_parsed_utc"] = created.astimezone(timezone.utc).isoformat() if created and created.tzinfo else (created.isoformat() if created else None)
    rec["modified_parsed_utc"] = modified.astimezone(timezone.utc).isoformat() if modified and modified.tzinfo else (modified.isoformat() if modified else None)
    rec["created_declared_utc"] = created_utc
    rec["modified_declared_utc"] = modified_utc
    rec["_created_dt"] = created
    rec["_modified_dt"] = modified
    return rec


def _findings_for_ooxml(rec: dict) -> list:
    out = []
    if rec.get("zip_crc") == "fail":
        out.append(_finding("E-ZIP-CRC-FAIL", LEVEL_ERROR, "包内部件 CRC 校验失败，字节完整性不可信"))
    if not rec.get("has_core_part"):
        out.append(_finding("E-PART-MISSING", LEVEL_ERROR, "缺 %s，创建/修改时刻不可溯" % CORE_PART, part=CORE_PART))
    if not rec.get("has_app_part"):
        out.append(_finding("E-PART-MISSING", LEVEL_ERROR, "缺 %s，著录统计不可溯" % APP_PART, part=APP_PART))

    created = rec.get("_created_dt")
    modified = rec.get("_modified_dt")

    if created is None and rec.get("meta_created_raw"):
        out.append(_finding("E-TZ-UNRESOLVABLE", LEVEL_ERROR,
                            "dcterms:created 不可解析为 ISO-8601",
                            raw_len=len(rec["meta_created_raw"])))
    if modified is None and rec.get("meta_modified_raw"):
        out.append(_finding("E-TZ-UNRESOLVABLE", LEVEL_ERROR,
                            "dcterms:modified 不可解析为 ISO-8601",
                            raw_len=len(rec["meta_modified_raw"])))

    if created is not None and modified is not None:
        if bool(created.tzinfo) != bool(modified.tzinfo):
            # 两值时区标记不一致 → 无法比较，属时区不可判定，复用已冻结编号。
            out.append(_finding("E-TZ-UNRESOLVABLE", LEVEL_ERROR,
                                "created 与 modified 时区标记不一致，无法比较",
                                created_declared_utc=rec["created_declared_utc"],
                                modified_declared_utc=rec["modified_declared_utc"]))
        else:
            delta = (created - modified).total_seconds()
            if delta > 0:
                out.append(_finding(
                    "E-TEMPORAL-INVERSION", LEVEL_ERROR,
                    "dcterms:created 晚于 dcterms:modified，该件自身时序自相矛盾",
                    created=rec["created_parsed_utc"], modified=rec["modified_parsed_utc"],
                    inversion_seconds=round(delta, 1),
                    inversion_hours=round(delta / 3600.0, 2)))

    # 时区标记核验：以文件系统 mtime 的 UTC 值为外部参照。
    if modified is not None and rec.get("modified_declared_utc"):
        try:
            fs_utc = datetime.strptime(rec["fs_mtime_utc"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError, TypeError):
            fs_utc = None
        if fs_utc is not None:
            status, offset, recovered = _recover_offset(modified, fs_utc)
            rec["tz_status"] = status
            if status == "recovered":
                out.append(_finding(
                    "W-TZ-MISLABEL", LEVEL_WARN,
                    "dcterms:modified 带 Z（UTC）后缀但内装本地墙钟；已按整时区偏移复原",
                    declared=rec["modified_parsed_utc"],
                    actual_offset_hours=offset,
                    recovered_utc=recovered.isoformat(),
                    fs_mtime_utc=rec["fs_mtime_utc"]))
                rec["tz_recovered_utc"] = recovered.isoformat()
                rec["tz_actual_offset_hours"] = offset
            elif status == "unresolvable":
                skew = (modified - fs_utc).total_seconds()
                out.append(_finding(
                    "E-TZ-UNRESOLVABLE", LEVEL_ERROR,
                    "dcterms:modified 声明 UTC，但与文件系统 mtime 的偏差无法归因于任何合法时区偏移",
                    skew_seconds=round(skew, 1), skew_hours=round(skew / 3600.0, 2),
                    tolerance_seconds=_TZ_RESIDUAL_TOLERANCE_SECONDS))
            else:
                rec["tz_actual_offset_hours"] = 0.0

    if rec.get("meta_total_time") == 0 and (rec.get("meta_words") or 0) > 0:
        out.append(_finding(
            "W-NO-AUTHORING-TIME", LEVEL_WARN,
            "TotalTime=0 而 Words>0：累计著录时长为零，该件为「再保存」而非著录会话",
            total_time=0, words=rec["meta_words"], application=rec.get("meta_application")))

    ins = rec.get("tracked_insertions") or 0
    dels = rec.get("tracked_deletions") or 0
    if ins or dels:
        out.append(_finding(
            "I-TRACKED-CHANGES", LEVEL_INFO,
            "存在未接受的修订标记，当前内容非单一 settled 文本",
            insertions=ins, deletions=dels))
    return out


def _verdict_from(findings: list) -> str:
    levels = {f["level"] for f in findings}
    if LEVEL_ERROR in levels:
        return VERDICT_BLOCK
    if LEVEL_WARN in levels:
        return VERDICT_WARN
    return VERDICT_PASS


def _public(rec: dict) -> dict:
    """剥离内部字段，只留可出档内容。"""
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def gate(path) -> dict:
    """对单件出裁定。fail-closed：一切异常收敛为 BLOCK（AC-6）。"""
    p = Path(path)
    try:
        if not p.is_file():
            return {
                "path": str(p), "name": p.name, "kind": None,
                "verdict": VERDICT_BLOCK,
                "findings": [_finding("E-READ-FAIL", LEVEL_ERROR, "文件不存在或不可读", exists=False)],
                "gate_version": GATE_VERSION,
            }
        rec = extract(p)
        kind = rec["kind"]

        if kind == KIND_PLAIN_TEXT:
            # 「未检查」与「检查通过」必须在台账上可区分（plan.md 取向 2）。
            return {
                **_public(rec), "verdict": VERDICT_NOT_APPLICABLE,
                "findings": [],
                "not_applicable_reason": "非 OOXML 件，无包内元数据面，判据不适用",
                "gate_version": GATE_VERSION,
            }
        if kind == KIND_CLOUD_STUB:
            stub = rec.get("stub") or {}
            reason = ("云指针存根，正文不可得；厂商权益门禁，本门禁不尝试绕过"
                      if stub.get("magic_match") else
                      "扩展名声明为云指针存根但魔数与 qonline 契约不符；"
                      "正文同样不可得，按 fail-closed 判 BLOCK 而非可读文本")
            return {
                **_public(rec), "verdict": VERDICT_BLOCK,
                "findings": [_finding(
                    "E-STUB-NO-BODY", LEVEL_ERROR, reason,
                    bytes=rec["bytes"],
                    magic_match=bool(stub.get("magic_match")),
                    stub_version=stub.get("stub_version"),
                    payload_offset=stub.get("payload_offset"),
                    field_count=stub.get("field_count"),
                    field_names=stub.get("field_names"))],
                "gate_version": GATE_VERSION,
            }
        if kind == KIND_UNKNOWN:
            return {
                **_public(rec), "verdict": VERDICT_BLOCK,
                "findings": [_finding("E-READ-FAIL", LEVEL_ERROR, "既非 OOXML 包亦非 UTF-8 文本，身份不可判")],
                "gate_version": GATE_VERSION,
            }

        findings = _findings_for_ooxml(rec)
        return {
            **_public(rec), "verdict": _verdict_from(findings),
            "findings": findings, "gate_version": GATE_VERSION,
        }
    except Exception as exc:  # noqa: BLE001 - fail-closed 收敛点
        return {
            "path": str(p), "name": p.name, "kind": None,
            "verdict": VERDICT_BLOCK,
            "findings": [_finding(
                "E-READ-FAIL", LEVEL_ERROR, "门禁自身异常，按 fail-closed 收敛为 BLOCK",
                exception=type(exc).__name__)],
            "exception": type(exc).__name__,
            "gate_version": GATE_VERSION,
        }


def compare_snapshots(a_items, b_items, key, name_field="name"):
    """跨快照比对。

    `key` 为必填位置参数，无默认值：不给「不声明也能跑」的余地（FR-4.1）。
    缺键即 INCOMPARABLE 并具名披露缺失字段，**绝不回落至其他字段**（FR-4.5）——
    静默回落会在两侧 schema 命名不同时产出自信的错误结论（2026-10-05 实测：
    10/10 条假 DRIFT，实为 0 漂移）。
    """
    def _incomparable(reason, **extra):
        base = {
            "verdict": "INCOMPARABLE", "comparable": False, "reason": reason,
            "key": key, "name_field": name_field,
            "missing_in_a": [], "missing_in_b": [], "only_in_a": [], "only_in_b": [],
            "per_item": [], "drift_count": None, "same_count": None,
            "total": None,
        }
        base.update(extra)
        return base

    if not isinstance(a_items, list) or not isinstance(b_items, list):
        return _incomparable("快照须为条目列表", a_type=type(a_items).__name__, b_type=type(b_items).__name__)
    if not isinstance(key, str) or not key:
        return _incomparable("比对键须为非空字符串且必须显式声明")

    for side, items in (("a", a_items), ("b", b_items)):
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                return _incomparable("条目须为对象", side=side, index=i,
                                     entry_type=type(it).__name__)

    def _index(items):
        out = {}
        for it in items:
            n = it.get(name_field)
            if not isinstance(n, str) or not n:
                return None, n
            out[n] = it
        return out, None

    a_map, a_bad = _index(a_items)
    if a_map is None:
        return _incomparable("a 侧存在缺失或非法的 %s 字段" % name_field, bad_value_type=type(a_bad).__name__)
    b_map, b_bad = _index(b_items)
    if b_map is None:
        return _incomparable("b 侧存在缺失或非法的 %s 字段" % name_field, bad_value_type=type(b_bad).__name__)

    missing_in_a = [{"name": n, "missing_fields": [key]} for n in sorted(a_map) if key not in a_map[n]]
    missing_in_b = [{"name": n, "missing_fields": [key]} for n in sorted(b_map) if key not in b_map[n]]
    only_in_a = sorted(set(a_map) - set(b_map))
    only_in_b = sorted(set(b_map) - set(a_map))

    if missing_in_a or missing_in_b or only_in_a or only_in_b:
        return _incomparable(
            "声明的比对键或名称集合在两侧不齐备，拒绝比对（禁止静默回落）",
            missing_in_a=missing_in_a, missing_in_b=missing_in_b,
            only_in_a=only_in_a, only_in_b=only_in_b,
            count_a=len(a_map), count_b=len(b_map))

    per_item = []
    drift = 0
    for n in sorted(a_map):
        same = a_map[n][key] == b_map[n][key]
        if not same:
            drift += 1
        per_item.append({"name": n, "key": key, "result": "SAME" if same else "DRIFT"})
    return {
        "verdict": "COMPARABLE", "comparable": True, "reason": "",
        "key": key, "name_field": name_field,
        "missing_in_a": [], "missing_in_b": [], "only_in_a": [], "only_in_b": [],
        "per_item": per_item, "drift_count": drift, "same_count": len(per_item) - drift,
        "total": len(per_item),
    }


def run(paths):
    """对一组路径出门禁报告。generated_at 为唯一随运行变化的字段（AC-7）。"""
    reports = [gate(p) for p in paths]
    tally = {}
    for r in reports:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    codes = {}
    for r in reports:
        for f in r["findings"]:
            codes[f["code"]] = codes.get(f["code"], 0) + 1
    return {
        "schema": "ooxml-meta-traceability-gate/1",
        "gate_version": GATE_VERSION,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(reports),
        "tally": tally,
        "finding_codes": codes,
        "reports": reports,
    }


def main(argv):
    paths = argv[1:]
    if not paths:
        print("usage: python -m selfevo.ooxml_meta <path> [<path> ...]", file=sys.stderr)
        return 2
    report = run(paths)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["tally"].get(VERDICT_BLOCK, 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
