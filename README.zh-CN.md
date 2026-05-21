# Cyber-Code-Shield

[English](README.md) | 简体中文

Cyber-Code-Shield 是一个面向内网、离线、强合规和高隐私开发环境的本地 AI 编程工具包与补丁助手。

它的目标是在不能使用云端 AI 编程工具时，尽量保留 AI Coding 的生产力：

- 配置本地 Ollama + Continue.dev，让 VS Code 使用本地模型
- 检查本地 AI 编程环境是否准备好
- 分析已有项目并生成本地项目上下文
- 使用本地模型生成可审查的代码补丁建议
- 根据错误日志、堆栈信息或 `path:line:column` 诊断生成修复建议
- 根据 TODO、`pass`、`NotImplementedError` 等占位实现生成补全建议
- 默认不自动修改源码，所有改动都需要人工审查后手动应用

> 目标：在不把项目代码、日志、文档或业务上下文发给云端 AI 的前提下，继续获得 AI 编程能力。

## 适合谁？

Cyber-Code-Shield 适合已经体验过 AI 编程效率提升，但所在环境不允许使用联网 AI 工具的开发者和团队。

典型场景：

- 企业内网研发
- 金融、政企、制造、医疗等合规要求较高的环境
- 离线或半离线开发工作站
- 禁用 Copilot、Cursor、ChatGPT、Claude Code 等云端 AI Coding 工具的团队

## 快速演示

检查本地环境：

```bash
python setup_local_ai.py --check
```

先试内置错误修复 demo，不调用 Ollama：

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --context-lite --dry-run
```

再试内置 TODO 补全 demo，不调用 Ollama：

```bash
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

根据你自己的项目任务生成可审查补丁建议：

```bash
python setup_local_ai.py --suggest-patch --project . --task "Add input validation" --files README.md --dry-run
```

## 当前状态

当前项目是早期 v0.2 MVP。

| 能力 | 状态 | 命令 | 是否写源码 |
| --- | --- | --- | --- |
| 环境检查 | 已完成 | `--check` | 否 |
| Continue.dev 本地配置 | 已完成 | `--merge`, `--install`, `--restore` | 只写配置 |
| 项目上下文分析 | 已完成 | `--project` | 只写上下文文件 |
| 离线环境报告 | 已完成 | `--report` | 只写报告文件 |
| 任务补丁建议 | 已完成 | `--suggest-patch` | 不写源码 |
| 错误修复建议 | 已完成 | `--fix-error` | 不写源码 |
| TODO 补全建议 | 已完成 | `--complete-todo` | 不写源码 |
| 自动应用补丁 | 未包含 | N/A | N/A |
| 完整本地 Claude Code Agent | 未包含 | N/A | N/A |

> **注意：** 补丁助手只生成 Markdown 建议文件，不会自动修改源码。请审查建议后手动应用。

后续计划：

- 根据相似模块生成同风格补丁
- 更精准的上下文选择和代码片段裁剪
- 企业部署和合规说明材料
- 更详细的框架/工具识别
- 桌面安装器原型

## 安装要求

使用生成的 Continue.dev 配置前，请先安装：

1. VS Code
2. Continue.dev 插件
3. Ollama
4. 你选择的本地模型

默认 balanced 配置：

```bash
ollama pull deepseek-coder-v2:16b
ollama pull nomic-embed-text
```

轻量配置：

