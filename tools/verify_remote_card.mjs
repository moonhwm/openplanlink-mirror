// Verify a remote A2A agent card against an out-of-band pinned Ed25519 key.
import {
  createHash,
  createPublicKey,
  timingSafeEqual,
  verify,
} from "node:crypto";

const CARD_URL = process.env.OPL_A2A_REMOTE_CARD_URL
  || "http://120.46.86.165/.well-known/agent-card.json";
const PINNED_PUBKEY_B64 = process.env.OPL_A2A_REMOTE_CARD_PUBKEY_B64;
const PINNED_CARD_SHA256 = process.env.OPL_A2A_REMOTE_CARD_BYTES_SHA256;
const MAX_CARD_BYTES = 131_072;

function decodeBase64(value, label) {
  if (typeof value !== "string"
      || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) {
    throw new Error(`${label} 不是规范 Base64`);
  }
  const decoded = Buffer.from(value, "base64");
  if (decoded.toString("base64") !== value) {
    throw new Error(`${label} 不是规范 Base64`);
  }
  return decoded;
}

function canon(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "[" + value.map(canon).join(",") + "]";
  if (typeof value === "object") {
    return "{" + Object.keys(value).sort()
      .map((key) => JSON.stringify(key) + ":" + canon(value[key])).join(",") + "}";
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    throw new Error("卡片包含非有限数值");
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("卡片包含不可规范化值");
  return encoded;
}

async function discardResponse(response) {
  if (response.body) await response.body.cancel().catch(() => {});
}

async function readLimited(response, limit) {
  if (!response.body) throw new Error("卡片响应缺少正文");
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) throw new Error("卡片超过大小上限");
      chunks.push(Buffer.from(value));
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  }
  return Buffer.concat(chunks, total);
}

async function main() {
  if (!PINNED_PUBKEY_B64 || !PINNED_CARD_SHA256) {
    throw new Error("缺少带外公钥或卡片字节摘要信任锚");
  }
  if (!/^[0-9a-f]{64}$/.test(PINNED_CARD_SHA256)) {
    throw new Error("固定卡片字节摘要格式非法");
  }
  const pinnedKeyBytes = decodeBase64(PINNED_PUBKEY_B64, "固定公钥");
  const response = await fetch(CARD_URL, {
    redirect: "error",
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) {
    await discardResponse(response);
    throw new Error(`HTTP 状态异常: ${response.status}`);
  }
  const contentLengthHeader = response.headers.get("content-length");
  if (contentLengthHeader !== null) {
    const contentLength = Number(contentLengthHeader);
    if (!Number.isSafeInteger(contentLength) || contentLength < 0
        || contentLength > MAX_CARD_BYTES) {
      await discardResponse(response);
      throw new Error("卡片 Content-Length 非法或超过上限");
    }
  }
  const bytes = await readLimited(response, MAX_CARD_BYTES);
  const bytesSha256 = createHash("sha256").update(bytes).digest();
  const pinnedBytesSha256 = Buffer.from(PINNED_CARD_SHA256, "hex");
  if (!timingSafeEqual(bytesSha256, pinnedBytesSha256)) {
    throw new Error("卡片字节摘要与带外信任锚不匹配");
  }

  const card = JSON.parse(bytes.toString("utf8"));
  if (!card || typeof card !== "object" || Array.isArray(card)
      || !card.integrity || typeof card.integrity !== "object"
      || Array.isArray(card.integrity)) {
    throw new Error("卡片完整性字段非法");
  }
  const { integrity, ...rest } = card;
  const { pubkey, sig, canonicalSha256 } = integrity;
  if (typeof canonicalSha256 !== "string" || !/^[0-9a-f]{64}$/.test(canonicalSha256)) {
    throw new Error("规范化摘要格式非法");
  }
  const cardKeyBytes = decodeBase64(pubkey, "卡片公钥");
  const signature = decodeBase64(sig, "签名");
  if (cardKeyBytes.length !== pinnedKeyBytes.length
      || !timingSafeEqual(cardKeyBytes, pinnedKeyBytes)) {
    throw new Error("卡片公钥与带外信任锚不匹配");
  }

  const canonical = canon(rest);
  const sha256 = createHash("sha256").update(canonical).digest("hex");
  const key = createPublicKey({ key: pinnedKeyBytes, format: "der", type: "spki" });
  if (key.asymmetricKeyType !== "ed25519" || signature.length !== 64) {
    throw new Error("公钥或签名不是 Ed25519 格式");
  }
  const signatureOk = verify(null, Buffer.from(canonical, "utf8"), key, signature);
  const digestOk = sha256 === canonicalSha256;

  console.log("  规范化 sha256 匹配 =", digestOk);
  console.log("  Ed25519 验签 =", signatureOk);
  console.log("★ VERDICT=" + (signatureOk && digestOk ? "PASS" : "BAD"));
  return signatureOk && digestOk ? 0 : 1;
}

try {
  process.exitCode = await main();
} catch (error) {
  console.error("远端卡片验证失败：" + (error instanceof Error ? error.message : String(error)));
  console.log("★ VERDICT=BAD");
  process.exitCode = 1;
}
