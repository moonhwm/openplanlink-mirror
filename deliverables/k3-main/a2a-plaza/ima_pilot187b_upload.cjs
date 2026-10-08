#!/usr/bin/env node
// -*- coding: utf-8 -*-
// 温层批次 B 批量上传器（索引文本）（断点续跑/重名时间戳/失败即停）
// 用法: node ima_pilot187_upload.cjs [--max N] [--start index]
// 状态落盘 a2a-plaza/pilot187_b_state.json（每件一条，随时可续）
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const NODE = process.execPath;
const SKILL = 'C:/Users/欧阳宏俊/.agents/skills/ima-skill';
const { imaApi } = require(path.join(SKILL, 'ima_api.cjs'));

const KB_ID = 'Sns5cMIOFmsG8ftUUA4XDHtNatkOmcgX5da2mU7cnak=';
const STATE = 'a2a-plaza/pilot187_b_state.json';
const argv = process.argv.slice(2);

const DIR='a2a-plaza/pilot187_b_txt';
const files = fs.readdirSync(DIR).map(f=>DIR+'/'+f);
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
  const up = JSON.parse(await imaApi('openapi/wiki/v1/add_knowledge', { file_path: path.resolve(abs), file_name: title, knowledge_base_id: KB_ID }));
  if (up.code !== 0) return { ok: false, stage: 'add_knowledge', err: up.msg };
  return { ok: true, title, size: fs.statSync(abs).size };
}

(async () => {
  let done = 0, fail = 0;
  for (let i = startAt; i < files.length; i++) {
    const abs = files[i];
    const rel = abs;
    if (state[rel] && state[rel].ok) { console.log('...跳过(已ok)', i, rel); continue; }
    if (done >= maxN) { console.log('...达上限', maxN); break; }
    const r = await uploadOne(abs, rel);
    state[rel] = { ...r, i, at: new Date().toISOString() };
    save();
    if (r.ok) { done++; console.log('...进度', done + '/' + files.length, r.title); }
    else { fail++; console.log('...FAIL', rel, r.stage, r.err); break; }
  }
  console.log('BATCH_DONE ok=' + Object.values(state).filter(s => s && s.ok).length + '/' + files.length + ' attempted=' + done);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
