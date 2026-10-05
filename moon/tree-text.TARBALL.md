# tree-text.tar.gz.b64 — 还原规程

116 件站点文本（HTML/JS/CSS/JSON/MD，均 ≤300 KB）的确定性 tar 包 gzip。

- 格式：base64 文本分 6 片：`tree-text.tar.gz.b64.p00` … `p05`
- 还原：`cat tree-text.tar.gz.b64.p0* | base64 -d > tree-text.tar.gz && tar xzf tree-text.tar.gz`
- 校验：
  - tar.gz 字节数 = **577,190**
  - tar.gz SHA3-256 = `7a14e5ca129a8a6f…`（前 16 hex）
  - 解包后每件 sha12 须与 `MANIFEST.json` 一致（116 件 text 类）
- 决定论：tar 成员 mtime=0 / uid=gid=0 / uname=gname=''，任何人重打包同树得同字节