```bash
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

高性能配置：

```bash
ollama pull qwen2.5-coder:32b
ollama pull nomic-embed-text
```

如果你已经有自己的本地模型，可以用 `--chat-model` 指定，例如：

```bash
python setup_local_ai.py --suggest-patch --project . --task "Add validation" --files README.md --chat-model gemma4-local --context-lite --patch-timeout 600
```

### 本地模型部署档位

Cyber-Code-Shield 适合按硬件条件和合规深度选择本地模型档位：

| 档位 | 典型用途 | 硬件适配 | 示例模型级别 |
| --- | --- | --- | --- |
| 轻量 / 试用 | 快速本地试跑、demo、简单修复、低成本验证 | 开发者笔记本或低显存测试机器 | E4B / 7B 级模型 |
| 深度合规 | 更高质量的错误修复、合规审查、复杂补丁建议 | 企业级工作站或大显存服务器 | Gemma 4 26B/31B 级模型 |

对于 `--fix-error`、`--suggest-patch` 这类补丁助手流程，26B/31B 级本地模型通常能提供更好的推理能力和更稳定的 diff。轻量模型依然适合快速验证，尤其是配合 `--context-lite` 使用，但需要认真查看 `Response warnings`。

模型名称取决于你本地 Ollama、LM Studio、llama.cpp server 或 vLLM 环境中实际配置的 tag。使用 `--chat-model` 时，请填写本地推理服务暴露出来的准确模型名。

## 快速开始

先检查本地环境：

```bash
python setup_local_ai.py --check
```

预览将要写入的 Continue.dev 配置，不修改文件：

```bash
python setup_local_ai.py --dry-run
```

默认写入 Continue.dev 当前推荐的 `config.yaml` 格式。旧版 `config.json` 仍然可用：

```bash
python setup_local_ai.py --config-format json --dry-run
```

合并到已有 Continue.dev 配置：

```bash
python setup_local_ai.py --merge
```

覆盖安装本地配置：

```bash
python setup_local_ai.py --install
```

恢复旧配置：

```bash
python setup_local_ai.py --restore
```

推荐用法：

- 已经有 Continue.dev 配置时，优先使用 `--merge`。
- 想要干净的本地-only 配置时，使用 `--install`。
- 不确定会发生什么时，先加 `--dry-run`。

安装/合并流程会：

1. 识别当前操作系统。
2. 默认定位 `~/.continue/config.yaml`，或在 `--config-format json` 下定位 `config.json`。
3. 写入前备份已有配置。
4. 写入基于本地 Ollama 的 Continue.dev 配置。

## 离线环境报告

生成本地 AI 环境报告：

```bash
python setup_local_ai.py --report
```

只预览报告，不写文件：

```bash
python setup_local_ai.py --report --dry-run
```

写到自定义路径：

```bash
python setup_local_ai.py --report --report-output ./local-ai-report.md
```

生成 JSON 报告：

```bash
python setup_local_ai.py --report --report-format json
```

默认输出文件：

```text
CYBER_CODE_SHIELD_REPORT.md
CYBER_CODE_SHIELD_REPORT.json
```

报告包括：

- OS 和 Python 版本
- Continue.dev 配置路径和备份路径
- Ollama CLI 和服务状态
- 当前选择的模型配置
- 所需模型和缺失模型
- API base 是否指向本机
- Continue.dev provider 检测结果
- 需要合规复核的云端 provider 线索
- 常见云端 AI API 环境变量名

脚本只报告环境变量名，不输出密钥值。

这个报告是配置复核辅助材料，不是正式安全审计。

## 已有项目分析

多数用户会在已有业务项目里使用本地 AI，而不是从零创建新项目。

生成本地项目上下文：

```bash
python setup_local_ai.py --project /path/to/your/project
```

只预览，不写文件：

```bash
python setup_local_ai.py --project /path/to/your/project --dry-run
```

默认会在目标项目里生成：

```text
CYBER_CODE_SHIELD_CONTEXT.md
```

内容包括：

- 语言识别
- 包管理器
- 框架和工具线索
- 测试工具
- 目录快照
- 从少量样例文件推断出的风格提示
- 给本地 AI 使用该项目时的建议

安全说明：

- 分析在本地运行。
- 会跳过 `.git`、`node_modules`、`dist`、`build`、`.venv`、`target` 等常见目录。
- 不修改业务源码。
- 除非使用 `--dry-run`，否则只写入生成的上下文 Markdown 文件。

## 本地补丁助手 MVP

Cyber-Code-Shield 可以调用本地模型，根据项目上下文生成可审查的补丁建议。Ollama 是默认 provider；补丁助手命令也支持 LM Studio、llama.cpp server、vLLM 等 OpenAI-compatible 本地服务。

根据错误日志生成修复建议：

```bash
python setup_local_ai.py --fix-error --project /path/to/project --error-log ./error.log
```

直接传入错误文本：

```bash
python setup_local_ai.py --fix-error --project /path/to/project --error-text "NameError: name 'user' is not defined"
```

`--fix-error` 可以从常见错误格式中提取文件和行号，例如：

```text
File "src/app.py", line 42, in login
src/app.py:42:13: NameError: user is not defined
```

根据任务描述生成补丁建议：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation for empty username"
```

根据 TODO / 未实现占位生成补全建议：

```bash
python setup_local_ai.py --complete-todo --project /path/to/project --files src/foo.py --chat-model gemma4-local --context-lite --patch-timeout 600
```

`--complete-todo` MVP 需要显式传入 `--files`，目前只检测明显的 `TODO`、`FIXME`、`pass`、`NotImplementedError` 和 `throw new Error("TODO")`。

限制提供给本地模型的参考文件：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files src/user.py tests/test_user.py
```

只预览 prompt，不调用 Ollama，不写文件：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --dry-run
```

