// MCP 服务启动器：把凭据/参数从环境变量注入真实服务器进程
// 用法：node launch.mjs <ima|wps|supabase|neon>
// 透明代理：stdio 继承，不截留任何字节
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

const ROOT = 'C:\\Users\\欧阳宏俊\\.dsh\\mcp-servers\\node_modules';
const NODE = process.execPath;

const SERVERS = {
  ima: {
    entry: path.join(ROOT, 'ima-mcp', 'dist', 'index.js'),
    args: () => [],
    requiredEnv: [],
  },
  wps: {
    entry: path.join(ROOT, 'wps-mcp', 'src', 'index.js'),
    args: (e) => ['--apiToken', e.WPS_API_TOKEN, '--fileId', e.WPS_FILE_ID, '--scriptId', e.WPS_SCRIPT_ID],
    requiredEnv: ['WPS_API_TOKEN', 'WPS_FILE_ID', 'WPS_SCRIPT_ID'],
  },
  supabase: {
    entry: path.join(ROOT, '@supabase', 'mcp-server-supabase', 'dist', 'cli.js'),
    args: (e) => ['--access-token', e.SUPABASE_ACCESS_TOKEN, '--read-only'],
    requiredEnv: ['SUPABASE_ACCESS_TOKEN'],
  },
  neon: {
    entry: path.join(ROOT, '@neondatabase', 'mcp-server-neon', 'dist', 'index.js'),
    args: (e) => ['start', e.NEON_API_KEY],
    requiredEnv: ['NEON_API_KEY'],
  },
  // 百度网盘（社区实现 capwitf/baidu-netdisk-knowledge-mcp，MIT）：无需启动参数，
  // 凭据走环境变量 BAIDU_APP_KEY / BAIDU_SECRET_KEY，登录用二维码 OAuth 运行时完成
  baidu: {
    entry: 'C:\\Users\\欧阳宏俊\\.dsh\\mcp-vendor\\baidu-netdisk-knowledge-mcp\\dist\\cli.js',
    args: () => [],
    requiredEnv: [],
  },
};

const id = process.argv[2];
const spec = SERVERS[id];
if (!spec) {
  process.stderr.write(`unknown server id: ${id}\n`);
  process.exit(2);
}
if (!existsSync(spec.entry)) {
  process.stderr.write(`entry missing: ${spec.entry}\n`);
  process.exit(3);
}
const missing = spec.requiredEnv.filter((k) => !process.env[k]);
if (missing.length) {
  process.stderr.write(`[${id}] 缺少环境变量: ${missing.join(', ')}\n`);
  process.exit(4);
}

const child = spawn(NODE, [spec.entry, ...spec.args(process.env)], { stdio: 'inherit' });
child.on('exit', (code, signal) => {
  process.stderr.write(`[${id}] 服务器退出 code=${code} signal=${signal}\n`);
  process.exit(code ?? 1);
});
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => { try { child.kill(); } catch {} });
}
