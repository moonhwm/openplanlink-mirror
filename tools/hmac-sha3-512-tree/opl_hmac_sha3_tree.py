# -*- coding: utf-8 -*-
"""opl_hmac_sha3_tree.py — HMAC-SHA3-512 键控哈希树（密钥自留）＋无钥伴生根（人人可验）。

依据标准：System.Security.Cryptography.HmacSha3_512（.NET）＝ RFC 2104 HMAC 以 SHA3-512 为内核。
本件用 Python 标准库 hmac + hashlib.sha3_512 实现同一构造，不引入第三方依赖，
以便任何厂商的 Agent 用任意语言复算（跨应用、跨厂商核验的前提是"只依赖公开标准"）。

为什么要两根而不是一根：
  - 无钥伴生根（plain SHA3-512 Merkle）：任何人都能复算 ⇒ 证"内容没被改"（完整性）。
  - 键控根（HMAC-SHA3-512 Merkle）：只有持钥者能造出合法树 ⇒ 证"这棵树是我方产的"（真伪性）。
  只发第一根，别人能验内容但谁都能伪造一棵同样自洽的树；只发第二根，别人拿到也验不了。
  两根同发、密钥自留，才同时满足"可核验"与"不可伪造"。

密钥纪律（红线）：
  - 密钥只存本机 keystore，**绝不**写入任何外发件、产物、日志、提交、报告。
  - 产物里只出现 kid（密钥的一次性摘要标识，SHA3-512(domain||key)[:16]），单向、不可逆推。
  - keystore 目录名含"敏感"，被我方出域形态门按路径形状直接拒出（结构性防线，不靠自觉）。

域分隔（防跨协议伪造）：叶、内节点、kid 各带独立标签，且拼接一律显式长度前缀，
避免 "ab"+"c" 与 "a"+"bc" 撞成同一输入（长度扩展/拼接歧义类攻击）。

奇数叶处理：**提升**（promote，单节点直接上移），绝不复制自身。
复制会让两棵不同形状的树得到同一个根（CVE-2012-2459 类），本件在 selftest 里
用"提升 vs 复制"两棵树根必须不同来把这条钉死。

用法：
  python opl_hmac_sha3_tree.py build   --root DIR [--git-tracked] [--out DIR]
  python opl_hmac_sha3_tree.py verify  --tree FILE [--key KEYFILE]
  python opl_hmac_sha3_tree.py prove   --tree FILE --path RELPATH [--key KEYFILE]
  python opl_hmac_sha3_tree.py selftest
退出码即判决：0=通过，1=判不过，2=用法/环境错误。
"""
import argparse
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CST = timezone(timedelta(hours=8))
ALGO = "HMAC-SHA3-512(RFC2104+FIPS202) / companion SHA3-512"
TAG_LEAF_K = b"OPL-A2A-HMACLEAF-v1"
TAG_LEAF_P = b"OPL-A2A-PLAINLEAF-v1"
TAG_NODE_K = b"OPL-A2A-HMACNODE-v1"
TAG_NODE_P = b"OPL-A2A-PLAINNODE-v1"
TAG_KID = b"OPL-A2A-KID-v1"
KEY_BYTES = 64          # SHA3-512 分组长度＝144B，块内取值；64B 随机熵足够且便于人工核对形态
HEXLEN = 128            # sha3_512 摘要十六进制长度
DEFAULT_KEYSTORE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_敏感_加密存储", "opl_hmac_keystore")
KEYNAME = "opl_a2a_tree.key"


# ---------------------------------------------------------------- 基本原语
def lp(b):
    """显式长度前缀：把拼接歧义消掉。"""
    if isinstance(b, str):
        b = b.encode("utf-8")
    return b"%d:" % len(b) + b


def sha3(b):
    return hashlib.sha3_512(b).hexdigest()


def hkey(key, tag, payload):
    return hmac.new(key, tag + payload, hashlib.sha3_512).hexdigest()


def kid_of(key):
    """密钥标识：单向摘要，可公开发；不可逆推密钥。"""
    return sha3(TAG_KID + lp(key))[:16]


def fp16(path):
    """文件内容指纹（sha3_512 截 16 位）——与本席四件套口径一致。"""
    h = hashlib.sha3_512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- 叶与树
