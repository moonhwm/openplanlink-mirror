// verify_remote_card.mjs —— 验证远端 A2A agent-card 的 Ed25519 签名（防 MITM）。
import { createHash, createPublicKey, verify } from "node:crypto";

const resp = await fetch("http://120.46.86.165/.well-known/agent-card.json");
const card = await resp.json();
const { integrity, ...rest } = card;
const { pubkey, sig, canonicalSha256 } = integrity;

function canon(obj) {
  if (obj === null) return "null";
  if (Array.isArray(obj)) return "[" + obj.map(canon).join(",") + "]";
  if (typeof obj === "object") {
    return "{" + Object.keys(obj).sort().map(k => JSON.stringify(k) + ":" + canon(obj[k])).join(",") + "}";
  }
  return JSON.stringify(obj);
}
const canonical = canon(rest);

const sha256 = createHash("sha256").update(canonical).digest("hex");
const key = createPublicKey({ key: Buffer.from(pubkey, "base64"), format: "der", type: "spki" });
const ok = verify(null, Buffer.from(canonical, "utf8"), key, Buffer.from(sig, "base64"));

console.log("  规范化 sha256 匹配 =", sha256 === canonicalSha256, "（", sha256.slice(0, 16) + "…", "）");
console.log("  Ed25519 验签 =", ok, "（signer:", integrity.signer, "）");
console.log("★ VERDICT=" + (ok && sha256 === canonicalSha256 ? "PASS" : "BAD"));
