#!/usr/bin/env node
// 独立验证 opl-attest/1：复算 SHA3-512 Merkle 根 + ed25519 验签
// 用法: node tools/verify.mjs [attest.json 路径]
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const fp = process.argv[2] || fileURLToPath(new URL("../attest.json", import.meta.url));
const a = JSON.parse(fs.readFileSync(fp, "utf-8"));
if (a.schema !== "opl-attest/1") { console.error("schema mismatch:", a.schema); process.exit(2); }
if (a.sig_alg !== "ed25519+sha3-512") { console.error("signature algorithm mismatch:", a.sig_alg); process.exit(2); }
if (!a.files || typeof a.files !== "object" || Array.isArray(a.files)) {
  console.error("invalid files mapping");
  process.exit(2);
}

const entries = Object.entries(a.files);
const countOk = Number.isSafeInteger(a.file_count) && a.file_count > 0 && a.file_count === entries.length;
const leafFormatOk = entries.every(([path, digest]) => (
  path.length > 0 && /^[0-9a-f]{128}$/.test(digest)
));
const rootFormatOk = /^[0-9a-f]{128}$/.test(a.merkle_root);
if (!countOk || !leafFormatOk || !rootFormatOk) {
  console.error("invalid attestation structure", { countOk, leafFormatOk, rootFormatOk });
  process.exit(1);
}

const decodeBase64 = (value, label) => {
  if (typeof value !== "string" || !/^[A-Za-z0-9+/]+={0,2}$/.test(value)) {
    throw new Error(`${label} is not canonical base64`);
  }
  const decoded = Buffer.from(value, "base64");
  if (decoded.toString("base64") !== value) throw new Error(`${label} is not canonical base64`);
  return decoded;
};

const sha3 = (b) => crypto.createHash("sha3-512").update(b).digest("hex");
let L = entries.sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0)).map(([, digest]) => digest);
while (L.length > 1) {
  const n = [];
  for (let i = 0; i < L.length; i += 2) {
    const r = L[i + 1] || L[i];
    n.push(sha3(Buffer.from(L[i] + r, "hex")));
  }
  L = n;
}
const root = L[0];
const rootOk = root === a.merkle_root;

const pub = crypto.createPublicKey({ key: decodeBase64(a.pubkey, "pubkey"), format: "der", type: "spki" });
const payload = JSON.stringify({ ts: a.ts, merkle_root: a.merkle_root, file_count: a.file_count });
const sigOk = crypto.verify(null, Buffer.from(payload), pub, decodeBase64(a.sig, "sig"));

console.log("schema      :", a.schema);
console.log("ts          :", a.ts);
console.log("files       :", a.file_count);
console.log("merkle_root :", a.merkle_root);
console.log("root match  :", rootOk);
console.log("sig verify  :", sigOk);
process.exit(rootOk && sigOk ? 0 : 1);