写到自定义建议文件：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --patch-output ./patch-suggestion.md
```

给本地大模型更长的加载或生成时间：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --chat-model gemma4-local --patch-timeout 600
```

使用更短上下文，方便本地大模型快速验证：

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files README.md --chat-model gemma4-local --context-lite --patch-timeout 600
```

使用 OpenAI-compatible 本地服务替代 Ollama：

```bash
# LM Studio 默认本地服务
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files src/user.py --inference-provider openai-compatible --api-base http://localhost:1234/v1 --chat-model your-local-model

# llama.cpp server
python setup_local_ai.py --fix-error --project /path/to/project --error-log ./error.log --inference-provider openai-compatible --api-base http://localhost:8080/v1 --chat-model your-local-model

# vLLM OpenAI-compatible server
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --inference-provider openai-compatible --api-base http://localhost:8000/v1 --chat-model your-local-model
```

本地验证中，`gemma4-local:latest` 在内置 Python traceback 的 `--fix-error` 场景下生成了较好的修复补丁。这只是示例模型，不是硬性要求。

建议先试内置 demo：

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --context-lite --dry-run
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

默认生成的建议文件类似：

```text
CYBER_CODE_SHIELD_PATCH_FIX_ERROR_YYYYMMDD-HHMMSS.md
CYBER_CODE_SHIELD_PATCH_SUGGEST_PATCH_YYYYMMDD-HHMMSS.md
CYBER_CODE_SHIELD_PATCH_COMPLETE_TODO_YYYYMMDD-HHMMSS.md
```

安全行为：

- 补丁助手只允许使用 `localhost`、`127.0.0.1` 等本机 API。
- Ollama 仍是默认 provider；OpenAI-compatible 模式面向本地 LM Studio、llama.cpp server 和 vLLM 端点，不面向云端 API。
- 它只读取受限的项目摘要和代码片段。
- 它只写入 Markdown 建议文件。
- 它不会自动修改业务源码，也不会自动应用 patch。
- 生成文件会记录原始请求、模型、超时、上下文模式，并默认不请求 thinking 输出。

生成建议里的质量护栏：

- `Compliance evidence` 会记录工具版本、provider、模型、模型档位、上下文模式、warning 数量，以及源码不会被自动修改这一事实。
- `Confidence` 应该是 `High`、`Medium` 或 `Low`。如果是 `Low`，建议先补上下文，不要直接应用 diff。
- `Missing context` 会列出本地模型还需要的文件、日志、测试、schema 或业务规则。可以优先用 `--files` 补充这些文件。
- 如果出现 `Response warnings`，它们是非阻断提示，用来标记缺少章节、无效 no-op diff、引用未提供上下文的文件，或 `--fix-error` 没有触及主故障行等可疑输出。
- `Policy warnings` 是非阻断的企业审查信号，用来提示依赖变更、网络调用、shell 执行、secret/env 文件、CI/CD 改动，或 auth/crypto/billing/user-data 等敏感区域。
- `Risks or assumptions` 是人工审查重点，复制任何建议代码前都应该先看这里。
- 本地模型仍可能犯错，生成文件只是可审查建议，不是自主 agent 的最终修改结果。
- 按任务风险匹配模型规模：轻量模型适合快速试用，26B/31B 级模型更适合深度合规和补丁生成工作。

补丁报告选项：

```bash
# 在生成报告中记录部署档位元数据；不会自动切换模型。
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --model-tier deep --chat-model gemma4-local:latest

