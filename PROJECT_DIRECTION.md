# Cyber-Code-Shield 项目方向

## 1. 项目一句话定位

Cyber-Code-Shield 是面向本地 AI Coding 的审查优先审计层和治理工具包，帮助强合规团队把本地模型生成的代码建议变成可人工审查、可审计留痕、可策略复核的补丁报告。

它不是单纯的模型配置文件，也不是完整 Claude Code / Cursor 替代品。当前重点是让企业、内网和隐私敏感团队在使用本地代码模型时，有一条清晰的 review-first 流程：本地模型生成建议，Cyber-Code-Shield 记录证据和 policy 信号，人类审查后再决定是否应用。

核心组合：

- Ollama / 本地 OpenAI-compatible 服务：本地运行代码模型
- Continue.dev：在 VS Code 中提供本地 AI 编程入口
- 本地代码库上下文：为补丁建议提供受控、有限的项目上下文
- 安装/检测脚本：降低普通用户和企业 IT 部署门槛
- 补丁报告与审计层：生成 Markdown/JSON patch reports，记录 report ID、hashes、warnings 和人工复核线索

---

## 2. 目标用户与需求判断

### 2.1 目标用户

第一批目标用户不是普通 AI 尝鲜者，而是：

- 在强合规环境中工作的程序员
- 已经体验过 AI 编程效率提升的人
- 因为公司、行业或项目限制，不能使用联网 AI 编程工具的人
- 所在环境可能涉及金融、政企、制造、军工、医疗、内网研发、涉密或数据敏感业务

这些用户已经知道 AI Coding 有价值，所以教育成本相对低；真正的问题不是“AI 编程有没有用”，而是“怎样在合规边界内继续使用”。

### 2.2 核心痛点

他们的主要痛点：

1. 代码、日志、需求、接口文档或业务数据不能上传云端。
2. 公司禁用 Copilot、Cursor、ChatGPT、Claude 等联网 AI 工具。
3. 本地模型和插件配置门槛高，个人很难一次性装好。
4. 企业 IT 或安全团队需要可解释、可审计、可恢复的部署方案。
5. 用户想保留 AI 编程体验，但不能违反公司合规要求。

### 2.3 项目提供的价值

Cyber-Code-Shield 要提供的是“本地 AI Coding 的治理和审计能力”，而不是简单宣传模型能力。

短期价值主张：

- 帮用户在不能用联网 AI 的环境里继续获得 AI Coding 能力
- 默认不配置云端模型提供商
- 把安装、检测、配置、恢复流程产品化
- 让补丁建议以报告形式留痕，而不是直接修改业务源码
- 让开发、安全和合规团队能查看 report ID、hashes、policy warnings 和 response warnings

中期价值主张：

- 用本地模型读取受控项目上下文，辅助定位报错和生成修复建议
- 根据 TODO、空函数、相似模块生成可审查代码补丁报告
- 先输出 diff、解释和审计证据，由用户确认后再手动应用
- 提供比通用 Continue.dev 配置更明确的“本地 AI 代码建议治理”工作流

### 2.4 商业化初步判断

这类用户的付费意愿可能不低，因为他们面临的是生产力损失和合规限制，不只是普通工具偏好。

潜在付费形态：

- 桌面安装器：面向个人或小团队，降低部署门槛
- 企业部署包：面向公司内网、IT 管理员、安全团队
- 付费文档/部署指南：面向需要合规说明和落地手册的团队
- 咨询/交付服务：帮助企业完成离线部署、环境检查和培训

收费方式暂未确定，后续需要结合目标用户触达方式、交付成本和授权模式继续讨论。

### 2.5 产品边界

当前明确不做：

- 不碰模型微调
- 不训练自有模型
- 不承诺绝对安全或绝对零泄漏
- 不声称正式安全认证
- 不一开始做复杂平台
- 不复制完整 Claude Code / Cursor 的 agent 能力
- 不做自动 apply patch
- 不把公网云模型 provider 作为默认方向
- 不自研实时 autocomplete 插件，实时补全优先交给 Continue.dev