def leaf_payload(relpath, fp, size):
    """叶输入＝路径(仓库相对, UTF-8)＋内容指纹＋字节数。路径用相对形，产物可外发不含本机真名。"""
    return lp(relpath) + lp(fp) + lp(str(size))


def leaf_pair(key, relpath, fp, size):
    p = leaf_payload(relpath, fp, size)
    return hkey(key, TAG_LEAF_K, p), sha3(TAG_LEAF_P + p)


def fold(hexes, key, tag_node):
    """自底向上折叠；奇数**提升**，绝不复制。返回 (root, levels)。"""
    if not hexes:
        # 空集不是"零承诺"洗成通过的地方：显式返回空根标记，调用方必须判它。
        return None, []
    levels = [list(hexes)]
    cur = list(hexes)
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(hkey(key, tag_node, lp(cur[i]) + lp(cur[i + 1])) if key
                       else sha3(tag_node + lp(cur[i]) + lp(cur[i + 1])))
        if len(cur) % 2 == 1:
            nxt.append(cur[-1])          # promote：单节点原样上移
        levels.append(nxt)
        cur = nxt
    return cur[0], levels


def build_tree(key, items):
    """items: [(relpath, fp16, size)] 已排序。返回带双根的树字典。"""
    items = sorted(items, key=lambda t: t[0])
    kl, pl, meta = [], [], []
    for rel, fp, size in items:
        k, p = leaf_pair(key, rel, fp, size)
        kl.append(k)
        pl.append(p)
        meta.append({"path": rel, "fp_sha3_512_16": fp, "size": size,
                     "leaf_hmac": k, "leaf_plain": p})
    kroot, klevels = fold(kl, key, TAG_NODE_K)
    proot, _ = fold(pl, None, TAG_NODE_P)
    return {
        "standard": ALGO,
        "kid": kid_of(key),
        "key_retained_locally": True,
        "key_value_published": False,
        "domain_tags": {"leaf_keyed": TAG_LEAF_K.decode(), "leaf_plain": TAG_LEAF_P.decode(),
                        "node_keyed": TAG_NODE_K.decode(), "node_plain": TAG_NODE_P.decode(),
                        "kid": TAG_KID.decode()},
        "leaf_formula": "HMAC_SHA3_512(key, TAG_LEAF || len(path):path || len(fp):fp || len(size):size)",
        "node_formula": "HMAC_SHA3_512(key, TAG_NODE || len(left):left || len(right):right)",
        "odd_leaf_rule": "promote(单节点上移，不复制自身)",
        "keyed_root": kroot,
        "plain_root": proot,
        "leaf_count": len(meta),
        "levels": len(klevels),
        "leaves": meta,
        "built_at": datetime.now(CST).isoformat(timespec="seconds"),
        "empty_set_guard": "leaf_count==0 时两根均为 null，核验方必须判 null，不得当通过",
    }


def recompute(tree, key):
    """从产物里的 leaves 重算双根，与声明值比对。"""
    metas = tree.get("leaves") or []
    if not metas:
        return {"ok": False, "why": "空叶集：null 根不得洗成通过", "leaf_count": 0}
    kl = [m["leaf_hmac"] for m in metas]
    pl = [m["leaf_plain"] for m in metas]
    # 叶自身也要重算，否则"改了叶值但根跟着改"这类自洽伪造查不出来
    leaf_ok = True
    bad_leaves = []
    for m in metas:
        k, p = leaf_pair(key, m["path"], m["fp_sha3_512_16"], m["size"])
        if k != m["leaf_hmac"] or p != m["leaf_plain"]:
            leaf_ok = False
            bad_leaves.append(m["path"])
    kroot, _ = fold(kl, key, TAG_NODE_K)
    proot, _ = fold(pl, None, TAG_NODE_P)
    return {
        "ok": leaf_ok and kroot == tree.get("keyed_root") and proot == tree.get("plain_root"),
        "leaf_recompute_ok": leaf_ok,
        "bad_leaves": bad_leaves[:10],
        "keyed_root_recomputed": kroot,
        "keyed_root_declared": tree.get("keyed_root"),
        "plain_root_recomputed": proot,
        "plain_root_declared": tree.get("plain_root"),
        "kid_recomputed": kid_of(key),
        "kid_declared": tree.get("kid"),
        "leaf_count": len(metas),
    }


