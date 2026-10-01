/* A2A 观测站 · 单一事实源（公开数据接口）
   性质：在案登记（静态公示），非实时遥测。全部条目出自《运维留痕_2026-09.md》在案事实。
   用法：任何页面 <script src="assets/status.js"> 后读取 window.A2A_STATUS；离线可开。 */
window.A2A_STATUS = {
  meta: {
    site: "A2A 观测站",
    version: "c1a9b5d",
    as_of: "2026-09-30",
    kind: "在案登记 · 非实时遥测",
    ledger: "运维留痕_2026-09.md"
  },
  channels: [
    { id: "observe", name: "观测",   href: "observe.html", note: "在案登记公示" },
    { id: "sandbox", name: "沙盘",   href: "sandbox.html", note: "节点消费·规范场运维" },
    { id: "sea",     name: "干涉海", href: "sea.html",     note: "相位场·拓扑涡旋" },
    { id: "cinema",  name: "飞天",   href: "cinema.html",  note: "壁画苏醒·循环展映" }
  ],
  charters: [
    { name: "A2A联合审计局宪章", rev: "v1.0", status: "在案" }
  ],
  cases: [
    { id: "OA-2026-001", target: "OpenPlanLink 审计首案", status: "在案" }
  ],
  roster: [
    { name: "compshare-cli", ref: "入册队列 #51", status: "在案" }
  ],
  keys: [
    { label: "PQ 公钥广播", ref: "总线 id=11178", fp: "b3cffb08…034a", note: "指纹截位显示" }
  ],
  topology: [
    { k: "沙盘节点",     v: "26（斐波那契球面）" },
    { k: "链路（边）",   v: "55" },
    { k: "Wilson 三角环", v: "16（规范不变量 Φ 可复测）" },
    { k: "分叉类型群",   v: "Z₃（深挖/横扩/分支，Cayley 表联动）" },
    { k: "干涉海拓扑荷", v: "+3/−3 总荷守恒" },
    { k: "干涉海内核电测", v: "6/6 通过（绕 ±1 涡旋 Δφ=±2π）" }
  ]
};
