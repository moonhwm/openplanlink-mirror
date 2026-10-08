#!/usr/bin/env node
// -*- coding: utf-8 -*-
// 温层批次 A 批量上传器（断点续跑/重名时间戳/失败即停）
// 用法: node ima_pilot187_upload.cjs [--max N] [--start index]
// 状态落盘 a2a-plaza/pilot187_state.json（每件一条，随时可续）
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const NODE = process.execPath;
const SKILL = 'C:/Users/欧阳宏俊/.agents/skills/ima-skill';
const { imaApi } = require(path.join(SKILL, 'ima_api.cjs'));

const KB_ID = 'Sns5cMIOFmsG8ftUUA4XDHtNatkOmcgX5da2mU7cnak=';
const STATE = 'a2a-plaza/pilot187_state.json';
const argv = process.argv.slice(2);
const maxN = argv.includes('--max') ? parseInt(argv[argv.indexOf('--max') + 1], 10) : Infinity;
const startAt = argv.includes('--start') ? parseInt(argv[argv.indexOf('--start') + 1], 10) : 0;

const batch = JSON.parse(fs.readFileSync('a2a-plaza/pilot187_batch.json', 'utf8'));
const files = [...batch.A1, ...batch.A2];
let state = fs.existsSync(STATE) ? JSON.parse(fs.readFileSync(STATE, 'utf8')) : {};
const save = () => fs.writeFileSync(STATE, JSON.stringify(state, null, 1));

function ts() { const d = new Date(); const p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`; }

async function uploadOne(abs, origLabel) {
  const fname0 = path.basename(abs);
  let pre = JSON.parse(execFileSync(NODE, [path.join(SKILL, 'knowledge-base/scripts/preflight-check.cjs'), '--file', path.resolve(abs)], { encoding: 'utf8' }));
  if (!pre.pass) return { ok: false, stage: 'preflight', err: pre.reason };

  let title = pre.file_name;
  let chk = JSON.parse(await imaApi('openapi/wiki/v1/check_repeated_names', { params: [{ name: title, media_type: pre.media_type }], knowledge_base_id: KB_ID }));
  if (chk.code !== 0) return { ok: false, stage: 'check_repeated_names', err: chk.msg };
  if (chk.data && chk.data.check_results && chk.data.check_results[0] && chk.data.check_results[0].is_repeated) {
    const ext = path.extname(title);
    title = title.slice(0, title.length - ext.length) + '_' + ts() + ext;
    chk = JSON.parse(await imaApi('openapi/wiki/v1/check_repeated_names', { params: [{ name: title, media_type: pre.media_type }], knowledge_base_id: KB_ID }));
    if (chk.code !== 0) return { ok: false, stage: 'check_repeated_names(2)', err: chk.msg };
    if (chk.data.check_results[0].is_repeated) return { ok: false, stage: 'check_repeated_names(2)', err: '加时间戳后仍重名，停' };
  }

  const cm = JSON.parse(await imaApi('openapi/wiki/v1/create_media', {
    file_name: title, file_size: pre.file_size, content_type: pre.content_type,
    knowledge_base_id: KB_ID, file_ext: pre.file_ext }));
  if (cm.code !== 0 || !cm.data) return { ok: false, stage: 'create_media', err: cm.msg };
  const mediaId = cm.data.media_id;
  const cos = cm.data.cos_credential || {};

  try {
    execFileSync(NODE, [
      path.join(SKILL, 'knowledge-base/scripts/cos-upload.cjs'),
      '--file', path.resolve(abs),
      '--secret-id', cos.secret_id || '', '--secret-key', cos.secret_key || '', '--token', cos.token || '',
      '--bucket', cos.bucket_name || '', '--region', cos.region || '', '--cos-key', cos.cos_key || '',
      '--content-type', pre.content_type,
      '--start-time', String(cos.start_time || ''), '--expired-time', String(cos.expired_time || ''),
      '--timeout', '300000'], { stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) { return { ok: false, stage: 'cos-upload', err: String(e).slice(0, 200) }; }

  const ak = JSON.parse(await imaApi('openapi/wiki/v1/add_knowledge', {
    media_type: pre.media_type, media_id: mediaId, title,
    knowledge_base_id: KB_ID,
    file_info: { cos_key: cos.cos_key, file_size: pre.file_size, file_name: title } }));
  if (ak.code !== 0) return { ok: false, stage: 'add_knowledge', err: ak.msg };
  return { ok: true, title, size: pre.file_size };
}

(async () => {
  let done = 0, attempted = 0;
  for (let i = startAt; i < files.length; i++) {
    const abs = files[i];
    const key = abs;
    if (state[key] && state[key].ok) continue;
    if (attempted >= maxN) break;
    attempted++;
    const r = await uploadOne(abs);
    state[key] = { ...r, i, at: new Date().toISOString() };
    save();
    if (!r.ok) {
      console.log(`FAIL[${i}] ${path.basename(abs)} [${r.stage}] ${r.err}`);
      console.log('== 失败即停（纪律）==');
      console.log(`PROGRESS ok=${Object.values(state).filter(x => x.ok).length}/${files.length} attempted_this_round=${attempted}`);
      return;
    }
    done++;
    if (done % 10 === 0) console.log(`...进度 ${Object.values(state).filter(x => x.ok).length}/${files.length}`);
  }
  const okN = Object.values(state).filter(x => x.ok).length;
  console.log(`BATCH_DONE ok=${okN}/${files.length} attempted=${attempted}`);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