def inclusion_proof(tree, relpath, key):
    """单文件包含证明：给持钥第三方，无需整棵树即可验一件。"""
    metas = tree.get("leaves") or []
    idx = next((i for i, m in enumerate(metas) if m["path"] == relpath), None)
    if idx is None:
        return {"ok": False, "why": "路径不在树内", "path": relpath}
    layer = [m["leaf_hmac"] for m in metas]
    leaf_h = metas[idx]["leaf_hmac"]     # idx 会在循环里被折叠，先把叶值留住
    sib = []
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer) - 1, 2):
            sib_pair = (i, i + 1)
            if idx in sib_pair:
                other = sib_pair[0] if idx == sib_pair[1] else sib_pair[1]
                sib.append({"sibling": layer[other], "side": "left" if other < idx else "right"})
            nxt.append(hkey(key, TAG_NODE_K, lp(layer[i]) + lp(layer[i + 1])))
        if len(layer) % 2 == 1:
            if idx == len(layer) - 1:
                sib.append({"sibling": None, "side": "promote"})
            nxt.append(layer[-1])
        idx //= 2
        layer = nxt
    return {"ok": True, "path": relpath, "leaf_hmac": leaf_h,
            "proof": sib, "root": layer[0], "matches_keyed_root": layer[0] == tree.get("keyed_root")}


def verify_proof(tree, relpath, fp, size, proof, key):
    """核验方侧：拿单件证明＋自己的密钥，复算到根。"""
    cur = hkey(key, TAG_LEAF_K, leaf_payload(relpath, fp, size))
    for step in proof:
        s = step.get("sibling")
        if s is None:
            continue                      # promote：本层无兄弟
        a, b = (s, cur) if step["side"] == "left" else (cur, s)
        cur = hkey(key, TAG_NODE_K, lp(a) + lp(b))
    return cur == tree.get("keyed_root"), cur


# ---------------------------------------------------------------- 密钥库
def ensure_key(path=None, create=True):
    """取密钥；不存在则生成（64B 随机）。绝不回显值，只报形态与 kid。"""
    p = path or os.path.join(DEFAULT_KEYSTORE, KEYNAME)
    if os.path.isfile(p):
        with open(p, "rb") as f:
            key = f.read()
        if len(key) != KEY_BYTES:
            raise SystemExit("密钥形态异常：期望 %dB，实得 %dB（%s）" % (KEY_BYTES, len(key), p))
        return key, p, "existing"
    if not create:
        raise SystemExit("密钥不存在且未允许生成：%s" % p)
    key = os.urandom(KEY_BYTES)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key, p, "generated"


# ---------------------------------------------------------------- 采集
def collect_blobs(root, ref="HEAD"):
    """按 **git blob 字节** 采集，而不是按工作树字节。
    为什么必须这样：Windows 上 core.autocrlf=true 且仓库无 .gitattributes 时，
    同一提交在 Windows 工作树里是 CRLF、在 Linux/macOS 工作树里是 LF，
    字节不同 ⇒ fp16 不同 ⇒ 根不同。按工作树出根＝把"我机器的换行设置"写进了存证，
    别的厂商照 README 一跑就 FAIL，还会误判成"内容被改过"。
    blob 字节与 checkout 过滤器无关，才是跨平台唯一可比的对象。"""
    ls = subprocess.run(["git", "-C", root, "ls-tree", "-r", "-z", ref], capture_output=True)
    if ls.returncode != 0:
        raise SystemExit("git ls-tree 失败：%s" % ls.stderr.decode("utf-8", "replace")[:200])
    entries, nonblob = [], []
    for rec in ls.stdout.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        parts = meta.split(b" ")
        if len(parts) >= 3 and parts[1] == b"blob":
            entries.append((path.decode("utf-8"), parts[2].decode("ascii")))
        elif len(parts) >= 3:
            nonblob.append(path.decode("utf-8"))   # 与 collect() 同一套返回契约：缺失是列表不是计数
    if not entries:
        return [], nonblob
    batch = subprocess.Popen(["git", "-C", root, "cat-file", "--batch"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
    stdin = b"".join(s.encode("ascii") + b"\n" for _, s in entries)
    out, _ = batch.communicate(stdin)
    items, pos = [], 0
    for rel, sha in entries:
        nl = out.index(b"\n", pos) if b"\n" in out[pos:] else -1
        if nl < 0:
            nonblob.append(rel)
            break
        header = out[pos:nl].split(b" ")
        pos = nl + 1
        if len(header) >= 3 and header[1] == b"blob":
            n = int(header[2])
            body = out[pos:pos + n]
            pos += n + 1                      # 内容后跟一个换行
            items.append((rel, hashlib.sha3_512(body).hexdigest()[:16], n))
        else:
            nonblob.append(rel)
    return items, nonblob


def collect(root, git_tracked=False):
    root = os.path.abspath(root)
    if git_tracked:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                             capture_output=True)
        if out.returncode != 0:
            raise SystemExit("git ls-files 失败：%s" % out.stderr.decode("utf-8", "replace")[:200])
        # -z：git 默认对非 ASCII 路径做 C-quoting，会整族漏掉中文名文件（E-59）
        rels = [x for x in out.stdout.decode("utf-8").split("\0") if x]
    else:
        rels = []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in (".git", "__pycache__")]
            for fn in fns:
                rels.append(os.path.relpath(os.path.join(dp, fn), root).replace("\\", "/"))
    items, missing = [], []
    for rel in rels:
        ap = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(ap):
            missing.append(rel)
            continue
        items.append((rel, fp16(ap), os.path.getsize(ap)))
    return items, missing


