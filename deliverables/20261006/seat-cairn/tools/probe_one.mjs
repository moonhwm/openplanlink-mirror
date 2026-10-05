// 通用单体 MCP 探针：node probe_one.mjs <entry.js> [key=value ...]
// 输出 initialize 结果与 tools/list 工具名
import { spawn } from 'node:child_process';

const [entry, ...kv] = process.argv.slice(2);
if (!entry) { console.error('usage: node probe_one.mjs <entry.js> [KEY=VAL ...]'); process.exit(2); }
const env = { ...process.env };
for (const pair of kv) {
  const i = pair.indexOf('=');
  if (i > 0) env[pair.slice(0, i)] = pair.slice(i + 1);
}

const child = spawn(process.execPath, [entry], { stdio: ['pipe', 'pipe', 'pipe'], env });
let out = '', err = '';
const finish = (result) => { try { child.kill(); } catch {} console.log(JSON.stringify(result, null, 2)); process.exit(0); };
const timer = setTimeout(() => finish({ ok: false, error: 'timeout(10s)', stderr: err.slice(0, 400) }), 10000);

child.stdout.on('data', (b) => {
  out += b.toString('utf8');
  let i;
  while ((i = out.indexOf('\n')) >= 0) {
    const line = out.slice(0, i).trim(); out = out.slice(i + 1);
    if (!line) continue;
    let m; try { m = JSON.parse(line); } catch { continue; }
    if (m.id === 1 && m.result) {
      clearTimeout(timer);
      child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
      child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }) + '\n');
    } else if (m.id === 2) {
      finish({
        ok: !!m.result?.tools,
        serverInfo: undefined,
        tools: (m.result?.tools ?? []).map((t) => t.name),
        toolCount: (m.result?.tools ?? []).length,
        error: m.error ? JSON.stringify(m.error).slice(0, 300) : undefined,
      });
    } else if (m.id === 1 && m.error) {
      clearTimeout(timer); finish({ ok: false, error: JSON.stringify(m.error).slice(0, 300), stderr: err.slice(0, 400) });
    }
  }
});
child.stderr.on('data', (b) => { err += b.toString('utf8'); });
child.on('error', (e) => finish({ ok: false, error: 'spawn: ' + e.message }));
child.on('exit', (c) => finish({ ok: false, error: 'exited ' + c, stderr: err.slice(0, 400) }));
child.stdin.write(JSON.stringify({
  jsonrpc: '2.0', id: 1, method: 'initialize',
  params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'dsh-probe', version: '1' } },
}) + '\n');
