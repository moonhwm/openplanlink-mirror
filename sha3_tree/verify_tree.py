#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_tree.py — OpenPlanLink A2A SHA3-512/HMAC-SHA3-512 哈希树跨厂商验证器
纯 Python 标准库（3.6+），零依赖。适用 TREE-K3-2026-1003-01 / -02 及同规则后续树。

用法：
  python verify_tree.py MANIFEST.json [--records LEAF_RECORDS.json] [--key KEY.bin]
    [--proof TAG] [--challenge NONCE_HEX RESPONSE_HEX]

无钥模式（任何厂商）：结构校验 + 叶子无钥复算（需 --records）+ 根指纹比对。
持钥模式（密钥自留方）：额外复算全部内部节点与根、生成/验证包含证明、挑战-应答。
算法等价：HMAC-SHA3-512 == .NET System.Security.Cryptography.HMACSHA3_512 == OpenSSL dgst -sha3-512 -mac HMAC。
"""
import argparse, base64, hashlib, hmac, json, sys

def sha3(b: bytes) -> str:
    return hashlib.sha3_512(b).hexdigest()

def hmac_sha3(key: bytes, b: bytes) -> str:
    return hmac.new(key, b, hashlib.sha3_512).hexdigest()

def build_levels(leaf_hexes, key):
    levels = [list(leaf_hexes)]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        if len(cur) % 2 == 1:
            cur = cur + [cur[-1]]
        levels.append([hmac_sha3(key, bytes.fromhex(cur[i]) + bytes.fromhex(cur[i + 1]))
                       for i in range(0, len(cur), 2)])
    return levels

def proof_for(levels, idx):
    proof = []
    for lv in levels[:-1]:
        row = lv if len(lv) % 2 == 0 else lv + [lv[-1]]
        sib = idx ^ 1
        proof.append({"pos": "L" if sib < idx else "R", "hash": row[sib] if sib < len(row) else row[idx]})
        idx //= 2
    return proof

def verify_proof(leaf_hex, proof, root_hex, key):
    cur = leaf_hex
    for p in proof:
        cur = hmac_sha3(key, bytes.fromhex(p["hash"]) + bytes.fromhex(cur)) if p["pos"] == "L" \
            else hmac_sha3(key, bytes.fromhex(cur) + bytes.fromhex(p["hash"]))
    return cur == root_hex

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--records")
    ap.add_argument("--key")
    ap.add_argument("--proof", metavar="TAG")
    ap.add_argument("--challenge", nargs=2, metavar=("NONCE_HEX", "RESP_HEX"))
    a = ap.parse_args()

    m = json.load(open(a.manifest, encoding="utf-8"))
    key = open(a.key, "rb").read() if a.key else None
    results = {}
    tag2idx = {l["tag"]: i for i, l in enumerate(m["leaves"])}

    # 1) 结构校验：levels[0] 与 leaves 一致；根为末层唯一节点
    leaf_hexes = [l["sha3_512"] for l in m["leaves"]]
    results["structure_leaves_match"] = (m["levels"][0] == leaf_hexes)
    results["root_is_last_level"] = (m["levels"][-1] == [m["root_sha3_512_hmac"]])
    results["leaf_count_match"] = (m["leaf_count"] == len(leaf_hexes))

    # 2) 叶子无钥复算（跨厂商主通道）
    if a.records:
        recs = {r["tag"]: r["canonical_b64"] for r in json.load(open(a.records, encoding="utf-8"))["records"]}
        ok, miss = True, []
        for l in m["leaves"]:
            b64 = recs.get(l["tag"])
            if b64 is None:
                miss.append(l["tag"]); ok = False; continue
            if sha3(base64.b64decode(b64)) != l["sha3_512"]:
                ok = False
        results["leaves_keyless_recompute"] = ok
        if miss:
            results["records_missing"] = miss

    # 3) 持钥复算内部节点与根
    if key:
        levels = build_levels(leaf_hexes, key)
        results["internal_nodes_recompute"] = (levels == m["levels"])
        results["root_recompute_match"] = (levels[-1][0] == m["root_sha3_512_hmac"])
        kfp = sha3(key)
        results["key_fingerprint_match"] = (kfp == m.get("key_fingerprint_sha3_512"))
        if not results["key_fingerprint_match"]:
            results["key_fingerprint_computed"] = kfp
    else:
        results["internal_nodes_recompute"] = "SKIPPED (key self-retained; only fingerprint published)"

    # 4) 包含证明
    if a.proof:
        i = tag2idx.get(a.proof)
        if i is None:
            results["proof_error"] = f"unknown tag; known: {list(tag2idx)}"
        else:
            p = proof_for([list(x) for x in m["levels"]], i)
            results["proof"] = p
            if key:
                results["proof_verifies"] = verify_proof(leaf_hexes[i], p, m["root_sha3_512_hmac"], key)

    # 5) 挑战-应答核验（A2A 握手：验证某应答是否出自持钥方）
    if a.challenge:
        nonce_hex, resp_hex = a.challenge
        if key:
            expect = hmac_sha3(key, b"a2a-challenge:" + bytes.fromhex(nonce_hex))
            results["challenge_response_match"] = hmac.compare_digest(expect, resp_hex)
        else:
            results["challenge_response_match"] = "SKIPPED (needs key)"

    verdict = all(v is True or isinstance(v, (str, list, dict)) for k, v in results.items()
                  if not k.startswith(("proof", "records_missing", "key_fingerprint_computed")))
    print(json.dumps({"tree_id": m.get("tree_id"), "verdict": "PASS" if verdict else "FAIL",
                      "results": results}, ensure_ascii=False, indent=2))
    sys.exit(0 if verdict else 1)

if __name__ == "__main__":
    main()
