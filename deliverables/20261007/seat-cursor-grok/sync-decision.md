# 同步决定 · cursor-grok · 2026-10-07

本席核对了 `moonhwm/openplanlink-mirror` 与本机另一份目录，没有把二者合并，也没有强推。

- 本克隆与 `origin/main` 同在 `9ad76ff560ef1c8fd04cc0d8292854b385bf03e8`。
- `china-macro-lead` 里的 `openplanlink-mirror` 只是站点抓取（`assets`、`atlas`、`data`、`index.html`、`videos.json`），不是这个 Git 仓库。按贡献约定，站点文件由看守链覆盖，不从那份抓取回写。
- `china-macro-lead` 本身没有远程，所以宏观笔记留在本机，不塞进本镜像。

下一步若要改站点，改上游握手工程里的构建源。若要把宏观仓库单独上传，给它一个自己的远程，而不是借用本仓库。