优先方向：

- 本地模型环境检测
- Continue.dev 配置安装与恢复
- 企业合规场景的说明、检查和交付材料
- 本地 patch suggestions 的审计报告、policy warning 和 response validation
- 以可审查报告为核心，而不是让本地模型直接大范围自动改项目

---

## 3. 当前阶段目标

先做一个可以发布到 GitHub 的 MVP，而不是一开始就做复杂商业系统或完整本地 Claude Code。

v0.1 MVP 目标：

1. 用户能看懂项目是干什么的。
2. 用户能一键检测本机环境。
3. 用户能一键安装 Continue.dev 本地配置。
4. 用户能安全备份和恢复原配置。
5. 用户能确认默认 AI 能力都走本机 Ollama。
6. 用户能生成项目上下文和离线环境报告，为后续本地补丁助手打底。

v0.2+ 产品目标：

1. 用户能把报错信息交给本地模型，获得修复解释和可审查 diff。
2. 用户能让工具根据 TODO、空函数或指定文件补全代码。
3. 用户能让工具参考现有模块风格生成相似代码补丁。
4. 工具默认先建议、不直接改；需要写入时必须有 dry-run、备份或确认机制。

最小可发布版本应该做到：

```bash
python setup_local_ai.py --check
python setup_local_ai.py --merge
python setup_local_ai.py --install
python setup_local_ai.py --restore
```

默认推荐真实用户优先使用 `--merge`，保留已有 Continue.dev 配置；`--install` 用于需要干净本地配置的场景。

---

## 3. 产品核心卖点

### 3.1 Local-first

默认只使用本机服务：

- Chat/refactor：`deepseek-coder-v2:16b`
- Tab autocomplete：`deepseek-coder-v2:16b`
- Embedding：`nomic-embed-text`
- API base：`http://localhost:11434`

### 3.2 Air-gap friendly

项目要适合离线、内网、隔离环境部署。

注意措辞：不要过度宣传“绝对 100% 零泄漏”。更稳妥的说法是：

- local-first
- air-gap friendly
- designed for privacy-sensitive coding environments
- no cloud provider configured by default

### 3.3 Safe configuration

安装脚本不能粗暴覆盖用户已有配置，必须提供：

- 自动备份
- 可恢复
- 可 dry-run
- 可检查
- 可 merge 到已有 Continue 配置，而不是只能完全覆盖
- 重复运行时不能覆盖第一次备份

### 3.4 Existing-project aware

真实工作场景里，大多数用户不是从零创建新项目，而是在已有项目中继续开发。

因此项目后续应该增强“读取旧项目/现有项目”的能力：

- 扫描目标项目的文件结构、语言、框架和包管理器
- 识别代码风格、命名习惯、测试习惯和目录约定
- 生成本地项目上下文摘要，帮助本地 AI 更贴近原项目继续写代码
- 尽量只读取必要的代码结构和样例，避免把整个项目复制到工具目录
- 结合 Continue.dev 的本地 codebase index，让用户在原项目里直接获得更贴近工作的 AI 辅助

这个方向比“只帮用户创建新项目”更贴近真实工作，因为强合规用户通常手头已经有业务项目。

### 3.5 Local Patch Assistant

长期愿景不是停留在配置 Continue.dev，而是做一个降级但可落地的本地代码助手：本地模型读取项目上下文，根据用户指定的问题生成可审查代码补丁。

优先场景：

1. 根据报错修复：用户提供错误日志，工具读取相关项目上下文，输出原因解释和 diff。
2. 根据 TODO / 空函数补代码：工具在有限上下文内补实现，而不是全项目自由发挥。
3. 根据相似模块续写：工具参考已有 controller/service/test 风格，生成同风格补丁。

设计原则：

- 不追求一开始达到 Claude Code 的完整 agent 水平。
- 不做实时 autocomplete；实时补全优先由 Continue.dev 负责。
- 以任务式补全和修复为主，例如 `fix-error`、`complete-todo`、`suggest-patch`。
- 默认输出 patch/diff 和解释，用户确认后再写入。
- 每次写入前保留备份或可恢复路径。

