#!/usr/bin/env node
import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";

const DOMAIN_PREFIX = Buffer.from("OpenPlanLink-A2A-HMAC-v1\0", "utf8");
const EXPECTED_BODY_HASH = "75d527c368f2efe848ecf6b073a36767800805e9eef2b1857d5f984f036eb6df891d75f72d9b154518c1cd58835286d1da9a38deba3de98b5a53e5ed78a84976";
const EXPECTED_TAG = "53d0d652af398f630eab41787fd4086300dc0ee298d5527aea4574f0679aefd42e27c4ac46cf11f6554b9251727f065ac41c41c5d0e58c8d9435b297c3f5f09a";
const TAGLESS_FIELDS = [
  "body_sha3_512",
  "key_id",
  "nonce",
  "recipient_id",
  "sender_id",
  "timestamp",
  "version",
];

function canonicalizeEnvelope(envelope) {
  assert.deepEqual(Object.keys(envelope).sort(), TAGLESS_FIELDS);
  for (const value of Object.values(envelope)) assert.equal(typeof value, "string");
  return Buffer.from(JSON.stringify(Object.fromEntries(TAGLESS_FIELDS.map((key) => [key, envelope[key]]))), "utf8");
}

function hmacSha3512(key, data) {
  return createHmac("sha3-512", key).update(data).digest("hex");
}

function decodeHex(value, label, expectedBytes) {
  assert.equal(typeof value, "string", `${label} must be a string`);
  assert.match(value, /^(?:[0-9a-f]{2})*$/, `${label} must be canonical lowercase hex`);
  if (expectedBytes !== undefined) assert.equal(value.length, expectedBytes * 2, `${label} has wrong length`);
  return Buffer.from(value, "hex");
}

const nss = [
  ["5365244bb43f23f18dfc86c09d62db4741138bec1fbddc282d295e0a098eb5c3e37bd6f4cc16d5ce7d77b1d474a1eb4db313cc0c24e48992ac125196549df9a8", "", "8327dc85e33898f05724b34a89dfc74f2581b228203ff148f7c86aa328e0e5330c00015d1d983ab005fbc18d3695f2dd5f304bab7a4b7c34f6d010ca0af1acf5"],
  ["00698977f7102c67b594166919aa99dc3e58c7b6697a6422e238d04d2f57b2c74e4e84f5c4c6b792952df72f1c09244802f0bcf8752efb90e836110703bfa21c", "01", "84185a2890b3f4c5ef8723c292db676c69104e7ff7def5ecf26928a41626d2b16b063d8a9df03917498467f5abd7af3c6c732957f67cb800a517b26963142a1d"],
];
assert.equal(nss.length, 2, "NSS fixed vector count changed");
for (const [keyHex, messageHex, expected] of nss) {
  const keyBytes = decodeHex(keyHex, "NSS key", 64);
  const messageBytes = decodeHex(messageHex, "NSS message");
  decodeHex(expected, "NSS tag", 64);
  assert.equal(hmacSha3512(keyBytes, messageBytes), expected);
}

const key = decodeHex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f", "envelope key", 64);
const envelope = {
  version: "a2a-hmac-sha3-512/v1",
  key_id: "k-test-1",
  sender_id: "cairn-dsh",
  recipient_id: "workbuddy-hy4",
  timestamp: "2026-10-03T18:00:00+08:00",
  nonce: "0123456789abcdef0123456789abcdef",
  body_sha3_512: createHash("sha3-512").update("hello").digest("hex"),
};
assert.equal(envelope.body_sha3_512, EXPECTED_BODY_HASH);
const authenticated = Buffer.concat([DOMAIN_PREFIX, canonicalizeEnvelope(envelope)]);
assert.equal(hmacSha3512(key, authenticated), EXPECTED_TAG);
console.log(JSON.stringify({ ok: true, nssVectors: nss.length, envelopeVector: true }));
