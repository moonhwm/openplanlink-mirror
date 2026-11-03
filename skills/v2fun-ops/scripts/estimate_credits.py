#!/usr/bin/env python3
"""V2Fun 积分消耗估算器。

数据源：doc.v2fun.ai/zh/pricing（2026-10-01 侦察快照，API 按任务计费口径）。
Web 端实际操作单价以页面操作前提示为准（官方注明"每次操作前显示所需积分"）。

用法：
  python3 estimate_credits.py                    # 打印完整单价表
  python3 estimate_credits.py --pipeline character   # 预设流程：完整角色（生图→3D→纹理→动画）
  python3 estimate_credits.py --items mesh_basic std_texture anim_retarget
  python3 estimate_credits.py --video-capture-basic 30   # 基础版视频动捕 30 秒
  python3 estimate_credits.py --video-capture-pro 30     # 高级版（含手部）30 秒
"""
import argparse
import sys

# 单价表（积分）。来源：doc.v2fun.ai/zh/pricing，侦察日期 2026-10-01。
PRICE_TABLE = {
    # 图像
    "txt2img_qwen":        ("文生图（Qwen-Image）", 1),
    "txt2img_nb2_lite":    ("文生图（Nano-Banana-2-Lite）", 5),
    "txt2img_nb2":         ("文生图（Nano-Banana-2）", 10),
    "txt2img_nb_pro":      ("文生图（Nano-Banana-Pro）", 15),
    "txt2img_gpt2":        ("文生图（GPT-Image-2 / 2.5-Flare / 2.5-Sunburst）", 10),
    "img_edit_multiview":  ("多视图图像编辑（GPT-Multiview）", 20),
    "img_process":         ("图像处理（SeedVR2）", 2),
    # 3D
    "mesh_basic":          ("文生/图生 3D（基础模型）", 20),
    "mesh_multiview_pro":  ("多视图 3D 生成（Pro-Multiview）", 20),
    "std_texture":         ("标准纹理（附加）", 20),
    "hd_texture_8k":       ("8K 高清纹理（附加）", 5),
    "pbr_texture":         ("PBR 材质（附加）", 2),
    "remesh":              ("重拓扑", 5),
    "format_convert":      ("格式转换", 5),
    # 动画/动捕（按时长的见下方函数）
    "anim_retarget":       ("动画重定向（每次）", 5),
}

PIPELINES = {
    # 帮助中心示例：生图 1 → 3D 20 → 纹理 20 → 动画 5 ≈ 46 积分
    "character": ["txt2img_qwen", "mesh_basic", "std_texture", "anim_retarget"],
    "mesh_only": ["mesh_basic"],
    "mesh_hd":   ["mesh_basic", "hd_texture_8k", "pbr_texture"],
}

def video_capture_cost(seconds: int, pro: bool) -> int:
    """基础版 1 积分/3 秒；高级版（含手部）10 积分/3 秒。按 3 秒为单位向上取整。"""
    units = -(-seconds // 3)
    return units * (10 if pro else 1)

def main() -> int:
    ap = argparse.ArgumentParser(description="V2Fun 积分消耗估算器")
    ap.add_argument("--pipeline", choices=sorted(PIPELINES), help="预设流程")
    ap.add_argument("--items", nargs="+", choices=sorted(PRICE_TABLE), help="逐项累加")
    ap.add_argument("--video-capture-basic", type=int, metavar="SEC", help="基础版视频动捕秒数")
    ap.add_argument("--video-capture-pro", type=int, metavar="SEC", help="高级版视频动捕秒数")
    args = ap.parse_args()

    if not any([args.pipeline, args.items, args.video_capture_basic, args.video_capture_pro]):
        width = max(len(v[0]) for v in PRICE_TABLE.values())
        print("=== V2Fun 官方单价表（API 口径，2026-10-01 快照）===")
        for key, (label, cost) in PRICE_TABLE.items():
            print(f"  {label:<{width}}  {cost:>3} 积分   [{key}]")
        print("  视频动捕·基础版           1 积分/3秒   (video_capture_cost)")
        print("  视频动捕·高级版(含手部)  10 积分/3秒   (video_capture_cost)")
        print("\n预设流程：")
        for name, keys in PIPELINES.items():
            total = sum(PRICE_TABLE[k][1] for k in keys)
            print(f"  {name}: {total} 积分  ({' → '.join(keys)})")
        return 0

    total = 0
    if args.pipeline:
        for k in PIPELINES[args.pipeline]:
            label, cost = PRICE_TABLE[k]
            print(f"  {label}: {cost}")
            total += cost
    if args.items:
        for k in args.items:
            label, cost = PRICE_TABLE[k]
            print(f"  {label}: {cost}")
            total += cost
    if args.video_capture_basic is not None:
        c = video_capture_cost(args.video_capture_basic, pro=False)
        print(f"  视频动捕·基础版 {args.video_capture_basic}s: {c}")
        total += c
    if args.video_capture_pro is not None:
        c = video_capture_cost(args.video_capture_pro, pro=True)
        print(f"  视频动捕·高级版 {args.video_capture_pro}s: {c}")
        total += c
    print(f"合计：{total} 积分")
    return 0

if __name__ == "__main__":
    sys.exit(main())