### 3.6 输出质量护栏

后续补丁建议文件应逐步增加质量护栏，帮助用户判断本地模型是否真的有足够上下文，而不是在不确定时硬编答案。

建议固定输出：

- Confidence：高 / 中 / 低。
- Missing context：还缺哪些上下文。
- Files needed：建议用户补充哪些文件。
- Risks / assumptions：当前建议的风险和假设。
- Suggested verification：建议如何验证改动。
- If uncertain, say so：不确定时明确说明，而不是伪造 diff。

这个方向比继续堆新命令更重要，因为目标用户已经体验过云端 AI Coding；他们更关心在受限环境里能不能稳定节省时间。

---

## 4. 推荐项目结构

后续逐步整理为：

```text
cyber-code-shield/
  README.md
  PROJECT_DIRECTION.md
  setup_local_ai.py
  config.yaml
  config.json
  configs/
    continue/
      config.ollama.deepseek.yaml
      config.ollama.deepseek.json
  scripts/
    check_environment.py
  examples/
    demo-buggy-project/
    demo-todo-project/
    sample-continue-config.json
  LICENSE
  .gitignore
```

当前可以先保留简单结构，等功能稳定后再整理目录。

---

## 5. setup_local_ai.py 后续要增强的能力

当前脚本已经能：

- 自动识别 OS
- 默认定位 `~/.continue/config.yaml`
- 支持 `--config-format json` 使用 legacy `~/.continue/config.json`
- 检查 Ollama 命令、服务和模型
- 支持 `--install` 覆盖安装
- 支持 `--merge` 合并到已有 Continue.dev 配置
- 支持 `--restore` 从主备份恢复
- 支持 `--dry-run` 预览写入内容
- 支持模型 profile 和自定义模型参数
- 支持 `--project PATH` 分析已有项目并生成 `CYBER_CODE_SHIELD_CONTEXT.md`
- 支持 `--report` 生成本地 AI 环境离线报告 `CYBER_CODE_SHIELD_REPORT.md` 或 JSON 报告
- 首次备份到 `config.yaml.bak` 或 `config.json.bak`，后续备份使用时间戳，避免覆盖第一次备份

后续建议增强：

1. `--check`
   - 检查 Python 版本
   - 检查 Ollama 是否安装
   - 检查 Ollama 服务是否启动
   - 检查模型是否已拉取
   - 检查 Continue 配置路径

2. `--install`
   - 写入配置
   - 自动备份旧配置
   - 输出后续操作提示

3. `--restore`
   - 从 `config.yaml.bak` 或 `config.json.bak` 恢复原配置

4. `--dry-run`
   - 只展示将要写入的路径和配置，不实际修改文件

5. `--merge`
   - 把本地 Ollama 模型追加进已有 Continue 配置
   - 比覆盖配置更适合真实用户
   - 如果重复运行，更新 Cyber-Code-Shield 自己的模型项，不重复堆积

6. `--project PATH`
   - 分析已有项目的语言、框架、包管理器、测试工具和目录结构
   - 从少量样例代码推断缩进、分号和代码组织线索
   - 生成 `CYBER_CODE_SHIELD_CONTEXT.md`
   - 默认不修改业务源代码

7. `--report`
   - 生成本地 AI 环境离线报告 `CYBER_CODE_SHIELD_REPORT.md`
   - 支持 `--report-format markdown/json`
   - 检查 Ollama 命令、服务、模型和 API 地址
   - 检查 Continue.dev 配置中的 provider、local autocomplete、local embeddings 和 codebase index
   - 标记可能需要合规复核的云端 provider 线索
   - 检测常见云端 AI API 环境变量是否存在，但不读取或输出密钥值
   - 报告用于配置复核，不等同正式安全审计

---

## 6. Continue.dev 配置兼容性

