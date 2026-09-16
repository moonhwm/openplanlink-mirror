#!/usr/bin/env node
// HarmonyOS hvigor 构建脚本（命令行入口）
// 用法：node hvigorw.js [task] [--mode debug|release] [--product default]
const { execSync } = require('child_process');
const path = require('path');

const hvigorConfig = require('./hvigor/hvigor-config.json5');
const nodeModulesPath = path.join(__dirname, 'node_modules');
const hvigorPath = path.join(nodeModulesPath, '@ohos', 'hvigor');

try {
  const hvigor = require(hvigorPath);
  hvigor.execute(process.argv.slice(2), {
    cwd: __dirname,
    nodeModulesPath: nodeModulesPath
  });
} catch (e) {
  console.error('hvigor not found. Run "npm install" first to install build dependencies.');
  console.error('Or open the project in DevEco Studio which provides hvigor automatically.');
  process.exit(1);
}