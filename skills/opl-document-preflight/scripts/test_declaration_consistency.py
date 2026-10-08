#!/usr/bin/env python3
"""declaration_consistency.py 的常驻自证套件。

覆盖三层：
  1. 判据分层——逐字重复 / 包含关系 / 高相似微改 / 中度相似 / 洁净，各归其位；
  2. 可失败性——FAIL 路径确实返回 1，覆盖缺口确实被披露（不以 PASS 冒充已比对）；
  3. cred-clean 性质——报告与 stdout 绝不出现输入中的凭据真值。
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import declaration_consistency as D  # noqa: E402

P1 = ("第一段：本文档规定统一执行口径，凡涉及复杂技术、协议及流程事项，须在双重框架下从严把控，"
      "确保目标高度一致、标准高度统一、执行高度贯通，切实形成统筹协同一体化推进的工作格局。")
P2 = ("第二段：所有修改必须署名并附唯一标识符，不得仅以不可识别证伪、难以对抗性审查的自称书写本稿，"
      "确保全过程留痕、可溯可查，满足审计追溯与对抗性复核之需要。")
P3 = ("第三段：目标存储节点包括WPS云文档与ima，推送时优先选择议会物理地址，"
      "操作完成后同步生成可交互架构图，为全链路可视化溯源与调度提供有力支撑。")


def write(tmp: str, name: str, body: str) -> Path:
    p = Path(tmp) / name
    p.write_bytes(body.encode("utf-8"))
    return p


def crlf(*paras: str) -> str:
    return "\r\n".join(paras) + "\r\n"


def run(path: Path, threshold: float = 0.60, min_len: int = 40):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = D.main([str(path), "--threshold", str(threshold),
                     "--min-segment-len", str(min_len)])
    return rc, buf.getvalue()


class VerdictLayeringTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def test_clean_document_passes(self):
        rc, out = run(write(self.td, "clean.txt", crlf(P1, P2, P3)))
        self.assertEqual(rc, 0)
        self.assertIn("verdict = PASS", out)

    def test_exact_duplicate_warns_not_fails(self):
        rc, out = run(write(self.td, "dup.txt", crlf(P1, P2, P3, P3)))
        self.assertEqual(rc, 0)
        self.assertIn("verdict = WARN", out)
        self.assertIn("逐字重复条款 1 对", out)

    def test_literal_containment_fails(self):
        extended = P3 + "另需同步生成可交互审计报告并归档备查。"
        rc, out = run(write(self.td, "contain.txt", crlf(P1, P2, P3, extended)))
        self.assertEqual(rc, 1)
        self.assertIn("verdict = FAIL", out)
        self.assertIn("口径歧义(包含关系)", out)

    def test_high_ratio_micro_edit_fails(self):
        edited = P1.replace("双重框架", "三重框架")
        rc, out = run(write(self.td, "micro.txt", crlf(P1, P2, edited)))
        self.assertEqual(rc, 1)
        self.assertIn("口径歧义", out)

    def test_same_clause_extended_fails(self):
        """同一条款被扩写（相似度 >= 0.9）属口径歧义，必须 FAIL。"""
        variant = P3.replace("WPS云文档与ima", "WPS云文档、ima与GitHub")
        rc, out = run(write(self.td, "ext.txt", crlf(P1, P2, P3, variant)))
        self.assertEqual(rc, 1)
        self.assertIn("verdict = FAIL", out)
        self.assertIn("口径歧义", out)

    def test_mid_similarity_warns_with_overlap(self):
        """相似度落在 [threshold, 0.9) 区间：告警交人工复核，不径判 FAIL。"""
        variant = P3.replace("推送时优先选择议会物理地址", "按轮次择优投递至指定节点池")
        rc, out = run(write(self.td, "mid.txt", crlf(P1, P2, P3, variant)))
        self.assertEqual(rc, 0)
        self.assertIn("verdict = WARN", out)
        self.assertIn("部分重叠条款 1 对", out)

    def test_short_fragment_inside_long_paragraph_is_not_ambiguity(self):
        """独立成行的短 URL 被长段落包含（比例 < 0.6），属正常排版，不得判口径歧义。"""
        short = "https://example.invalid/push-endpoint?channel=placeholder"
        long_para = ("第四段：本条款规定消息推送通道的配置入口为 " + short +
                     " ，凡涉凭据形态一律不得出域，出域载荷须经脱敏处理并留痕备查，"
                     "确保全过程可溯可查、可对抗性复核，并接受常态化审计与监督检查。")

        nlen = lambda s: len(D.normalize(s))  # noqa: E731  用被测件自身归一口径
        proportion = nlen(short) / nlen(long_para)
        self.assertLess(proportion, 0.6, "夹具失效：比例须低于闸门才有意义")
        self.assertGreaterEqual(nlen(short), 40, "夹具失效：短行须达参与门槛")

        rc, out = run(write(self.td, "frag.txt", crlf(P1, P2, long_para, short)))
        self.assertNotIn("口径歧义", out)
        self.assertEqual(rc, 0)

    def test_containment_proportion_gate_boundary(self):
        """比例闸边界：短段占长段 >= 0.6 才算同条款扩写。"""
        base = "条款正文" * 25  # 100 字
        near = base[:70]        # 0.70 >= 0.6 -> 判歧义
        far = base[:30]         # 0.30 <  0.6 -> 不判歧义
        rc1, out1 = run(write(self.td, "prop_hi.txt", crlf(P1, base, near)))
        self.assertEqual(rc1, 1)
        self.assertIn("口径歧义(包含关系)", out1)
        rc2, out2 = run(write(self.td, "prop_lo.txt", crlf(P1, base, far)))
        self.assertNotIn("口径歧义", out2)
        self.assertEqual(rc2, 0)

    def test_bare_lf_fails(self):
        body = "\n".join([P1, P2, P3]) + "\n"
        rc, out = run(write(self.td, "lf.txt", body))
        self.assertEqual(rc, 1)
        self.assertIn("行尾不变量破坏", out)


class CoverageDisclosureTests(unittest.TestCase):
    """覆盖缺口必须被说出来，不得以 PASS 冒充「已比对且无差异」。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name
        self.short = crlf("第三段:存储节点含WPS与ima。",
                          "第三段:存储节点含WPS、ima与GitHub。")

    def tearDown(self):
        self._td.cleanup()

    def test_short_pairs_disclosed_as_skipped(self):
        rc, out = run(write(self.td, "short.txt", self.short))
        self.assertEqual(rc, 0)
        self.assertIn("未参与比对", out)
        self.assertIn("覆盖缺口", out)

    def test_lowering_min_len_exposes_the_pair(self):
        rc, out = run(write(self.td, "short2.txt", self.short), min_len=8)
        self.assertNotIn("覆盖缺口", out)
        self.assertIn("部分重叠条款 1 对", out)
        self.assertEqual(rc, 0)


class InputErrorTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def test_missing_file_returns_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = D.main([str(Path(self.td) / "nope.txt")])
        self.assertEqual(rc, 2)

    def test_non_utf8_returns_2(self):
        p = Path(self.td) / "bad.txt"
        p.write_bytes(b"\xff\xfe\x00bad bytes")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = D.main([str(p)])
        self.assertEqual(rc, 2)
        self.assertIn("拒绝猜测编码", buf.getvalue())


class CredCleanTests(unittest.TestCase):
    """cred-clean 是本件的硬性质：真值绝不进报告、不进 stdout。"""

    SECRET_MAC = "AA:BB:CC:DD:EE:FF"
    SECRET_SENDKEY = "sctpFAKEFAKE-fakefakefake0000"

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name

    def tearDown(self):
        self._td.cleanup()

    def test_secrets_never_appear_in_report_or_stdout(self):
        leaky_url = f"https://example.invalid/push?key={self.SECRET_SENDKEY}"
        body = crlf(
            P1, P2,
            f"第三段：消息推送通道（{self.SECRET_SENDKEY}）配置入口 {leaky_url} ，"
            f"本机网卡标识为 {self.SECRET_MAC}，二者均属凭据形态不得出域。",
            f"第三段补：同一入口重复登记一次以便比对 {leaky_url} 。")
        src = write(self.td, "secret.txt", body)
        report_path = Path(self.td) / "report.json"

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            D.main([str(src), "--json", str(report_path)])
        stdout = buf.getvalue()
        payload = report_path.read_text(encoding="utf-8")

        # 硬性质：真值既不进 stdout 也不进落盘报告
        for secret in (self.SECRET_MAC, self.SECRET_SENDKEY):
            self.assertNotIn(secret, stdout)
            self.assertNotIn(secret, payload)
        # 掩码在「会被打印的字段」上确实生效（重复链接项）
        self.assertIn("[MASK:push-sendkey]", stdout)
        self.assertIn("[MASK:push-sendkey]", payload)
        # 单元层：mask() 对整段文本一次即净，且幂等
        masked = D.mask(body)
        self.assertNotIn(self.SECRET_MAC, masked)
        self.assertIn("[MASK:mac-address]", masked)

        data = json.loads(payload)
        self.assertEqual(data["secret_shapes_detected"].get("mac-address"), 1)
        # 裸送 1 次 + 两条 URL 内各 1 次 = 3
        self.assertEqual(data["secret_shapes_detected"].get("push-sendkey"), 3)

    def test_doubled_account_detected_and_masked(self):
        body = crlf(P1, P2,
                    "第四段：成果统一上传至 123456789@example.com123456789@example.com 名下仓库，"
                    "并同步生成凭证票据纳入总线体系经后量子加密处理。")
        shapes = D.account_shapes(body)
        doubled = [s for s in shapes if s["concatenated_self_duplicate"]]
        self.assertEqual(len(doubled), 1)
        self.assertEqual(doubled[0]["local_len"], 9)
        self.assertNotIn("123456789", json.dumps(shapes, ensure_ascii=False))

    def test_mask_is_idempotent(self):
        once = D.mask(f"键 {self.SECRET_SENDKEY} 与 {self.SECRET_MAC}")
        self.assertEqual(D.mask(once), once)
        self.assertNotIn(self.SECRET_SENDKEY, once)


if __name__ == "__main__":
    unittest.main(verbosity=2)
