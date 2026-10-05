#!/usr/bin/env node
// Read-only MCP adapter over the verified official IMA skill. No HTTP listener.
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');

const skillRoot = process.argv[2];
if (!skillRoot) process.exit(2);
const officialScript = path.join(skillRoot, 'ima_api.cjs');
const expectedScript = '3ef318c47cdcd894e41d3c33fb675b592a33c36555800a123119b7ed1451b1e5';
if (crypto.createHash('sha256').update(fs.readFileSync(officialScript)).digest('hex') !== expectedScript) process.exit(2);
const upstreamFetch = global.fetch;
global.fetch = (input, options = {}) => {
  const url = new URL(typeof input === 'string' ? input : input.url);
  if (url.origin !== 'https://ima.qq.com' || url.username || url.password) throw new Error('Unsupported API destination');
  return upstreamFetch(input, {...options, redirect: 'error', signal: AbortSignal.timeout(20000)});
};
const {imaApi} = require(officialScript);
const stringField = {type: 'string'};
const listFields = {query: stringField, cursor: stringField, limit: {type: 'integer', minimum: 1, maximum: 20}};
const tools = [
  {name: 'ima_credentials_check', description: 'Check credential availability without returning credentials. This does not prove authentication.', inputSchema: {type: 'object', additionalProperties: false, properties: {}}},
  {name: 'ima_knowledge_bases_list', description: 'List or search knowledge bases using official IMA OpenAPI.', inputSchema: {type: 'object', additionalProperties: false, properties: listFields}},
  {name: 'ima_knowledge_base_get', description: 'Read knowledge base details.', inputSchema: {type: 'object', additionalProperties: false, required: ['ids'], properties: {ids: {type: 'array', items: stringField, minItems: 1, maxItems: 20}}}},
  {name: 'ima_knowledge_list', description: 'Read one page of knowledge base entries or a folder.', inputSchema: {type: 'object', additionalProperties: false, required: ['knowledge_base_id'], properties: {knowledge_base_id: stringField, folder_id: stringField, cursor: stringField, limit: {type: 'integer', minimum: 1, maximum: 50}}}},
  {name: 'ima_knowledge_search', description: 'Search entries within a knowledge base.', inputSchema: {type: 'object', additionalProperties: false, required: ['knowledge_base_id', 'query'], properties: {knowledge_base_id: stringField, query: stringField, cursor: stringField}}},
];

