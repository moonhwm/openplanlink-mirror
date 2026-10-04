#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""event_driven.py —— 事件驱动骨架：信息等幂消费共振场。

本体系由事件驱动（非预编排固定流程）：系统依据运行时发生的各类事件
（用户操作 / 消息到达 / 状态变化 / 定时到期）触发相应响应与处理逻辑。

事件模型：事件 = (type, 来源, 载荷, 幂等键, 时间戳)
  共振场  = 事件总线：事件入 → 幂等去重（CAS）→ 路由到 handler → 留痕审计
  等幂消费 = 同一事件（同幂等键）只处理一次（复用 cas_store 的 CAS 语义）
纯标准库。留痕进 _audit JSONL。
"""
import json
import pathlib
import time

LOG_FILE = pathlib.Path(__file__).parent / "event_field_audit.jsonl"

EVENT_TYPES = {"user_op", "message_arrival", "state_change", "timer_due", "model_result"}

_HANDLERS = {}
_SEEN = {}  # 幂等键 → 处理时间（内存共振场；持久化可换 cas_store）


def on(event_type):
    """装饰器：注册某事件类型的 handler。"""
    def deco(fn):
        _HANDLERS[event_type] = fn
        return fn
    return deco


def _audit(ev, result):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"event": ev, "result": result, "ts": time.time()}, ensure_ascii=False) + "\n")


def emit(event_type, source, payload, idempotency_key=None, now=None):
    """事件入共振场：幂等去重 + 路由 handler + 留痕。返回处理结果。"""
    if event_type not in EVENT_TYPES:
        return {"ok": False, "reason": "未知事件类型"}
    key = idempotency_key or json.dumps([event_type, source, payload], ensure_ascii=False, sort_keys=True)
    if key in _SEEN:
        return {"ok": True, "dup": True, "reason": "等幂跳过（已消费）"}
    _SEEN[key] = time.time()
    handler = _HANDLERS.get(event_type)
    if handler is None:
        return {"ok": False, "reason": "无 handler"}
    try:
        result = handler(source, payload)
    except Exception as e:
        result = {"ok": False, "reason": "%s: %s" % (type(e).__name__, e)}
    _audit({"type": event_type, "source": source, "payload": payload, "key": key}, result)
    return {"ok": True, "dup": False, "result": result}


if __name__ == "__main__":
    @on("message_arrival")
    def _route(sender, payload):
        return {"routed_to": payload.get("recipient_id", "?")}

    @on("state_change")
    def _state(sender, payload):
        return {"state": payload.get("to"), "from": payload.get("from")}

    r1 = emit("message_arrival", "cairn-dsh", {"recipient_id": "workbuddy-hy4"}, "msg-1")
    r2 = emit("message_arrival", "cairn-dsh", {"recipient_id": "workbuddy-hy4"}, "msg-1")  # 等幂重复
    r3 = emit("state_change", "cairn-dsh", {"from": "idle", "to": "busy"}, "st-1")
    print("  事件1 =", r1)
    print("  事件2（重复幂等） =", r2)
    print("  事件3 =", r3)
    print("  共振场留痕 =", LOG_FILE.exists())
