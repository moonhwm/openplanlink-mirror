// MCP 握手探针：对四个 stdio MCP server 依次做 initialize + tools/list
// 用法： node probe_mcp.mjs
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

const ROOT = 'C:\\Users\\欧阳宏俊\\.dsh\\mcp-servers\\node_modules';
const SERVERS = [
  { name: 'ima', pkg: 'ima-mcp', bin: 'dist/index.js' },
  // 以下三项需要真实凭据才能做业务调用；此处用占位值仅验证 MCP 协议层是否可达
  { name: 'wps', pkg: 'wps-mcp', bin: 'src/index.js', args: ['--apiToken', 'DUMMY', '--fileId', 'DUMMY', '--scriptId', 'DUMMY'] },
  { name: 'supabase', pkg: '@supabase/mcp-server-supabase', bin: 'dist/cli.js', args: ['--access-token', 'DUMMY', '--read-only'] },
  { name: 'neon', pkg: '@neondatabase/mcp-server-neon', bin: 'dist/index.js', args: ['start', 'DUMMY'] },
];

function probe(s) {
  return new Promise((resolve) => {
    const entry = path.join(ROOT, ...s.pkg.split('/'), ...s.bin.split('/'));
    if (!existsSync(entry)) return resolve({ name: s.name, ok: false, error: 'entry missing: ' + entry });
    const child = spawn(process.execPath, [entry, ...(s.args ?? [])], { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    const result = { name: s.name, ok: false };
    const done = (extra) => {
      clearTimeout(timer);
      try { child.kill(); } catch {}
      resolve(Object.assign(result, extra));
    };
    const timer = setTimeout(() => done({ error: 'timeout(8s)', stderr: err.slice(0, 300) }), 8000);
    child.stdout.on('data', (b) => {
      out += b.toString('utf8');
      let idx;
      while ((idx = out.indexOf('\n')) >= 0) {
        const line = out.slice(0, idx).trim();
        out = out.slice(idx + 1);
        if (!line) continue;
        let msg;
        try { msg = JSON.parse(line); } catch { continue; }
        if (msg.id === 1 && msg.result) {
          result.serverInfo = msg.result.serverInfo;
          result.protocolVersion = msg.result.protocolVersion;
          child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
          child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }) + '\n');
        } else if (msg.id === 2) {
          if (msg.result?.tools) {
            result.tools = msg.result.tools.map((t) => t.name);
            result.toolCount = result.tools.length;
            result.ok = true;
            done({});
          } else {
            done({ error: msg.error ? JSON.stringify(msg.error).slice(0, 200) : 'no tools field' });
          }
        } else if (msg.id === 1 && msg.error) {
          done({ error: 'init error: ' + JSON.stringify(msg.error).slice(0, 200) });
        }
      }
    });
    child.stderr.on('data', (b) => { err += b.toString('utf8'); });
    child.on('error', (e) => done({ error: 'spawn error: ' + e.message }));
    child.on('exit', (c) => { if (!result.ok) done({ error: 'exited code ' + c, stderr: err.slice(0, 300) }); });
    child.stdin.write(
      JSON.stringify({
        jsonrpc: '2.0', id: 1, method: 'initialize',
        params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'dsh-probe', version: '1.0.0' } },
      }) + '\n',
    );
  });
}

const results = [];
for (const s of SERVERS) results.push(await probe(s));
console.log(JSON.stringify(results, null, 2));
