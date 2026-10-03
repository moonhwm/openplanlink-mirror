#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""compensate.py —— 补偿事务（Saga 补偿模式：自动回滚已执行步骤）。

依《认证流程专章》第七章（一）：MFA 验证失败或钩子校验未通过时执行自动回滚，
已执行之半程操作（暂存、构建中间产物、临时授权）按补偿逻辑逆序撤销。
参照 Saga orchestration pattern（AWS Prescriptive Guidance，按标题引用）。
纯标准库，Windows 直跑。
"""


class Tx:
    """补偿事务：记录步骤的撤销函数，失败时逆序回滚。"""

    def __init__(self):
        self.steps = []      # [(label, undo_fn)]
        self.committed = False

    def step(self, label, do_fn, undo_fn):
        """执行一步：do_fn 成功则登记 undo_fn；do_fn 抛异常则立即逆序回滚已执行步骤。"""
        try:
            do_fn()
        except Exception:
            self.rollback()
            raise
        self.steps.append((label, undo_fn))
        return label

    def rollback(self):
        """逆序撤销已执行步骤。"""
        for label, undo in reversed(self.steps):
            undo()
        self.steps = []

    def commit(self):
        self.committed = True
        self.steps = []


if __name__ == "__main__":
    log = []
    tx = Tx()
    tx.step("暂存", lambda: log.append("暂存A"), lambda: log.append("撤销A"))
    tx.step("临时授权", lambda: log.append("授权B"), lambda: log.append("撤销B"))
    print("  执行后 log =", log)
    tx.rollback()          # 模拟 MFA 失败 → 自动回滚
    print("  回滚后 log =", log, "（逆序撤销：撤销B→撤销A）")

    # 中途失败自动回滚
    log2 = []
    tx2 = Tx()
    try:
        tx2.step("步1", lambda: log2.append("1"), lambda: log2.append("撤销1"))
        tx2.step("步2", lambda: (_ for _ in ()).throw(RuntimeError("步2失败")), lambda: log2.append("撤销2"))
    except RuntimeError:
        pass
    print("  中途失败自动回滚后 log2 =", log2, "（撤销1已逆序执行）")
