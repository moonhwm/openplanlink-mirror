# Git 上传前检查

`git_upload_gate.py` 读取将要推送的 Git 对象，包括中间提交、提交消息、标签消息、树中的名称和 ZIP/Office 内文。它不以当前工作区代替历史。报告不给出原始匹配值或凭据片段。

在仓库根目录运行一次 `git config --local core.hooksPath tools/hooks`，将本仓库钩子设为上传前入口。这个配置只作用于本仓库；已有钩子请先自行核对并保留。Windows 可用 `OPL_PYTHON` 或 `SELFVO_PYTHON` 指定现有 Python 解释器。钩子与程序缺失、历史不完整或读取失败都阻断。

钩子保留主镜像既有的 main 提交签名要求，按实际目标引用检查对应提交，且只接受 Git 的可信签名状态 G。非 main 分支仍作凭据检查，不误用当前 HEAD 或 origin/main 代替待推引用。SSH 签名需要 Git 既有的 allowedSigners 配置；本程序不生成正式身份、密钥或信任名单。

退出码：0 为本次已枚举范围通过已知模式检查；1 为检测到凭据形态或 main 签名未通过；2 为检查不完整。二进制、外部 LFS 内容、超限容器和浅克隆不会被静默放行。报告仅用于技术预检，不能证明所有凭据均不存在。

离线复核已知基线后的增量对象：

```text
python tools/git_upload_gate.py --repo . --range BASE_COMMIT HEAD_COMMIT
python tools/git_upload_gate.py --repo . --tip HEAD --output history-audit.json
python -m unittest discover -s tests -p test_git_upload_gate.py -v
```

`--range` 的基线必须来自实际已核验的远端提交。新分支的 pre-push 旧 OID 为零，会保守检查全部可达历史；远端旧 OID 本地缺失时也检查全部历史。历史已有凭据形态时，新增清洁提交不会使完整历史检查变为通过。先由凭据实际持有人核对和替换暴露值，再制定保留署名、引用与归档证据的历史清理方案。不要靠测试、示例、API_KEY 等邻近词降级放行，也不要改成只扫描末次提交。

GitHub 检查工作流在上传后对 PR 增量作复核，不能撤回已上传的内容。手动关闭钩子、绕过 Git 走 API 上传及其他客户端都需要在发送前独立检查实际发送的对象。是否设为分支必须通过的检查，仍取决于仓库的实际保护规则；加入工作流文件不自动改变这些规则。

依据：[Git 钩子标准输入](https://git-scm.com/docs/githooks)、[可达对象枚举](https://git-scm.com/docs/git-rev-list)、[对象读取](https://git-scm.com/docs/git-cat-file)。程序使用 Python 标准库及已有 Git，不引入 Python 第三方依赖。
