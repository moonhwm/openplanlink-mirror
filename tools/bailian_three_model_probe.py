#!/usr/bin/env python3
# bailian_three_model_probe.py v1.0 — 百炼三模型强制调用实测（世界模型/决策模型/向量编码与重排序）
# 纪律：凭据只从 a2a-bridge/.env 读（源码零字面量、输出零回显）；HTTP 仅 https 且 host 白名单；
#       拒环回/私有/保留地址；每探针记状态码、时延、模型名与截断输出，不作成败之外的推断。
# 用法：python burn/scripts/bailian_three_model_probe.py [--probe-text "…"]
import argparse, ipaddress, json, os, socket, sys, time, urllib.error, urllib.request
from pathlib import Path

ALLOW_HOSTS = {'dashscope.aliyuncs.com'}
ENV_FILE = Path('a2a-bridge/.env')
COMPAT = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
NATIVE = 'https://dashscope.aliyuncs.com/api/v1'


def load_key(name):
    """只从 .env / 环境变量取键；返回值绝不打印。"""
    v = os.environ.get(name)
    if v:
        return v
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
            s = line.strip()
            if s.startswith(name + '='):
                return s.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def guard_url(url):
    """host 白名单 + 拒环回/私有/保留；仅 https。"""
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme != 'https':
        raise ValueError('scheme not https: %s' % p.scheme)
    if p.hostname not in ALLOW_HOSTS:
        raise ValueError('host not allowed: %s' % p.hostname)
    for info in socket.getaddrinfo(p.hostname, p.port or 443):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_link_local:
            raise ValueError('resolved to blocked address family')
    return url


def post(url, key, payload, timeout=60):
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(guard_url(url), data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + key)
    req.add_header('Content-Type', 'application/json')
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            return {'status': r.status, 'ms': round((time.perf_counter() - t0) * 1000, 1), 'body': raw}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'ms': round((time.perf_counter() - t0) * 1000, 1),
                'body': e.read().decode('utf-8', 'replace')[:400]}
    except Exception as e:
        return {'status': None, 'ms': round((time.perf_counter() - t0) * 1000, 1), 'body': '%s: %s' % (type(e).__name__, e)}


def clip(s, n=220):
    s = str(s).replace('\n', ' ')
    return s[:n] + ('…' if len(s) > n else '')


def probe_embedding(key, text):
    # 型号实测口径（2026-10-09）：text-embedding-v3 → 400 AllocationQuota.FreeTierOnly（免费额度耗尽+控制台「仅用免费额度」模式）；
    # v4/v2/v1 均 200。故默认走 v4（1024 维），并把 v3 之墙如实记入 --variants 扫描结果，不改判为「不可用」。
    r = post(COMPAT + '/embeddings', key, {'model': 'text-embedding-v4', 'input': text, 'dimensions': 1024})
    out = {'probe': '向量编码 text-embedding-v4', 'status': r['status'], 'ms': r['ms']}
    if r['status'] == 200:
        d = json.loads(r['body'])
        vec = (d.get('data') or [{}])[0].get('embedding') or []
        out.update({'dim': len(vec), 'head4': [round(x, 6) for x in vec[:4]], 'usage': d.get('usage')})
    else:
        out['err'] = clip(r['body'])
    return out


def probe_rerank(key, query, docs):
    # 型号实测口径（2026-10-09）：gte-rerank（v1）→ 403 AccessDenied（该型号未授权）；gte-rerank-v2 → 200；
    # gte-rerank-hybrid / Qwen3-Reranker-0.6B → 400 Model not exist。故默认走 v2，不据 v1 之 403 判「重排序不可用」。
    r = post(NATIVE + '/services/rerank/text-rerank/text-rerank', key,
             {'model': 'gte-rerank-v2', 'input': {'query': query, 'documents': docs},
              'parameters': {'return_documents': False, 'top_n': len(docs)}})
    out = {'probe': '重排序 gte-rerank-v2', 'status': r['status'], 'ms': r['ms']}
    if r['status'] == 200:
        d = json.loads(r['body'])
        res = (d.get('output') or {}).get('results') or []
        out['ranking'] = [{'index': x.get('index'), 'score': round(float(x.get('relevance_score', 0)), 4)} for x in res]
    else:
        out['err'] = clip(r['body'])
    return out