function available(file) {
  try {return fs.statSync(path.join(os.homedir(), '.config', 'ima', file)).size > 0;} catch {return false;}
}
function safeMessage(message) {
  let text = String(message || '').slice(0, 1000);
  for (const name of ['IMA_CLIENT_ID', 'IMA_OPENAPI_CLIENTID', 'IMA_API_KEY', 'IMA_OPENAPI_APIKEY']) {
    if (process.env[name]) text = text.split(process.env[name]).join('[redacted]');
  }
  for (const name of ['client_id', 'api_key']) {
    try {const value = fs.readFileSync(path.join(os.homedir(), '.config', 'ima', name), 'utf8').trim();
      if (value) text = text.split(value).join('[redacted]');} catch {}
  }
  return text.replace(/[A-Za-z0-9_+/=-]{48,}/g, '[opaque value omitted]');
}
function validate(tool, args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('Arguments must be an object');
  const schema = tool.inputSchema;
  for (const key of Object.keys(args)) {
    const field = schema.properties[key];
    if (!field) throw new Error('Unsupported argument');
    const value = args[key];
    if (field.type === 'string' && (typeof value !== 'string' || value.length > 10000)) throw new Error('Invalid string argument');
    if (field.type === 'integer' && (!Number.isInteger(value) || value < field.minimum || value > field.maximum)) throw new Error('Invalid page limit');
    if (field.type === 'array' && (!Array.isArray(value) || value.length < field.minItems || value.length > field.maxItems || value.some(v => typeof v !== 'string' || !v || v.length > 2000))) throw new Error('Invalid identifier list');
  }
  for (const key of schema.required || []) if (!(key in args) || args[key] === '') throw new Error('Required argument missing');
}
function select(value, fields) {
  return Object.fromEntries(fields.filter(key => value && key in value).map(key => [key, value[key]]));
}
function normalize(name, data) {
  if (name === 'ima_knowledge_bases_list') {
    return {knowledge_bases: (data.info_list || []).map(item => ({id: item.kb_id || item.id, name: item.kb_name || item.name || '', ...select(item, ['description','content_count','member_count','role_type','base_type'])})), ...select(data, ['is_end','next_cursor'])};
  }
  if (name === 'ima_knowledge_base_get') {
    const entries = data.infos || data.info_map || {};
    return {infos: Object.fromEntries(Object.entries(entries).map(([id, info]) => [id, {id: info.kb_id || info.id || id, name: info.kb_name || info.name || '', ...select(info,['description','recommended_questions','content_count'])}]))};
  }
  const entries = data.knowledge_list || data.info_list || [];
  return {entries: entries.map(item => select(item,['media_id','title','name','media_type','parent_folder_id','highlight_content','file_number','folder_number'])), ...select(data,['is_end','next_cursor','current_path'])};
}
async function call(name, args) {
  const tool = tools.find(item => item.name === name);
  if (!tool) throw new Error('Unknown read-only tool');
  validate(tool, args);
  if (name === 'ima_credentials_check') return {
    client_id_available: !!(process.env.IMA_CLIENT_ID || process.env.IMA_OPENAPI_CLIENTID) || available('client_id'),
    api_key_available: !!(process.env.IMA_API_KEY || process.env.IMA_OPENAPI_APIKEY) || available('api_key'),
    authentication_tested: false, credential_values_returned: false,
  };
  const requests = {
    ima_knowledge_bases_list: ['openapi/wiki/v1/search_knowledge_base', {query: '', cursor: '', limit: 20, ...args}],
    ima_knowledge_base_get: ['openapi/wiki/v1/get_knowledge_base', args],
    ima_knowledge_list: ['openapi/wiki/v1/get_knowledge_list', {cursor: '', limit: 20, ...args}],
    ima_knowledge_search: ['openapi/wiki/v1/search_knowledge', {cursor: '', ...args}],
  };
  const [endpoint, body] = requests[name];
  const raw = await imaApi(endpoint, body, {baseUrl: 'https://ima.qq.com', skillVersion: '1.1.10'});
  if (Buffer.byteLength(raw, 'utf8') > 8_000_000) throw new Error('Provider response exceeds limit');
  const response = JSON.parse(raw);
  if (response.code !== 0) {
    const error = new Error(safeMessage(response.msg));
    error.providerCode = response.code;
    throw error;
  }
  return {code: 0, data: normalize(name, response.data || {}),
    observed_data_fields: Object.keys(response.data || {}), official_host: 'ima.qq.com'};
}
function send(id, result, error) {
  const response = {jsonrpc: '2.0', id};
  if (error) response.error = error; else response.result = result;
  process.stdout.write(JSON.stringify(response) + '\n');
}
async function handle(message) {
  if (message.id === undefined) return;
  if (message.method === 'initialize') return send(message.id, {protocolVersion: '2024-11-05', capabilities: {tools: {}}, serverInfo: {name: 'opl-ima-readonly', version: '0.1.0'}});
  if (message.method === 'ping') return send(message.id, {});
  if (message.method === 'tools/list') return send(message.id, {tools});
  if (message.method !== 'tools/call') return send(message.id, null, {code: -32601, message: 'Method not found'});
  try {
    const result = await call(message.params?.name, message.params?.arguments || {});
    send(message.id, {content: [{type: 'text', text: JSON.stringify(result)}]});
  } catch (error) {
    send(message.id, {isError: true, content: [{type: 'text', text: JSON.stringify({error: safeMessage(error.message), provider_code: error.providerCode ?? null})}]});
  }
}
const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
let processing = Promise.resolve();
lines.on('line', line => {
  if (Buffer.byteLength(line, 'utf8') > 100000) return send(null, null, {code: -32600, message: 'Request too large'});
  let message;
  try {message = JSON.parse(line);} catch {return send(null, null, {code: -32700, message: 'Parse error'});}
  processing = processing.then(() => handle(message)).catch(() => send(message.id ?? null, null, {code: -32603, message: 'Internal error'}));
});
lines.on('close', () => processing.finally(() => process.exit(0)));