已核对：Continue.dev 当前推荐 `config.yaml`，legacy `config.json` 已被官方文档标记为 deprecated。

当前策略：

- 默认生成 `~/.continue/config.yaml`
- 使用 model roles：`chat`、`edit`、`apply`、`summarize`、`autocomplete`、`embed`
- 本地 embedding 使用 Ollama `nomic-embed-text` 和 `embed` role
- 保留 `--config-format json` 支持旧版 Continue.dev `config.json`

每次发布前仍要验证：

- Continue.dev 是否仍支持当前 YAML 字段
- Ollama provider 字段是否正确
- roles 是否仍为推荐方式
- embed/autocomplete options 是否仍然有效

---

## 7. 发布版本路线

### v0.1 MVP

目标：能发布、能安装、能恢复。

包含：

- README
- PROJECT_DIRECTION
- LICENSE（Apache-2.0）
- setup_local_ai.py
- config.yaml
- config.json
- 环境检测
- 安装/合并/恢复/dry-run

### v0.2 本地代码纠错助手

目标：在本地 AI 环境底座之上，增加第一个真正面向代码修改的能力。

当前 MVP 已包含：

- `suggest-patch`：根据用户描述生成可审查 Markdown 补丁建议
- `fix-error`：根据错误日志、项目结构和相关文件生成修复建议，并支持轻量文件/行号诊断提取
- `complete-todo`：根据指定文件中的 TODO/pass/NotImplemented 标记生成补全建议
- `--context-lite`：降低 prompt 体积，方便本地大模型验证
- `--patch-timeout`：适配本地大模型首次加载或长时间生成
- 默认只输出 Markdown 补丁建议，不直接写入业务代码
- 支持 `--dry-run` 预览 prompt，支持输出 patch suggestion 文件

### v0.3 本地代码补全 / 项目续写

目标：更接近“根据原项目补代码”的体验。

增加：

- `complete-todo`：根据 TODO、pass、空函数或指定 symbol 补实现；当前 MVP 已开始支持指定文件中的 TODO/pass/NotImplemented 标记
- `complete-file`：在指定文件内生成局部补全建议
- `add-similar`：参考已有模块生成相似 controller/service/test 补丁
- 更强的相关文件选择和上下文裁剪，避免把整个项目塞给本地模型
- 生成 patch 后由用户确认再写入

### v0.4 审计友好补丁报告

目标：把本地补丁助手生成的报告升级成更适合企业复核和留痕的证据工件。

当前已支持轻量版 `--report` 和合规版 patch Markdown 报告。

增加：

- Patch report ID
- Prompt SHA-256 和模型响应 SHA-256
- 已审查文件 SHA-256 和字节大小
- 机器可读 JSON patch report
- Policy warning severity levels
- 更完整的 report/policy 边界测试
- 明确说明 hash 是审计 fingerprint，不是加密或匿名化

### v0.4.1 产品定位与审计示例

目标：把项目从“本地 AI 编程助手/补丁助手”明确调整为“本地 AI Coding 的审查优先审计层”。

包含：

- README 首屏定位更新
- 中文 README 同步
- 示例 Markdown patch report
- 示例 JSON patch report
- 企业试点 checklist
- 发布 checklist 更新
- changelog 更新
- 明确 sample report 是展示材料，不是正式安全认证

### v0.5 CLI 架构拆分与审计引擎基础

目标：在不改变 CLI 行为的前提下，把当前单脚本内已经形成的治理能力拆成更清晰的内部模块，为后续 policy profile、risk score、report bundle 和企业流程集成做准备。

v0.5 第一阶段已完成：

- `patch_report`：report ID、hashes、schema、Markdown/JSON rendering
- `policy_warnings`：policy warning detection、severity、企业复核信号
- `validation`：response sections、diff sanity、path/context checks
- `hashing` / `serialization` / `patch_parsing` / `error_locations`：审计与校验辅助能力

后续继续拆分：

- `inference`：Ollama 和 OpenAI-compatible 本地推理客户端
- `project_context`：项目扫描、上下文摘要、snippet 选择
- `cli`：命令行参数和 orchestration entrypoint

