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

## 多远端上传入口

`python tools/push_gate.py --repo . --remote origin --remote gitcode` 执行 fetch、必要的主远端重定基、暂存区树验证、逐远端对象检查、快进推送和引用读回。省略远端时使用该仓已配置的 origin/gitcode，分支取当前分支。必须是干净工作区且没有进行中的 Git 操作；不会自动 stash，不使用固定 C 盘仓库，不强推。镜像存在分歧时停止，保留引用以供合流。

读取现有 64 字节密钥：优先使用显式 `--key-file`，否则使用 `OPL_A2A_HMAC_KEY_B64` 或 `OPL_A2A_HMAC_KEY_FILE`；默认文件为用户已有的 `.a2a-hmac-key.bin`。缺失、格式错误或执行中改变均停止。已有树在刷新前须能以当前密钥认证原根，不将认证失败当作自动重签或密钥轮换。程序不创建或改写密钥，不记录密钥指纹、底层错误文本或远端 URL。

各远端使用自己的旧引用计算待发送范围，不能用另一服务器的已有对象排除本服务器仍需检查的对象。每个远端推送后读回目标引用；部分成功或未知结果记录在 `.git/opl-push-gate.jsonl` 和标准输出，多远端上传没有分布式原子性。不要因非零退出码就盲目重试；先按事件和引用读回对账。

每次推送临时链入受控 pre-push 入口，按服务器即时返回的引用重新检查，覆盖检查后远端回退等竞态；随后继续执行既有 pre-push 钩子。配置只作用于该次 Git 调用，不永久改写用户的 hooksPath，也不跳过原钩子的限制。未显式指定 OPL_PYTHON 时，将本次运行的 Python 解释器提供给原钩子；直接调用源码钩子时，自动候选须能运行 --version，避免 Windows 中存在但不能运行的 python3 别名阻断可用解释器。

`python tools/build_opl_tree.py --repo . --directory deliverables/20261003` 保留交付目录清单构式；导入无副作用，仅排除该目录根部的输出本身，嵌套同名附件仍纳入。它的目录范围与 Git 暂存区全树不同，不能用该清单替代上传树验证。密钥策略与上传入口一致。