def base_commit(root):
    """把树钉在一个提交上：不写清基线，核验方无从知道这根对应仓库的哪个状态。"""
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                             capture_output=True, timeout=20)
        if out.returncode == 0:
            return out.stdout.decode("ascii", "replace").strip()
    except Exception:
        pass
    return None


def face_from_tree(t, with_leaves=False):
    """紧凑对外面：只留复算所需的最小声明。叶可由"仓库文件＋算法"重算，
    所以发叶＝把 309KB 的冗余搬进库；不发叶＝核验方自己算，且算不出就是内容被人改过。"""
    f = {k: t[k] for k in ("standard", "kid", "key_retained_locally", "key_value_published",
                           "domain_tags", "leaf_formula", "node_formula", "odd_leaf_rule",
                           "keyed_root", "plain_root", "leaf_count", "levels", "built_at",
                           "empty_set_guard", "source_root_alias", "keystore", "selfcheck_after_build")}
    for opt in ("base_commit", "source_root_kind", "seat", "missing_count", "content_source"):
        if opt in t:
            f[opt] = t[opt]
    if with_leaves:
        f["leaves"] = t["leaves"]
    return f


# ---------------------------------------------------------------- 自检
def selftest():
    """合成夹具自检＋阴性对照。每条对照都必须"有牙"：把好的改成坏的，判据必须翻红。"""
    ck = []

    def case(name, cond, detail=""):
        ck.append({"case": name, "pass": bool(cond), "detail": detail})

    key = os.urandom(KEY_BYTES)
    other = os.urandom(KEY_BYTES)
    items = [("a.txt", sha3(b"A")[:16], 10), ("b/c.txt", sha3(b"C")[:16], 20),
             ("b/d.txt", sha3(b"D")[:16], 30), ("e.bin", sha3(b"E")[:16], 40),
             ("中文件.md", sha3("中".encode())[:16], 50)]

    t = build_tree(key, items)
    case("T1 双根非空且异值", t["keyed_root"] and t["plain_root"] and t["keyed_root"] != t["plain_root"],
         "keyed=%s… plain=%s…" % (t["keyed_root"][:12], t["plain_root"][:12]))
    case("T2 同钥重算自洽", recompute(t, key)["ok"])

    r_bad = recompute(t, other)
    case("T3 阴性·换钥必翻红", not r_bad["ok"] and not r_bad["leaf_recompute_ok"],
         "换钥后叶重算失败=%s" % (not r_bad["leaf_recompute_ok"]))

    t2 = json.loads(json.dumps(t))
    t2["leaves"][2]["size"] = 999
    case("T4 阴性·篡改叶必翻红", not recompute(t2, key)["ok"],
         "bad_leaves=%s" % recompute(t2, key)["bad_leaves"])

    t3 = json.loads(json.dumps(t))
    t3["leaves"][0]["leaf_hmac"], t3["leaves"][1]["leaf_hmac"] = \
        t3["leaves"][1]["leaf_hmac"], t3["leaves"][0]["leaf_hmac"]
    case("T5 阴性·换序必翻红", not recompute(t3, key)["ok"], "叶序换了但根没换 ⇒ 必须查出")

    # CVE-2012-2459：奇数叶"复制"与"提升"必须给出不同的根
    odds = [("a", sha3(b"1")[:16], 1), ("b", sha3(b"2")[:16], 2), ("c", sha3(b"3")[:16], 3)]
    layer = [leaf_pair(key, r, f, s)[0] for r, f, s in sorted(odds)]
    promote = fold(layer, key, TAG_NODE_K)[0]
    copied = layer + [layer[-1]]
    dup_root = fold(copied, key, TAG_NODE_K)[0]
    case("T6 阴性·提升≠复制(抗 CVE-2012-2459)", promote != dup_root,
         "promote=%s… duplicate=%s…" % (promote[:12], dup_root[:12]))

    # 域分隔：叶标签与节点标签不得互换后仍自洽
    x = hkey(key, TAG_LEAF_K, lp(b"z"))
    y = hkey(key, TAG_NODE_K, lp(b"z"))
    case("T7 域分隔生效", x != y, "同载荷不同标签 ⇒ 摘要必须不同")

    # 长度前缀：拼接歧义必须被消掉
    case("T8 拼接歧义已消除", lp(b"ab") + lp(b"c") != lp(b"a") + lp(b"bc"))

    # 单件包含证明：正例通过，改一个字节即翻红
    pr = inclusion_proof(t, "b/c.txt", key)
    ok, got = verify_proof(t, "b/c.txt", sha3(b"C")[:16], 20, pr["proof"], key)
    case("T9 单件证明可验", ok and pr["matches_keyed_root"], "root=%s…" % got[:12])
    ok2, _ = verify_proof(t, "b/c.txt", sha3(b"C!")[:16], 20, pr["proof"], key)
    case("T10 阴性·单件证明改内容必翻红", not ok2)

    # 空集守卫：不得把 null 根洗成通过
    te = build_tree(key, [])
    case("T11 空集守卫", te["keyed_root"] is None and not recompute(te, key)["ok"],
         "空集根=null 且核验判不过")

    # kid 稳定性与不可逆推形态
    case("T12 kid 稳定且非密钥本身", kid_of(key) == kid_of(key) and kid_of(key) != key.hex()[:16]
         and len(kid_of(key)) == 16)

    npass = sum(1 for c in ck if c["pass"])
    return {"verdict": "PASS" if npass == len(ck) else "FAIL",
            "passed": npass, "total": len(ck), "cases": ck}