# 特殊流程中禁用 policy warning 扫描。
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --no-policy-warnings
```

## 高质量任务写法指南

本地模型最适合处理范围小、描述明确、相关文件少的任务。

适合从这些任务开始：

- 根据明确 traceback 或 `path:line:column` 诊断修复一个错误。
- 补全指定文件里的一个 TODO、`pass` 或 `NotImplementedError`。
- 给一个函数或命令增加小范围输入校验。
- 参考附近代码风格生成一个相似 helper 函数。
- 针对窄范围 bug 生成解释和可审查 diff。

不建议一开始就交给本地模型的任务：

- “重构整个项目”。
- “优化所有性能问题”。
- “实现完整权限系统”。
- “理解业务并重新设计架构”。
- 没有日志、文件范围或预期行为的“修好所有问题”。

一个好的任务描述通常包括：

```text
目标：
相关文件：
当前错误或未完成代码：
预期行为：
约束：
```

选择 `--files` 时建议保持克制：

- 先选目标文件。
- 必要时只增加 1-3 个直接相关文件。
- 如果有相关测试文件，可以一起传入。
- 不要一开始传整个项目。
- 如果输出质量不好，先减少上下文，再考虑增加上下文。

不好的任务：

```bash
--task "Fix this project"
```

更好的任务：

```bash
--task "Fix the NameError in app.py. The function should use the raw_username parameter, strip whitespace, and return lowercase text."
```

不好的任务：

```bash
--task "Add validation"
```

更好的任务：

```bash
--task "In app.py, validate that username is 3-20 characters and contains only letters, digits, or underscores."
```

## Continue.dev 配置兼容性

Continue.dev 当前推荐 `config.yaml`，使用 `chat`、`autocomplete`、`embed` 等 model roles。

Cyber-Code-Shield 默认写入：

```text
~/.continue/config.yaml
```

生成的 YAML 配置包括：

- chat/edit/apply/summarize 角色，用于本地聊天和重构
- autocomplete 角色，用于本地 Tab 补全
- embed 角色，使用 `nomic-embed-text` 做本地代码库 embedding

旧版 Continue.dev 可以继续使用 legacy `config.json`：

```bash
python setup_local_ai.py --config-format json --install
```

仓库模板包括：

```text
config.yaml
config.json
configs/continue/config.ollama.deepseek.yaml
configs/continue/config.ollama.deepseek.json
```

## 模型配置

默认 balanced profile：

```bash
python setup_local_ai.py --profile balanced --install
```

可用 profile：

| Profile | Chat/refactor | Autocomplete | Embedding | 适合机器 |
| --- | --- | --- | --- | --- |
| `light` | `qwen2.5-coder:7b` | `qwen2.5-coder:7b` | `nomic-embed-text` | 配置较低机器 |
| `balanced` | `deepseek-coder-v2:16b` | `deepseek-coder-v2:16b` | `nomic-embed-text` | 默认 MVP 配置 |
| `strong` | `qwen2.5-coder:32b` | `qwen2.5-coder:32b` | `nomic-embed-text` | 高性能机器 |

可以不改脚本直接覆盖模型：

```bash
python setup_local_ai.py \
  --chat-model qwen2.5-coder:14b \
  --autocomplete-model qwen2.5-coder:7b \
  --embedding-model nomic-embed-text \
  --install
```

自定义 Ollama 地址：

```bash
python setup_local_ai.py --api-base http://127.0.0.1:11434 --check
```

## 示例文件

`examples/` 目录包含示例输出和配置场景：

- `continue-before-merge.json`：合并前的 Continue.dev 配置示例
- `continue-after-merge.json`：合并本地 Ollama 设置后的 Continue.dev 配置示例
- `sample-project-context.md`：`--project PATH` 输出示例
- `sample-offline-report.md`：`--report` Markdown 输出示例

这些示例不包含真实密钥。

## 产品方向

Cyber-Code-Shield 第一版不尝试复制完整 Claude Code Agent 体验。近期方向更窄，也更现实：本地模型驱动的代码修复、TODO 补全和补丁生成。

当前 MVP 工作流示例：

```bash
python setup_local_ai.py --fix-error --project . --error-log error.log --context-lite
python setup_local_ai.py --complete-todo --project . --files src/foo.py --context-lite
python setup_local_ai.py --suggest-patch --project . --task "add input validation to the login flow" --files src/login.py
```

核心原则：先生成解释和可审查 diff，再由用户决定是否应用。

## 已知限制

- 补丁建议只是 Markdown 建议，不会自动应用。
- Cyber-Code-Shield 不是完整的本地 Claude Code 或 Cursor 替代品。
- 暂无自主多步 agent 循环，也不会自动运行测试。
- 本地模型输出质量取决于模型能力和提供的上下文。
- 上下文选择是启发式且有上限，目的是让本地推理更可控。
- `--complete-todo` 当前需要显式传入 `--files`。
- 离线报告是配置复核辅助材料，不是正式安全审计。

## 隐私与安全边界

Cyber-Code-Shield 是 local-first 工具，默认不配置云端 AI provider。

但用户和组织仍需要自行确认：

- Ollama 绑定在预期的本机或内网地址。
- Continue.dev 没有额外配置云端 provider。
- VS Code 和扩展符合公司安全策略。
- 操作系统、网络和终端环境符合内部合规要求。

本项目适合 air-gap friendly 场景，但不声称仅凭本工具即可实现绝对零泄漏。

## 项目方向和发布说明

- [PROJECT_DIRECTION.md](PROJECT_DIRECTION.md)
- [CHANGELOG.md](CHANGELOG.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