def probe_decision(key, text):
    """决策模型近似：单次前向、结构化输出（分类 + 是非 + 评分 + 概率分布与置信度）。"""
    sysp = ('你是结构化决策器。只输出一个 JSON 对象，字段固定为：'
            '{"label":"通过|复核|否决","yes_no":true|false,"score_0_100":整数,'
            '"probabilities":{"通过":0-1,"复核":0-1,"否决":0-1},"confidence":0-1,"reason":"不超过30字"}。'
            '概率三项之和为 1。不输出任何其它文本。')
    r = post(COMPAT + '/chat/completions', key,
             {'model': 'qwen-plus', 'messages': [{'role': 'system', 'content': sysp},
                                                  {'role': 'user', 'content': text}],
              'temperature': 0, 'response_format': {'type': 'json_object'}}, timeout=90)
    out = {'probe': '决策模型（qwen-plus 单次前向结构化输出，近似口径）', 'status': r['status'], 'ms': r['ms']}
    if r['status'] == 200:
        d = json.loads(r['body'])
        content = ((d.get('choices') or [{}])[0].get('message') or {}).get('content')
        out['parsed'] = clip(content, 300)
        out['usage'] = d.get('usage')
    else:
        out['err'] = clip(r['body'])
    return out


def probe_world(key, text):
    """世界模型：先探是否存在专用端点（诚实记录 404/400），再以对话模型近似「角色演绎/实时导演」两模式。"""
    out = {'probe': '世界模型（开放式世界模型：世界探索/实时导演/角色演绎）'}
    r0 = post(NATIVE + '/services/worldmodel/generation/generation', key, {'model': 'world-model', 'input': {'prompt': text}})
    out['专用端点探测'] = {'path': '/services/worldmodel/generation/generation', 'status': r0['status'], 'ms': r0['ms'], 'resp': clip(r0['body'], 160)}
    sysp = ('你运行在「实时导演 + 角色演绎」模式：给定一段场景文本，输出 JSON：'
            '{"scene_state":"当前世界状态一句话","next_beats":["接下来三个可能事件"],"role_lines":{"角色A":"一句台词"},'
            '"director_note":"导演提示一句话"}。不输出其它文本。')
    r1 = post(COMPAT + '/chat/completions', key,
              {'model': 'qwen-max', 'messages': [{'role': 'system', 'content': sysp}, {'role': 'user', 'content': text}],
               'temperature': 0.7, 'response_format': {'type': 'json_object'}}, timeout=120)
    out['近似实现'] = {'model': 'qwen-max', 'status': r1['status'], 'ms': r1['ms']}
    if r1['status'] == 200:
        d = json.loads(r1['body'])
        out['近似实现']['parsed'] = clip(((d.get('choices') or [{}])[0].get('message') or {}).get('content'), 320)
        out['近似实现']['usage'] = d.get('usage')
    else:
        out['近似实现']['err'] = clip(r1['body'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe-text', default='A2A 治理网络提交一份后量子加密体系升级方案，含分层密钥派生与不可篡改审计链，候主权人终审。')
    ap.add_argument('--skip-world', action='store_true')
    a = ap.parse_args()
    key = load_key('DASHSCOPE_API_KEY')
    if not key:
        print(json.dumps({'fatal': 'DASHSCOPE_API_KEY 未注入（.env 与环境变量均无）'}, ensure_ascii=False))
        return 2
    print(json.dumps({'key_present': True, 'key_len': len(key), 'note': '键值零回显'}, ensure_ascii=False))
    res = [probe_embedding(key, a.probe_text),
           probe_rerank(key, '后量子加密与密钥轮换',
                        ['HMAC-SHA3-512 树与分层密钥派生、动态轮换方案。', '桌面快捷方式清单与 .lnk 文件盘点。',
                          'AES-256-GCM 载荷加密与每消息唯一 nonce。']),
           probe_decision(key, a.probe_text)]
    if not a.skip_world:
        res.append(probe_world(key, '场景：多席位治理网络在夜间峰谷窗集结，需决定下一轮算力分配。'))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
