# spec-attest_selfcheck

## 目的
证明件自洽性与「同批不变式」校验：判定一份 attest/manifest 是否**内部自洽**（声明的文件集与其声明的根同一批），并可选择性对磁盘实况做落盘校验。

## 输入/输出
- 输入：`<manifest.json>`、可选 `--root-dir`、`--verify-disk`、`--normalize-crlf`（保留项）、`--key-file`/`--key-env`、`--json`
- 输出：四档结果表（L1 结构 / L2 叶自洽 / L3 根自洽 / L4 落盘）＋ 根 MAC 结论 ＋ `VERDICT=`
- 退出码：全过 0；任一 FAIL 1；件不存在 2

## 不变量
- **L3 为纯声明值检验**：仅用 manifest 自己声明的 leaf 集自举默克尔根，**不触碰任何本地文件**——这是识别「声明值不同批」的决定性档
- 无密钥时 MAC 判 **SKIP**，并输出 `PASS(未签名件)`，**绝不伪造验签结论**
- **L4 采用「原始优先、归一化兜底」**：原始相符即通过；原始不符但**文本**（前 8 KiB 无 NUL）归一化后相符 ⇒ 记「CRLF 救回」（非篡改）；两者皆不符才算**真漂移**
  - 反面教训（本工具历次实现）：① 只按原始比对 ⇒ 在 Windows/autocrlf 环境把整仓误报为篡改；② 只按归一化比对 ⇒ 把「本就以 CRLF 入签」的文件误报为漂移。**两个方向都会造成假阳性，故必须双向判定**
- 二进制文件一律只按原始字节比对

## 失败模式
- manifest 缺 `files`/`merkle_root_sha3_512` → 对应档 FAIL（结构缺失）
- `content_sha3_512` 非法 hex → 该文件计入 L2 不符（不中断）
- `--key-env` 非 hex → 回落读 `--key-file`；两者皆无 → MAC SKIP

## 关键函数
- sha3
- leaf_of
- root_of
- main

## 验收断言
- 对内部自洽的证明件：L1/L2/L3 PASS
- 人为把 `merkle_root_sha3_512` 改一位 ⇒ L3 FAIL 且退出码 1（可定位）
- 本仓 `skills/context-pruner/FORGE_REPORT.md`（以 CRLF 入签）应判 **CRLF 救回**，而非真漂移
