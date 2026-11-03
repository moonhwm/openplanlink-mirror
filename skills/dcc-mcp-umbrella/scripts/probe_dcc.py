#!/usr/bin/env python3
"""dcc-mcp-umbrella 统一探活脚本（stdlib only）。

用法：
  probe_dcc.py --registry                      # 打印七线注册表（域/授权/状态基线）
  probe_dcc.py --url <mcp_endpoint> [--token-env ENV_NAME]
                                               # 远端 MCP 探活：initialize + tools/list + 401 挑战解析
  probe_dcc.py --from-list <file>              # 会话工具清单分组：读文本里的工具名，按前缀归线
  probe_dcc.py --self-test                     # 自测

纪律：token 只从环境变量读，永不打印其值；输出只含状态与工具清单。
"""
import json, os, re, sys, urllib.request, urllib.error

REGISTRY = {
    "maya":       {"domain": "mesh/animation", "kind": "plugin-mcp", "tool_prefix": "mcp__plugin-",
                   "server": "maya", "auth": "插件安装+本地常驻服务",
                   "baseline": "已见注册；服务器断连时不可用，需重连/重授权"},
    "3dsmax":     {"domain": "mesh/animation", "kind": "plugin-or-local-mcp", "tool_prefix": "mcp__plugin-",
                   "server": None, "auth": "同 DCC 规程", "baseline": "未见注册（预留位）"},
    "blender":    {"domain": "mesh/animation", "kind": "community-mcp", "tool_prefix": None,
                   "server": "blender", "auth": "本地插件+Socket（以实际部署为准）",
                   "baseline": "未见注册（预留位）"},
    "rodin":      {"domain": "mesh/animation", "kind": "remote-mcp",
                   "url": "https://api.hyper3d.com/api/mcp", "tool_prefix": "rodin_",
                   "auth": "OAuth 浏览器授权（PKCE S256，scopes: rodin:generate rodin:read）",
                   "baseline": "7 件 rodin_* 工具已实测（2026-09-23 基线）"},
    "tripo":      {"domain": "mesh/animation", "kind": "plugin-mcp", "tool_prefix": "tripo_",
                   "auth": "TRIPO_API_KEY 环境变量", "baseline": "24 件 tripo_* 工具在册"},
    "solidworks": {"domain": "parametric/engineering", "kind": "reserved", "tool_prefix": None,
                   "auth": "以实际部署为准", "baseline": "未见注册；未见知名官方 MCP（预留位）"},
    "cad":        {"domain": "parametric/engineering", "kind": "reserved", "tool_prefix": None,
                   "auth": "以实际部署为准", "baseline": "未见注册；未见知名官方 MCP（预留位）"},
}

JSONRPC_INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                           "clientInfo": {"name": "dcc-umbrella-probe", "version": "1.0.0"}}}
JSONRPC_TOOLS = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def _post(url, payload, token=None, timeout=20):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            # Streamable HTTP 可能回 SSE；取最后一个 data: JSON
            if raw.lstrip().startswith("event:") or "\ndata:" in raw or raw.lstrip().startswith("data:"):
                datas = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")]
                raw = datas[-1] if datas else "{}"
            return r.status, dict(r.headers), json.loads(raw)
    except urllib.error.HTTPError as e:
        hdrs = dict(e.headers)
        try:
            return e.code, hdrs, json.loads(e.read().decode("utf-8", "replace") or "{}")
        except Exception:
            return e.code, hdrs, {}
    except Exception as e:
        return None, {}, {"error": f"{type(e).__name__}: {e}"}


def probe_remote(url, token_env=None):
    token = os.environ.get(token_env) if token_env else None
    out = {"url": url, "token_env_used": bool(token_env), "token_present": bool(token)}
    st, hdrs, init = _post(url, JSONRPC_INIT, token)
    out["initialize_status"] = st
    out["endpoint_ok"] = st == 200
    if st in (401, 403):
        out["auth_challenge"] = hdrs.get("WWW-Authenticate") or hdrs.get("www-authenticate")
        out["initialize_body"] = init
        return out
    if isinstance(init, dict) and init.get("result"):
        out["serverInfo"] = init["result"].get("serverInfo")
        out["protocolVersion"] = init["result"].get("protocolVersion")
    st2, _, tools = _post(url, JSONRPC_TOOLS, token)
    out["tools_status"] = st2
    if isinstance(tools, dict) and isinstance(tools.get("result"), dict):
        out["tools"] = sorted(t["name"] for t in tools["result"].get("tools", []))
    return out


def from_list(path):
    text = open(path, encoding="utf-8").read()
    names = sorted(set(re.findall(r"(?:mcp__plugin-[\w-]+_[\w-]+__|rodin_|tripo_)[A-Za-z0-9_]+", text)))
    groups = {}
    for n in names:
        line = ("rodin" if n.startswith("rodin_") else
                "tripo" if n.startswith("tripo_") else
                re.sub(r"^mcp__plugin-[\w-]+?_([\w-]+?)__.*$", r"\1", n))
        groups.setdefault(line, []).append(n)
    return {"source": path, "lines_found": groups,
            "unmatched_note": "未匹配前缀的工具名不归属任何已注册线，需人工核对"}


def self_test():
    assert REGISTRY["rodin"]["url"].startswith("https://")
    assert len(REGISTRY) == 7
    tmp = "/tmp/_dcc_probe_selftest.txt"
    open(tmp, "w").write("mcp__plugin-autodesk-maya_maya__scene_query tripo_convert rodin_generate")
    r = from_list(tmp)
    assert r["lines_found"]["maya"] and r["lines_found"]["tripo"] and r["lines_found"]["rodin"]
    return {"self_test": "ok"}


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--self-test" in args:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
    elif "--registry" in args:
        print(json.dumps(REGISTRY, ensure_ascii=False, indent=2))
    elif "--from-list" in args:
        print(json.dumps(from_list(args[args.index("--from-list") + 1]), ensure_ascii=False, indent=2))
    elif "--url" in args:
        url = args[args.index("--url") + 1]
        env = args[args.index("--token-env") + 1] if "--token-env" in args else None
        print(json.dumps(probe_remote(url, env), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
        sys.exit(64)
