#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""live_state_loop.py —— 实时状态环（spec-live_state_loop 的实现件）。

规范契约（spec-live_state_loop.md）：
  目的：实时状态环；输入/输出：周期 → 状态；
  不变量：状态一致；失败模式：异常恢复；关键函数：once / main；验收断言：状态在册。

实现口径：
  - 周期拍一次状态（ts、seq、内存/句柄/探针项），append-only 落 state_loop.jsonl（在册即可复算）；
  - once() 拍一拍并返回状态 dict；main() 以 interval 连续循环，单拍异常捕获登记后继续（异常恢复）；
  - 纯标准库，零外部依赖。
"""
import json
import os
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "state_loop.jsonl")


def _probe():
    """状态探针：时钟与存活面（可扩展挂接系统指标）。"""
    return {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "pid": os.getpid()}


def _head_seq():
    if not os.path.exists(LEDGER):
        return 0
    n = 0
    with open(LEDGER, encoding="utf-8") as f:
        for _ in f:
            n += 1
    return n


def once():
    """拍一拍：采集状态、登记在册、返回状态 dict。"""
    state = {"seq": _head_seq() + 1, "kind": "tick"}
    state.update(_probe())
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(state, ensure_ascii=False) + "\n")
    return state


def main(interval=60, cycles=None):
    """状态环主循环：单拍异常登记 error 拍并续行（异常恢复），不让环死。"""
    n = 0
    while cycles is None or n < cycles:
        try:
            once()
        except Exception as e:  # 失败模式：异常恢复——错误在册而环不死
            err = {"seq": _head_seq() + 1, "kind": "error",
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "detail": str(e)[:200]}
            with open(LEDGER, "a", encoding="utf-8") as f:
                f.write(json.dumps(err, ensure_ascii=False) + "\n")
            traceback.print_exc()
        n += 1
        time.sleep(interval)


def _selftest():
    """验收断言：状态在册——拍后 ledger 存在且含本拍。"""
    s = once()
    assert os.path.exists(LEDGER)
    last = open(LEDGER, encoding="utf-8").read().strip().splitlines()[-1]
    assert json.loads(last)["seq"] == s["seq"], "状态未在册"
    print("SELFTEST PASS: 状态在册 seq=%d" % s["seq"])


if __name__ == "__main__":
    _selftest()
