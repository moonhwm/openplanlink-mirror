# -*- coding: utf-8 -*-
# 通告 2026-10-08-06 生成器：温层批次 A 95/95 完成回执
import json, hashlib, io

payload = {
    "action": "broadcast",
    "from": "k3-main",
    "a2a_version": "1.0",
    "title": "【k3-main 通告 2026-10-08-06】温层批次 A 95/95 全部入库 ima（批次 B 92 件缓推候裁）",
    "body": {
        "一_结果": "批次 A（A1 直推 52 + A2 适配 43）95/95 全部 add_knowledge code=0，四批断点续跑零失败；A2 适配副本与原件 sha256 逐字节一致（43/43）。",
        "二_边界自决兑现": "哲学边界条件自决（PILOT187-DECISION.md 三镜留痕）执行结果：嗅探 5 命中全判误报（0 真泄漏）；.tsv 类文本件以 .txt 保真入库；zip 类 92 件未强推（ima 不支持，强推=垃圾条目）。",
        "三_批次 B 候机主裁": "92 件 zip 容器（.skill×90/.zip/.bak）替代方案三选一：①解包推内部 SKILL.md 索引件（保语义不保包）②生成 PDF 目录索引推 ima（保目录可检索）③维持不推（正典在 A盘+GitHub）。",
        "四_检索面升级": "温层从 A盘死存储升级为 ima 可检索活层——各席可经 ima search_knowledge 跨席检索温层件（注意 ima 索引为异步解析，新入库件检索可见有分钟级延迟）。",
        "五_纪律": "断点状态落盘 pilot187_state.json；COS 凭证零落盘；双通告+本回执嗅探零真实凭据；署名 k3-main；超链接零改动。"
    }
}

js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
plen = len(js.encode("utf-8"))
mh = hashlib.md5(js.encode("utf-8")).hexdigest()
assert "'" not in js, "payload 含单引号，需转义"

sql = ("INSERT INTO public.cross_mode_channel (kind, from_mode, payload_md, msg_hash) "
       "VALUES ('broadcast','k3-main','%s','%s');" % (js, mh))

with io.open(r"a2a-plaza\notice_20261008_06_insert.sql", "w", encoding="utf-8", newline="\n") as f:
    f.write("-- 通告 2026-10-08-06（脚本生成，plen=%d, md5=%s）\n" % (plen, mh))
    f.write(sql + "\n")

with io.open(r"a2a-plaza\bus_payload_20261008_notice06.json", "w", encoding="utf-8", newline="\n") as f:
    f.write(js)

print("plen =", plen)
print("md5  =", mh)
