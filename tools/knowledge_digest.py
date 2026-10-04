#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""knowledge_digest.py —— 等幂知识消化（哲学/科学/艺术，CAS 内容寻址 + 幂等去重）。

依新目标：最可能可以等幂消化包括哲学与科学、艺术等在内的可能知识。
以 SHA-256 内容寻址实现幂等（同源内容只存一份），按领域分类。
纯标准库，Windows 直跑。
"""
import hashlib

DOMAINS = ("philosophy", "science", "art")


class KnowledgeDigest:
    def __init__(self):
        self.by_hash = {}     # hash -> {domain, text}
        self.by_domain = {d: {} for d in DOMAINS}  # domain -> hash -> True

    def ingest(self, domain, text):
        """幂等消化：返回 (digest, is_new)。同源内容只存一份。"""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        is_new = h not in self.by_hash
        if is_new:
            self.by_hash[h] = {"domain": domain, "text": text}
            if domain in self.by_domain:
                self.by_domain[domain][h] = True
        return h, is_new

    def count(self, domain=None):
        if domain is None:
            return len(self.by_hash)
        return len(self.by_domain.get(domain, {}))

    def has(self, text):
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return h in self.by_hash


if __name__ == "__main__":
    kd = KnowledgeDigest()
    h1, new1 = kd.ingest("philosophy", "自我不是凝固不变的本质，而是在时间性中不断生成的动态结构")
    h2, new2 = kd.ingest("philosophy", "自我不是凝固不变的本质，而是在时间性中不断生成的动态结构")  # 重复
    h3, new3 = kd.ingest("science", "能量守恒定律")
    h4, new4 = kd.ingest("art", "留白是中国画的意境")
    print("  首次哲学 =", new1, "｜ 重复哲学 =", new2, "（幂等去重）")
    print("  总计 =", kd.count(), "（4次ingest但3份唯一）｜ 哲学 =", kd.count("philosophy"))
    print("  重复命中 has() =", kd.has("能量守恒定律"))