# ---------------------------------------------------------------- 命令
def cmd_build(a):
    key, keypath, origin = ensure_key(a.key, create=not a.no_create_key)
    if a.git_blobs:
        items, missing = collect_blobs(a.root, a.ref or "HEAD")
        csrc = "git_blob(ref=%s)" % (a.ref or "HEAD")
    else:
        items, missing = collect(a.root, git_tracked=a.git_tracked)
        csrc = "worktree_bytes" + ("(git_tracked)" if a.git_tracked else "(fs_walk)")
    if not items:
        print("拒绝出树：采集到 0 件（root=%r git_tracked=%s）——空集不得当通过" % (a.root, a.git_tracked))
        return 2
    t = build_tree(key, items)
    t["source_root_kind"] = "git_blob" if a.git_blobs else ("git_tracked" if a.git_tracked else "filesystem_walk")
    t["content_source"] = csrc
    t["source_root_alias"] = a.root_alias or "SOURCE::"   # 外发件不含本机绝对路径与真名
    t["missing_paths"] = missing[:20]
    t["missing_count"] = len(missing)
    t["seat"] = a.seat
    t["base_commit"] = base_commit(a.root)
    t["keystore"] = {"path_shape": "<workspace>/_敏感_加密存储/opl_hmac_keystore/*.key",
                     "actual_path_published": False, "key_origin": origin,
                     "key_bytes": KEY_BYTES, "note": "密钥自留：位置与形态可述，值绝不外发"}
    rc = recompute(t, key)
    t["selfcheck_after_build"] = {"ok": rc["ok"], "leaf_count": rc["leaf_count"]}
    if not rc["ok"]:
        print("拒绝出件：建完立刻自验不过（%s）" % json.dumps(rc, ensure_ascii=False)[:300])
        return 1
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.now(CST).strftime("%Y%m%d%H%M")
    name = "HMAC_SHA3_512树_%s_%s.json" % (stamp, a.seat)
    p = os.path.join(a.out, name)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=1)
    b = open(p, "rb").read()
    print("树已出：%s" % p)
    print("  件数=%d 层数=%d 缺件=%d" % (t["leaf_count"], t["levels"], t["missing_count"]))
    print("  键控根(HMAC-SHA3-512) = %s" % t["keyed_root"])
    print("  伴生根(plain SHA3-512) = %s" % t["plain_root"])
    print("  kid=%s（密钥自留于 %s，值未外发）" % (t["kid"], t["keystore"]["path_shape"]))
    print("  产物四件套：fp16=%s size=%d" % (sha3(b)[:16], len(b)))
    if a.public_face:
        face = face_from_tree(t)
        with io.open(a.public_face, "w", encoding="utf-8") as f:
            json.dump(face, f, ensure_ascii=False, indent=1, sort_keys=True)
        fb = open(a.public_face, "rb").read()
        print("  对外紧凑面：%s fp16=%s size=%d（不含叶，叶由核验方自算）"
              % (a.public_face, sha3(fb)[:16], len(fb)))
    return 0


