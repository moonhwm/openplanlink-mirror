// xcheck_node.mjs —— 独立实现 JCS(RFC8785) + HMAC-SHA3-512，与 Python 版对账
import { createHmac, createHash } from "node:crypto";

// ---- RFC 8785 JCS（独立实现）----
function jcsString(s) {
  let out = '"';
  for (const ch of s) {
    const o = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === '\\') out += '\\\\';
    else if (ch === '\b') out += '\\b';
    else if (ch === '\t') out += '\\t';
    else if (ch === '\n') out += '\\n';
    else if (ch === '\f') out += '\\f';
    else if (ch === '\r') out += '\\r';
    else if (o < 0x20) out += '\\u' + o.toString(16).padStart(4, '0');
    else out += ch;
  }
  return out + '"';
}
function jcsNumber(n) {
  if (n === 0) return '0'; // 含 -0
  if (Number.isInteger(n)) return String(n);
  let s = String(n); // JS 的 String(number) 对普通小数无指数；对极大极小用指数
  if (s.includes('e') || s.includes('E')) {
    s = n.toFixed(20).replace(/0+$/, '').replace(/\.$/, '');
  }
  return s;
}
function jcs(obj) {
  if (obj === null) return 'null';
  if (obj === true) return 'true';
  if (obj === false) return 'false';
  if (typeof obj === 'number') return jcsNumber(obj);
  if (typeof obj === 'string') return jcsString(obj);
  if (Array.isArray(obj)) return '[' + obj.map(jcs).join(',') + ']';
  if (typeof obj === 'object') {
    const keys = Object.keys(obj).sort();
    return '{' + keys.map(k => jcsString(k) + ':' + jcs(obj[k])).join(',') + '}';
  }
  throw new Error('unsupported type');
}

// ---- HMAC-SHA3-512 ----
function hmacSha3512(keyHex, data) {
  return createHmac('sha3-512', Buffer.from(keyHex, 'hex')).update(data).digest('hex');
}
function sha3512Hex(data) {
  return createHash('sha3-512').update(data).digest('hex');
}

// ---- ① NSS 原语对账（empty message / short message）----
const nss = [
  ['5365244bb43f23f18dfc86c09d62db4741138bec1fbddc282d295e0a098eb5c3e37bd6f4cc16d5ce7d77b1d474a1eb4db313cc0c24e48992ac125196549df9a8', '', '8327dc85e33898f05724b34a89dfc74f2581b228203ff148f7c86aa328e0e5330c00015d1d983ab005fbc18d3695f2dd5f304bab7a4b7c34f6d010ca0af1acf5'],
  ['00698977f7102c67b594166919aa99dc3e58c7b6697a6422e238d04d2f57b2c74e4e84f5c4c6b792952df72f1c09244802f0bcf8752efb90e836110703bfa21c', '01', '84185a2890b3f4c5ef8723c292db676c69104e7ff7def5ecf26928a41626d2b16b063d8a9df03917498467f5abd7af3c6c732957f67cb800a517b26963142a1d'],
];
for (const [k, m, exp] of nss) {
  const got = hmacSha3512(k, Buffer.from(m, 'hex'));
  console.log('NSS', got === exp ? '✅' : '★', got.slice(0, 16) + '…', got === exp ? '匹配' : '不匹配');
}

// ---- ② 完整包络 tag（固定值，与 Python 对账）----
const KEY = '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f';
const body = Buffer.from('hello', 'utf-8');
const env = {
  version: 'a2a-hmac-sha3-512/v1',
  key_id: 'k-test-1',
  sender_id: 'cairn-dsh',
  recipient_id: 'workbuddy-hy4',
  timestamp: '2026-10-03T18:00:00+08:00',
  nonce: '0123456789abcdef0123456789abcdef',
  body_sha3_512: sha3512Hex(body),
};
const authInput = Buffer.from('OpenPlanLink-A2A-HMAC-v1\u0000', 'utf-8') + '';
const prefix = Buffer.from('OpenPlanLink-A2A-HMAC-v1\u0000', 'utf-8');
const canonical = Buffer.from(jcs(env), 'utf-8');
const tag = createHmac('sha3-512', Buffer.from(KEY, 'hex')).update(Buffer.concat([prefix, canonical])).digest('hex');

console.log('BODY_SHA3_512', env.body_sha3_512);
console.log('JCS', jcs(env));
console.log('ENV_TAG', tag);
