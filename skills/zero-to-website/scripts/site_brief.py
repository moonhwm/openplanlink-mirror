#!/usr/bin/env python3
"""Initialize and validate a zero-to-website intake brief using only stdlib."""

import argparse
import json
import sys
from pathlib import Path

SITE_TYPES = {
    "marketing", "blog", "portfolio", "docs", "saas", "dashboard",
    "community", "ecommerce", "other",
}
CONTENT_STATES = {"ready", "partial", "missing"}
DEVICE_PRIORITIES = {"mobile", "responsive", "desktop"}
DOMAIN_STATES = {"owned", "needs-purchase", "platform-subdomain", "undecided"}
DATA_FLAGS = (
    "accounts", "persistent_records", "shared_data", "submissions",
    "file_uploads", "payments",
)
SECRET_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey", "private_key")


def template():
    return {
        "project_name": "",
        "goal": "",
        "audience": [],
        "primary_action": "",
        "site_type": "marketing",
        "must_ship": [],
        "out_of_scope": [],
        "content_readiness": "missing",
        "device_priority": "responsive",
        "languages": ["zh-CN"],
        "brand": {"direction": "", "assets_ready": False},
        "data": {key: False for key in DATA_FLAGS},
        "integrations": [],
        "domain": {"desired": "", "status": "undecided"},
        "launch_requested": False,
        "constraints": {"budget": "", "timeline": "", "assumptions": []},
    }


def is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(is_nonempty_string(item) for item in value)


def scan_secret_keys(value, path="$"):
    hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(word in lowered for word in SECRET_WORDS):
                hits.append(f"{path}.{key}")
            hits.extend(scan_secret_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scan_secret_keys(child, f"{path}[{index}]"))
    return hits


def recommend(data):
    flags = data.get("data", {})
    if not isinstance(flags, dict):
        return "invalid", []
    if flags.get("payments"):
        return "capability-review-required", [
            "支付涉及平台能力、商户资质、合规和真实交易验证；先审查，不伪造支付闭环。"
        ]
    if any(flags.get(key) for key in ("accounts", "persistent_records", "shared_data", "submissions", "file_uploads")):
        if flags.get("file_uploads"):
            return "full-stack-with-object-storage", [
                "存在服务端数据或文件需求，需要真实后端、数据库元数据和对象存储。"
            ]
        return "full-stack", ["存在登录、持久化、共享或真实提交需求，需要真实后端与数据库。"]
    return "frontend-only", ["未发现服务端数据需求；若使用浏览器本地存储，须披露其局限。"]


def validate(brief):
    errors = []
    warnings = []
    if not isinstance(brief, dict):
        return ["root must be a JSON object"], warnings, "invalid", []

    for field in ("project_name", "goal", "primary_action"):
        if not is_nonempty_string(brief.get(field)):
            errors.append(f"{field}: non-empty string required")
    for field in ("audience", "must_ship"):
        value = brief.get(field)
        if not string_list(value) or not value:
            errors.append(f"{field}: non-empty array of non-empty strings required")

    if brief.get("site_type") not in SITE_TYPES:
        errors.append(f"site_type: expected one of {sorted(SITE_TYPES)}")
    if brief.get("content_readiness") not in CONTENT_STATES:
        errors.append(f"content_readiness: expected one of {sorted(CONTENT_STATES)}")
    if brief.get("device_priority") not in DEVICE_PRIORITIES:
        errors.append(f"device_priority: expected one of {sorted(DEVICE_PRIORITIES)}")

    data = brief.get("data")
    if not isinstance(data, dict):
        errors.append("data: object required")
        data = {}
    for key in DATA_FLAGS:
        if not isinstance(data.get(key), bool):
            errors.append(f"data.{key}: boolean required")

    domain = brief.get("domain")
    if not isinstance(domain, dict):
        errors.append("domain: object required")
        domain = {}
    if domain.get("status") not in DOMAIN_STATES:
        errors.append(f"domain.status: expected one of {sorted(DOMAIN_STATES)}")
    if not isinstance(domain.get("desired", ""), str):
        errors.append("domain.desired: string required")
    if not isinstance(brief.get("launch_requested"), bool):
        errors.append("launch_requested: boolean required")

    for field in ("out_of_scope", "languages", "integrations"):
        if field in brief and not string_list(brief[field]):
            errors.append(f"{field}: array of non-empty strings required")

    secret_hits = scan_secret_keys(brief)
    if secret_hits:
        errors.append(f"secret-like fields are forbidden in brief: {secret_hits}")

    if brief.get("content_readiness") == "missing":
        warnings.append("内容尚未就绪：使用明确标注的结构样例，不得虚构事实、评价或资质。")
    if brief.get("launch_requested") and domain.get("status") in (None, "undecided"):
        warnings.append("请求发布但域名策略未定：先区分平台预览、部署地址和自定义域名。")
    if domain.get("status") == "needs-purchase":
        warnings.append("域名购买属于外部付费动作：核查可用性并取得明确授权后再执行。")
    if data.get("file_uploads") and not data.get("persistent_records"):
        warnings.append("文件上传通常还需数据库保存元数据；复核 persistent_records 是否应为 true。")
    if brief.get("site_type") in {"saas", "dashboard", "community", "ecommerce"}:
        route_for_warning, _ = recommend(brief)
        if route_for_warning == "frontend-only":
            warnings.append("该站点类型常需后端；若本轮仅做介绍页可保持前端路线，否则复核数据需求是否漏填。")

    route, reasons = recommend(brief)
    return errors, warnings, route, reasons


def cmd_init(args):
    output = Path(args.output)
    if output.exists() and not args.force:
        print(json.dumps({"ok": False, "error": f"refusing to overwrite: {output}"}, ensure_ascii=False))
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(template(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "next": f"python3 {Path(__file__).resolve()} check {output}"}, ensure_ascii=False))
    return 0


def cmd_check(args):
    try:
        brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    errors, warnings, route, reasons = validate(brief)
    report = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "recommended_route": route,
        "route_reasons": reasons,
        "note": "推荐路线仍需结合实际平台能力、用户约束和官方文档复核。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="write a blank brief template")
    init_parser.add_argument("--output", required=True)
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=cmd_init)
    check_parser = subparsers.add_parser("check", help="validate a brief and recommend architecture")
    check_parser.add_argument("brief")
    check_parser.set_defaults(func=cmd_check)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
