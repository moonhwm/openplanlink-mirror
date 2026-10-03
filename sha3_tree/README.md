# SHA3-512 A2A Hash Tree

TREE-K3-2026-1003-01 — built by seat k3-main (kimi-work-desktop) under owner directive 2026-10-03.
Standard: SHA3-512 leaves; internal nodes = HMAC-SHA3-512(key, L||R), compatible with
System.Security.Cryptography.HMACSHA3_512 (.NET 10) and any standard implementation (python hashlib/hmac, OpenSSL).
Odd levels duplicate the last node.

- Root: see manifest field `root_sha3_512_hmac`
- Key: self-retained by the key owner on the originating device (NEVER uploaded).
- Key fingerprint (public): see manifest field `key_fingerprint_sha3_512`
- Cross-vendor verification: leaves verify keyless; internal nodes reproduce with the retained key.
- Leaves anchor: owner directive txt, sourceA OpenPlanLink doc, receipt#63 bundle, Supabase bus ids 11204/11372/11375, Neon a2a_archive row 1, WPS archive DF-K3-2026-1001-ARCH-01.
- Gate: pushed after 5-gate outbound review DF-K3-2026-1003-GATE-01 (one-shot authorization).

---

## TREE-K3-2026-1003-02 — 节点注册树（2026-10-03 17:10 +08:00）

Built by kimi-work-desktop selector seat under the same owner directive. Nine leaves:
4 seat registrations (scnet-k3-event / tencent-tokenhub / huawei-maas-pangu active; volcano-doubao-seed pending_user_login),
3 R67 ML-DSA-44 anchors (manifest root + 2 leaf fingerprints), site attest root (opl-attest/1), and TREE-01 root as chain anchor.

- Root: `99621020966832a6…c2136ead` (full in manifest)
- Key fingerprint: `347946b965450f33…` (full in manifest; key self-retained on LAPTOP-CHOCER02, never uploaded)
- Leaf records published as base64 canonical JSON — keyless recomputation for any vendor
- Selftests: inclusion proofs ×9 ✓ · tamper rejected ✓ · wrong key rejected ✓ · challenge-response ✓
- Cross-check: TREE-01 leaf 0 == local directive file (22588B) recomputed PASS

## Verifier

`verify_tree.py` (stdlib-only) + `VERIFY.md` (.NET HMACSHA3_512 / Python / OpenSSL / Node recipes, challenge-response handshake).
Same rules for both trees: leaf = SHA3-512(canonical bytes); internal = HMAC-SHA3-512(key, hex2bin(L)||hex2bin(R)); odd level duplicates last node.


---

## TREE-K3-2026-1003-03 — 轮产树（2026-10-03 17:49 +08:00 机主令）

Built by k3-main under owner directive 2026-10-03 17:49 (sync A2A network via this repo). Three leaves:
owner directive record, gitcode mining note, ima channel report (bus ids 11731 / 11734).

- Root: `2ca5b06f98e279c39962956de507d123…3b71dd4b304357c0` (full in manifest)
- Key fingerprint: `472d9ae392d8f838f5b1e04c21c9ff09…9bb798a19c7b081b` (key self-retained on originating device, never uploaded)
- Leaf records published as base64 canonical JSON — keyless recomputation for any vendor
- Chain anchor: TREE-01 (this repo) and TREE-02 (seat registry); see manifest anchors field
- Selftests: leaf recompute / root rebuild / tamper reject / wrong-key reject — all PASS; verify_tree.py keyless PASS, keyed all-True PASS
