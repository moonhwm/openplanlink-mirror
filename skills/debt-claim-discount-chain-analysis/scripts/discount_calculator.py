#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""债权信息折扣期全链路分析 - 汇总指标计算脚本

计算三情景折扣后估值（悲观=区间下限连乘 / 中性=中值连乘 / 乐观=上限连乘）、
按折扣因子逐环节的 Waterfall、HHI 集中度。输出与 examples.md 同口径可复算。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

R = Tuple[float, float]  # (下限, 上限)


@dataclass
class DebtClaim:
    """单笔债权：名义金额 + D1-D6 六因子区间（0-1 小数）"""
    name: str
    debtor: str
    nominal: float
    d1: R = (1.0, 1.0)   # 判决确认
    d2: R = (1.0, 1.0)   # 执行折扣
    d3: R = (1.0, 1.0)   # 资产折扣
    d4: R = (1.0, 1.0)   # 顺位折扣
    d5: R = (1.0, 1.0)   # 时间价值
    d6: R = (1.0, 1.0)   # 不确定性

    def factors(self) -> List[Tuple[str, R]]:
        return [("D1 判决确认", self.d1), ("D2 执行折扣", self.d2), ("D3 资产折扣", self.d3),
                ("D4 顺位折扣", self.d4), ("D5 时间价值", self.d5), ("D6 不确定性", self.d6)]


def time_value_range(years: float, r_low: float = 0.05, r_high: float = 0.10) -> R:
    """D5 区间：1/(1+r)^n，r∈[r_low, r_high]（r 越高折得越狠=下限）"""
    return (1 / (1 + r_high) ** years, 1 / (1 + r_low) ** years)


def evaluate(claim: DebtClaim) -> Dict[str, object]:
    def run(pick):
        bal, steps = claim.nominal, []
        for name, (lo, hi) in claim.factors():
            f = pick(lo, hi)
            new = bal * f
            steps.append((name, bal - new, new))
            bal = new
        return bal, steps
    pess, _ = run(lambda lo, hi: lo)
    neut, nsteps = run(lambda lo, hi: (lo + hi) / 2)
    opti, _ = run(lambda lo, hi: hi)
    return {"pessimistic": pess, "neutral": neut, "optimistic": opti, "steps": nsteps}


def portfolio_waterfall(claims: List[DebtClaim]) -> List[Tuple[str, float, float]]:
    """组合 waterfall：按因子环节加总（中性口径）"""
    names = [n for n, _ in claims[0].factors()]
    bals = {c.name: c.nominal for c in claims}
    out, prev = [], sum(bals.values())
    for i, name in enumerate(names):
        for c in claims:
            lo, hi = c.factors()[i][1]
            bals[c.name] *= (lo + hi) / 2
        cur = sum(bals.values())
        out.append((name, prev - cur, cur))
        prev = cur
    return out


def hhi(nominals: List[float]) -> float:
    """债权集中度（按名义金额份额平方和，0-10000）"""
    t = sum(nominals)
    return sum((x / t * 100) ** 2 for x in nominals) if t else 0.0


def fmt(x: float) -> str:
    return f"{x:,.2f}"


def main() -> None:
    claims = [
        DebtClaim("债权一", "某甲置业公司+实控人乙", 18_000_000.00,
                  d2=(0.05, 0.25), d3=(0.20, 0.60), d4=(0.03, 0.30),
                  d5=time_value_range(5.7), d6=(0.85, 0.95)),
        DebtClaim("债权二", "某丙重机公司", 700_000.00,
                  d2=(0.00, 0.05), d3=(0.00, 0.05), d4=(0.03, 0.30),
                  d5=time_value_range(3), d6=(0.50, 0.70)),
        DebtClaim("债权三", "某丁制造公司", 2_000_000.00,
                  d2=(0.80, 1.00), d3=(0.95, 1.00), d4=(0.70, 0.95),
                  d5=time_value_range(2), d6=(0.95, 0.98)),
    ]
    print("== 逐笔三情景 ==")
    tot = {"pessimistic": 0.0, "neutral": 0.0, "optimistic": 0.0}
    for c in claims:
        r = evaluate(c)
        for k in tot: tot[k] += r[k]
        print(f"{c.name}（{c.debtor}，名义 {fmt(c.nominal)}）：悲观 {fmt(r['pessimistic'])} / "
              f"中性 {fmt(r['neutral'])} / 乐观 {fmt(r['optimistic'])}")
        for name, cut, bal in r["steps"]:
            print(f"    {name}：-{fmt(cut)} → 余 {fmt(bal)}")
    print(f"\n== 组合（名义 {fmt(sum(c.nominal for c in claims))}）==")
    print(f"悲观 {fmt(tot['pessimistic'])} / 中性 {fmt(tot['neutral'])} / 乐观 {fmt(tot['optimistic'])}")
    print("\n== 组合 Waterfall（中性，按因子环节）==")
    prev = sum(c.nominal for c in claims)
    for name, cut, bal in portfolio_waterfall(claims):
        print(f"  减：{name} -{fmt(cut)} → 余 {fmt(bal)}")
    print(f"勾稽：扣减合计+终值 = {fmt(prev)}")
    h = hhi([c.nominal for c in claims])
    tier = "低" if h < 1000 else ("中" if h < 1500 else ("较高" if h <= 1800 else "高（极度集中）"))
    print(f"\nHHI = {h:,.0f}（{tier}；尺度：<1000 低 / 1000-1500 中 / 1500-1800 较高 / >1800 高）")
    print(f"中性折扣率 = {(1 - tot['neutral'] / prev) * 100:.1f}%")


if __name__ == "__main__":
    main()
