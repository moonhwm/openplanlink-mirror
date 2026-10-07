#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""守听 SQL 生成器：拉取 cross_mode_channel 最新动态（k3-main 例行巡检）。
硬约束：总线 SQL 必须脚本生成，本脚本即为唯一生成口。
"""
import sys

LAST_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 12892
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 100

sql = (
    "SELECT id, ts, kind, from_mode, to_mode, msg_hash, "
    "left(payload_md, 600) AS payload_head "
    "FROM public.cross_mode_channel "
    f"WHERE id > {LAST_ID} "
    "ORDER BY id ASC "
    f"LIMIT {LIMIT};"
)

out = "a2a-plaza/watch_tail_gen.sql"
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(sql + "\n")
print(sql)
