#!/usr/bin/env node
// 独立验证 opl-attest/1：复算 SHA3-512 Merkle 根 + ed25519 验签
// 用法: node tools/verify.mjs [attest.json 路径]
import fs from "node:fs";
import crypto from "node:crypto";

const fp = process.argv[2] || new URL("../attest.json", import.meta.url).pathname;
const a = JSON.parse(fs.readFileSync(fp, "utf-8"));
if (a.schema !== "opl-attest/1") { console.error("schema mismatch:", a.schema); process.exit(2); }

const sha3 = (b) => crypto.createHash("sha3-512").update(b).digest("hex");
let L = Object.keys(a.files).sort().map((k) => a.files[k]);
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

const pub = crypto.createPublicKey({ key: Buffer.from(a.pubkey, "base64"), format: "der", type: "spki" });
const payload = JSON.stringify({ ts: a.ts, merkle_root: a.merkle_root, file_count: a.file_count });
const sigOk = crypto.verify(null, Buffer.from(payload), pub, Buffer.from(a.sig, "base64"));

console.log("schema      :", a.schema);
console.log("ts          :", a.ts);
console.log("files       :", a.file_count);
console.log("merkle_root :", a.merkle_root);
console.log("root match  :", rootOk);
console.log("sig verify  :", sigOk);
process.exit(rootOk && sigOk ? 0 : 1);
