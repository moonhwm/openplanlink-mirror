#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bounded heterogeneous routes. ID OPL-HETERO-20261009-01.
Author codex-review-20261005. Secrets stay in the existing managed env file.
Running this module reports key availability and never invokes inference.
"""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

KEY_FILE = str(Path.home() / '.hetero-model-keys.env')

PLATFORMS = {
    "siliconflow": {"base": "https://api.siliconflow.cn/v1", "key_env": "SILICONFLOW_KEY", "role": "硅基流动通路"},
    "302.ai": {"base": "https://api.302ai.cn/v1", "key_env": "AI302_KEY", "role": "非国内型号须逐项核验"},
    "national-supercomputing": {"base": "https://api.scnet.cn/api/llm/v1", "key_env": "SCNET_KEY", "role": "国家超算互联网通路"},
}
MAX_RESPONSE_BYTES = 2_000_000
MODEL_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_./:+-]{0,159}\Z')
FOREIGN_FAMILY = re.compile(r'(?i)^(?:openai/|anthropic/|google/|xai/)?(?:gpt-|claude-|gemini-|grok-|o[134](?:-|$))')
DOMESTIC_NAMES = re.compile(r'qwen|deepseek|glm|kimi|moonshot|hunyuan|doubao|minimax|baidu|ernie|stepfun', re.I)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _load_keys():
    keys = {}
    if os.path.exists(KEY_FILE):
        for line in open(KEY_FILE, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                value = v.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                keys[k.strip()] = value
    return keys


def _key(name):
    return _load_keys().get(name, "")


def _route(base, key_env):
    for provider, config in PLATFORMS.items():
        if base == config['base'] and key_env == config['key_env']:
            return provider
    raise ValueError('unapproved_endpoint_or_credential_binding')

def _safe_model(model):
    return isinstance(model, str) and bool(MODEL_ID.fullmatch(model)) and not re.search(r'sk-|ghp_|github_pat_', model, re.I)

def _request(provider, path, payload=None):
    config = PLATFORMS[provider]
    key = _key(config['key_env'])
    if not key:
        return {'error': 'credential_missing', 'provider': provider}
    req = urllib.request.Request(config['base'] + path,
        data=None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return {'error': 'response_limit', 'provider': provider}
        value = json.loads(raw)
        if not isinstance(value, dict):
            return {'error': 'response_shape_unverified', 'provider': provider}
        if 'error' in value:
            return {'error': 'provider_rejected', 'provider': provider}
        return value
    except urllib.error.HTTPError as error:
        return {'error': 'http_rejected', 'http_status': error.code, 'provider': provider}
    except Exception as e:
        return {'error': 'request_failed', 'error_type': type(e).__name__, 'provider': provider}

def catalog(provider):
    """Authenticated GET of safe model IDs; no inference or fee claim."""
    if provider not in PLATFORMS:
        return {'error': 'unknown_provider'}
    value = _request(provider, '/models')
    if 'error' in value:
        return value
    if not isinstance(value.get('data'), list):
        return {'error': 'response_shape_unverified', 'provider': provider}
    models = sorted({x['id'] for x in value['data'] if isinstance(x, dict) and _safe_model(x.get('id'))})
    return {'provider': provider, 'models': models, 'model_count': len(models),
            'authenticated_catalog_read': True, 'inference_verified': False}

def chat(model, prompt, base="https://api.siliconflow.cn/v1", key_env="SILICONFLOW_KEY", max_tokens=64,
         *, verified_foreign_models=()):
    """Bounded chat; caller retains resource/fee approval responsibility.
    302 requires an explicit reviewed non-domestic model set. A family name
    alone does not establish backend identity or performance.
    """
    try:
        provider = _route(base, key_env)
    except ValueError:
        return {'error': 'unapproved_endpoint_or_credential_binding'}
    if not _safe_model(model):
        return {'error': 'invalid_model_id'}
    if provider == '302.ai' and (not isinstance(verified_foreign_models, (tuple, list, set, frozenset))
                                or not FOREIGN_FAMILY.match(model) or DOMESTIC_NAMES.search(model)
                                or model not in verified_foreign_models):
        return {'error': '302_foreign_model_not_verified', 'provider': provider}
    if not isinstance(prompt, str) or not prompt or len(prompt.encode('utf-8')) > 1_000_000:
        return {'error': 'invalid_prompt'}
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 4096:
        return {'error': 'invalid_output_limit'}
    value = _request(provider, '/chat/completions', {'model': model,
        'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': max_tokens})
    if 'error' in value:
        return value
    try:
        content = value['choices'][0]['message']['content']
        response_model = value.get('model')
        if provider == '302.ai' and (not _safe_model(response_model) or not FOREIGN_FAMILY.match(response_model)
                                    or DOMESTIC_NAMES.search(response_model) or response_model not in verified_foreign_models):
            return {'error': '302_response_identity_unverified', 'provider': provider}
        if not isinstance(content, str) or (response_model is not None and not _safe_model(response_model)):
            raise ValueError('invalid_content_or_response_model')
        tokens = value.get('usage', {}).get('total_tokens')
        if tokens is not None and (isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0):
            raise ValueError('invalid_usage')
        return {'model': response_model, 'content': content, 'tokens': tokens, 'provider': provider}
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return {'error': 'response_shape_unverified', 'provider': provider}


def status():
    """三平台 key 状态（只报有无 key、不报 key 值）。"""
    keys = _load_keys()
    return {p: {'has_key': bool(keys.get(c['key_env'])), 'role': c['role'],
                'authentication_verified': False} for p, c in PLATFORMS.items()}


if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False))