def cmd_verify(a):
    with io.open(a.tree, encoding="utf-8") as f:
        t = json.load(f)
    if not t.get("leaves"):
        print("判不过：产物叶集为空（null 根不得当通过）")
        return 1
    if a.keyless:
        # 无钥核验：只能验伴生根（完整性），键控根标"未证"而非"通过"
        pl = [m["leaf_plain"] for m in t["leaves"]]
        leaf_ok = all(sha3(TAG_LEAF_P + leaf_payload(m["path"], m["fp_sha3_512_16"], m["size"]))
                      == m["leaf_plain"] for m in t["leaves"])
        proot, _ = fold(pl, None, TAG_NODE_P)
        ok = leaf_ok and proot == t.get("plain_root")
        print(json.dumps({"mode": "keyless", "verdict": "PASS" if ok else "FAIL",
                          "plain_root_recomputed": proot, "plain_root_declared": t.get("plain_root"),
                          "leaf_recompute_ok": leaf_ok, "leaf_count": len(pl),
                          "keyed_root": "UNPROVEN(无钥不可验真伪，只验完整性)",
                          "kid_declared": t.get("kid")}, ensure_ascii=False, indent=1))
        return 0 if ok else 1
    key, keypath, origin = ensure_key(a.key, create=False)
    rc = recompute(t, key)
    rc["mode"] = "keyed"
    rc["verdict"] = "PASS" if rc["ok"] else "FAIL"
    rc["keypath_shape"] = "<keystore>/*.key"
    print(json.dumps(rc, ensure_ascii=False, indent=1))
    return 0 if rc["ok"] else 1


