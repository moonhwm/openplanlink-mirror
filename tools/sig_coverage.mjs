import { readFileSync } from 'node:fs';
const VAULT = 'C:/Users/欧阳宏俊/Documents/kimi/tasks/2026-08-27/22-20-45-c3ffff44/GOVERNANCE/credentials';
const supa = JSON.parse(readFileSync(VAULT + '/supabase_channel.json', 'utf-8'));
const REST = supa.url.replace(/\/$/, '') + '/rest/v1/cross_mode_channel';
const HDR = { 'apikey': supa.publishable_key, 'Authorization': 'Bearer ' + supa.publishable_key };
const r = await fetch(REST + '?select=id,from_mode,kind,payload_md&order=id.desc&limit=300', { headers: HDR });
const rows = await r.json();
const re = /"sig"\s*:\s*"[A-Za-z0-9+/=]{40,}"/;
const seats = {};
for (const x of rows) {
  const s = seats[x.from_mode] = seats[x.from_mode] || { n: 0, sig: 0, kinds: {} };
  s.n++; s.kinds[x.kind] = (s.kinds[x.kind] || 0) + 1;
  if (re.test(x.payload_md)) s.sig++;
}
console.log('窗口', rows[rows.length-1].id, '→', rows[0].id, '共', rows.length, '行');
for (const [k, v] of Object.entries(seats).sort((a,b)=>b[1].n-a[1].n)) {
  console.log(k.padEnd(28), String(v.sig+'/'+v.n).padStart(8), (100*v.sig/v.n).toFixed(0)+'%', JSON.stringify(v.kinds));
}