目标结构草案：

```text
cyber_code_shield/
  cli.py
  config.py
  environment_report.py
  project_context.py
  patch_assistant.py
  patch_report.py
  policy_warnings.py
  validation.py
  inference/
    ollama.py
    openai_compatible.py
```

桌面安装器后置，等 CLI 内部结构和审计核心稳定后再考虑。

### v0.6 Policy profiles 与 report bundle

v0.6 的主线不是继续做更像 Agent 的自动编程能力，而是把 Cyber-Code-Shield 从“补丁建议报告工具”推进到“本地 AI Coding 审查证据生成器”。

核心目标：

- 引入可配置 `policy profile`，把固定 policy warnings 变成面向不同复核场景的规则集合。
- 引入 `report bundle`，把 Markdown/JSON 报告、policy warnings、validation warnings、reviewed file hashes、environment summary 和 manifest 打包成一组可保存证据。
- 保持 review-first 和 manual-apply 边界，不做自动 apply patch。
- 明确项目不是正式合规认证工具，而是为安全、IT、合规和研发团队生成本地复核证据。

建议优先 profile：

- `basic`：当前默认 warning 行为。
- `enterprise-strict`：提高 secret、shell、network、dependency、CI/CD 等高风险变更的复核优先级。
- `china-privacy`：强调个人信息、日志、API key、云端 provider、可能的数据出境路径。
- `supply-chain`：强调 dependency、lockfile、package scripts、CI/CD、Dockerfile 和构建链路。

建议 report bundle 结构：

```text
CYBER_CODE_SHIELD_BUNDLE_YYYYMMDD-HHMMSS/
  report.md
  report.json
  reviewed-files.json
  policy-warnings.json
  validation-warnings.json
  environment-summary.json
  manifest.json
```

`manifest.json` 应记录 bundle ID、report ID、tool version、generated_at、model、inference provider、api base、reviewed file hashes、report hashes，以及 `source_files_modified_automatically: false`。

---

## 8. 当前优先级

下一步优先做这几件事：

1. 按 `RELEASE_CHECKLIST.md` 跑一遍非破坏性验证命令，确认 v0.5 架构拆分没有改变 CLI 行为。
2. v0.6 优先做 `policy profile` 和 `report bundle`，把项目推进到“本地 AI Coding 审查证据生成器”。
3. 继续完成 `inference`、`project_context` 和 `cli` 的低风险拆分，但不要为了拆分而重写业务逻辑。
4. 继续优化上下文选择和 snippet 裁剪，让本地模型输入更聚焦。
5. 后续再考虑 `add-similar`、risk score、企业部署材料和桌面安装器。
6. 暂不做自动 apply，除非补丁生成质量和回滚机制足够稳定。

---

## 9. 协作约定

以后继续这个项目时，先读这个文件，确认方向没有变。

如果项目方向发生变化，优先更新本文件，而不是只在聊天里说。

沟通方式：

- 英文材料按英文理解
- 和用户交流保持中文
- 优先给出能落地的文件、命令和代码
- 不要一开始做过重架构，先把 MVP 跑通

---

## 10. 当前项目状态

当前工作区已经生成：

- `README.md`
- `CHANGELOG.md`
- `RELEASE_CHECKLIST.md`
- `LICENSE`
- `config.yaml`
- `config.json`
- `configs/`
- `setup_local_ai.py`
- `PROJECT_DIRECTION.md`
- `examples/`

当前 CLI、JSON 配置、examples 和 Local Patch Assistant dry-run 已经做过基础验证。

当前补丁助手能力包括：

- `--suggest-patch`
- `--fix-error`，包含轻量文件/行号诊断提取
- `--complete-todo`，指定文件 MVP
- `--context-lite`
- `--patch-timeout`

下一次继续工作时，可以优先按 `RELEASE_CHECKLIST.md` 做 v0.2.0 发布前检查，或继续优化上下文选择和发布材料。