def cmd_prove(a):
    with io.open(a.tree, encoding="utf-8") as f:
        t = json.load(f)
    key, _, _ = ensure_key(a.key, create=False)
    pr = inclusion_proof(t, a.path, key)
    if not pr.get("ok"):
        print(json.dumps(pr, ensure_ascii=False))
        return 1
    m = next(x for x in t["leaves"] if x["path"] == a.path)
    ok, root = verify_proof(t, a.path, m["fp_sha3_512_16"], m["size"], pr["proof"], key)
    print(json.dumps({"path": a.path, "fp_sha3_512_16": m["fp_sha3_512_16"], "size": m["size"],
                      "proof_steps": len(pr["proof"]), "proof": pr["proof"],
                      "recomputed_root": root, "verdict": "PASS" if ok else "FAIL",
                      "note": "接收方需自持同钥；无钥者只能验伴生根"}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def find_key(start=None):
    """向上逐级找 keystore；找不到＝无钥路径（第三方默认如此），不是错误。"""
    d = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    for _ in range(10):
        p = os.path.join(d, "_敏感_加密存储", "opl_hmac_keystore", KEYNAME)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def cmd_check(a):
    """第三方核验入口：对着**仓库本身的文件**重算双根，与对外紧凑面比对。
    无钥 ⇒ 只能验伴生根（完整性），键控根如实记 UNPROVEN；有钥 ⇒ 两根都验（完整性＋真伪）。
    这条路径不需要产物里带叶：带叶就变成"信产物"，不带叶才是"信算法＋信仓库"。"""
    with io.open(a.face, encoding="utf-8") as f:
        t = json.load(f)
    items, missing = (collect_blobs(a.root, a.ref or "HEAD") if a.git_blobs
                      else collect(a.root, git_tracked=a.git_tracked))
    if not items:
        print("判不过：仓库里采集到 0 件（不得把空集当通过）")
        return 1
    pl, kl = [], []
    key = None
    kp = a.key or find_key()
    if not a.keyless and kp and os.path.isfile(kp):
        key, _, _ = ensure_key(kp, create=False)
    for rel, fp, size in sorted(items, key=lambda x: x[0]):
        p = sha3(TAG_LEAF_P + leaf_payload(rel, fp, size))
        pl.append(p)
        if key:
            kl.append(hkey(key, TAG_LEAF_K, leaf_payload(rel, fp, size)))
    proot, _ = fold(pl, None, TAG_NODE_P)
    res = {"mode": "keyed" if key else "keyless",
           "files_checked": len(items), "missing_in_worktree": len(missing),
           "plain_root_recomputed": proot, "plain_root_declared": t.get("plain_root"),
           "integrity": "PASS" if proot == t.get("plain_root") else "FAIL",
           "leaf_count_declared": t.get("leaf_count"), "leaf_count_actual": len(items)}
    if key:
        kroot, _ = fold(kl, key, TAG_NODE_K)
        res["keyed_root_recomputed"] = kroot
        res["keyed_root_declared"] = t.get("keyed_root")
        res["kid_recomputed"] = kid_of(key)
        res["kid_declared"] = t.get("kid")
        res["authenticity"] = ("PASS" if kroot == t.get("keyed_root") and res["kid_recomputed"] == res["kid_declared"]
                               else "FAIL")
    else:
        res["authenticity"] = "UNPROVEN(无钥：谁都能造一棵自洽的伴生根，故真伪只能由持钥者定)"
    bc = base_commit(a.root)
    if bc and t.get("base_commit"):
        res["base_commit_match"] = (bc == t["base_commit"])
        res["base_commit_actual"] = bc
    res["verdict"] = ("PASS" if res["integrity"] == "PASS" and
                      (not key or res.get("authenticity") == "PASS") else "FAIL")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["verdict"] == "PASS" else 1


def cmd_selftest(a):
    r = selftest()
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r["verdict"] == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="HMAC-SHA3-512 键控树（密钥自留）＋无钥伴生根")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="对目录/仓库出树")
    b.add_argument("--root", required=True)
    b.add_argument("--git-tracked", action="store_true", help="只取 git 跟踪件（用 -z 防非 ASCII 漏采）")
    b.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    b.add_argument("--seat", default="qoder-505f061a")
    b.add_argument("--key", default=None)
    b.add_argument("--root-alias", default=None, help="源根别名，产物内不落本机绝对路径")
    b.add_argument("--no-create-key", action="store_true")
    b.add_argument("--public-face", default=None,
                   help="另出一份不含叶的对外紧凑面（可进库/可公开），全量叶集只留本机")
    b.add_argument("--git-blobs", action="store_true",
                   help="按 git blob 字节采集（跨平台唯一可比口径，抗 autocrlf 漂移）")
    b.add_argument("--ref", default=None, help="配合 --git-blobs，默认 HEAD")
    b.set_defaults(fn=cmd_build)

    c = sub.add_parser("check", help="第三方核验：对仓库文件重算双根并与对外面比对")
    c.add_argument("--root", required=True)
    c.add_argument("--face", required=True)
    c.add_argument("--git-tracked", action="store_true")
    c.add_argument("--keyless", action="store_true",
                   help="模拟无钥第三方：本机即使有钥也按无钥路径走，只出完整性判决")
    c.add_argument("--key", default=None, help="显式密钥路径；缺省则向上找 keystore，找不到就走无钥路径")
    c.add_argument("--git-blobs", action="store_true")
    c.add_argument("--ref", default=None)
    c.set_defaults(fn=cmd_check)

    v = sub.add_parser("verify", help="核验一棵已出的树")
    v.add_argument("--tree", required=True)
    v.add_argument("--key", default=None)
    v.add_argument("--keyless", action="store_true", help="无钥核验：只验伴生根，键控根记 UNPROVEN")
    v.set_defaults(fn=cmd_verify)

    p = sub.add_parser("prove", help="出单文件包含证明")
    p.add_argument("--tree", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--key", default=None)
    p.set_defaults(fn=cmd_prove)

    s = sub.add_parser("selftest", help="合成夹具自检＋阴性对照")
    s.set_defaults(fn=cmd_selftest)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
