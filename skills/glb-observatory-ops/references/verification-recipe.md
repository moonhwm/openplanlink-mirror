# verification-recipe.md · swiftshader 实渲验证配方（R74 实证固化）

## 1. 起本地服务

GLB 走 fetch，file:// 直开会被 CORS 拦——必须起 http.server：

```bash
cd <site_root> && setsid bash -c 'python3 -m http.server <port> --bind 127.0.0.1 > /tmp/srv.log 2>&1' < /dev/null > /dev/null 2>&1 &
```

- 端口逐轮换（残进程占口）；`pkill -f "http.server"` 会误杀自身命令行——pkill 与起服务**分两条命令**。

## 2. Playwright 配方

- **脚本写 /tmp 用 shell 跑**——IPython 有运行中的 asyncio loop，`sync_playwright` 在其中直接报错。
- **脱离进程组**：shell 工具超时杀整组，用 `setsid bash -c '...' < /dev/null > /dev/null 2>&1 &` + sleep + 读输出文件。
- 启动参数：`launch(executable_path="/usr/bin/chromium", args=["--no-sandbox","--use-gl=swiftshader","--enable-unsafe-swiftshader"])`。
- 大 GLB（20 MB 级）在软渲下载入需数十秒：`wait_until="networkidle", timeout=90000`，再等加载遮罩消失（`wait_for_function` 盯 `bar-wrap.done` 或错误遮罩出现）。

## 3. 断言六件

1. 错误遮罩未出现（`#err` 未 display:block）；
2. HUD 统计非空且含「网格/三角面」；
3. **截图实渲可见模型**——这是最终判据；
4. `pageerrors` 为空；
5. **截图内含状态行** `MODEL_LOADED | pageerrors: 0`（页面自证，非仅笔记声称）——模板内置 `#vstatus` 与 `window.__pageErrors`/`dataset.pageerrors`/`dataset.modelLoaded`/`dataset.firstFrame`，验证脚本可读断言，截图人眼可复核；
6. **程序化拖拽/滚轮后相机位姿变化**（截图机位与初始不同即证轨道控制生效；`canvas.dispatchEvent(new PointerEvent('pointerdown',...))` 序列或 Playwright mouse API 均可）。

## 4. 读数假象判例（R74 立案）

`preserveDrawingBuffer` 默认 false：渲染循环下一帧即清缓冲——此时 `canvas.toDataURL()` / `drawImage(webglCanvas)` / `readPixels` 读回**全黑**，像素和=0。这不是缺陷。处置：**勿用 canvas 读像素做判据，一律以 pg.screenshot 截图为准**。确需读像素判据时，初始化渲染器加 `preserveDrawingBuffer:true`（有性能代价，观展页不必）。

## 5. 覆盖层拦截

元素被 overlay 拦截时 `pg.click` 会重试至死——改 JS 派发：
`element.dispatchEvent(new MouseEvent('click',{bubbles:true}))`。

## 6. 验收留痕

截图 + 断言 JSON + 端点 200 清单入 verifier runs 目录；台台账记 sha[:16]。

**失败路径亦须留痕**：首轮验证若走通过失败路径（如 `chromium --headless --screenshot --virtual-time-budget` 在 rAF 无限渲染循环下逐帧软渲，20 MB 级模型必超时无产出），把失败命令、现象、修正（改走 §2 Playwright 配方）一并记入留痕——不独记成功路径。诚实记录未遂是留痕的一部分。
