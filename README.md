# Cyber-Code-Shield

English | [简体中文](README.zh-CN.md)

Cyber-Code-Shield is a local-first AI coding setup kit and patch assistant for developers and teams working in privacy-sensitive or strong-compliance environments.

It helps you keep AI coding useful when cloud AI tools are restricted or not allowed:

- configure local Ollama + Continue.dev for VS Code
- check local AI environment readiness
- analyze existing projects and generate local project context
- generate reviewable patch suggestions from local models
- fix errors with file/line context from stack traces or diagnostics
- complete TODO, `pass`, and `NotImplementedError` placeholders
- keep source changes manual and reviewable

> Goal: preserve AI coding productivity without sending project code, logs, or business context to cloud AI providers.

## Who is this for?

Cyber-Code-Shield is designed for developers who have experienced the productivity benefits of AI coding, but work in environments where source code, logs, documents, or business data cannot be sent to cloud AI providers.

Typical scenarios:

- Enterprise internal development
- Financial, government, manufacturing, medical, or regulated environments
- Air-gapped or intranet-only workstations
- Teams where Copilot, Cursor, ChatGPT, or cloud AI coding tools are restricted

## Quick demo

Check local readiness:

```bash
python setup_local_ai.py --check
```

Try the bundled error-fix demo without calling Ollama:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --context-lite --dry-run
```

Try the bundled TODO-completion demo without calling Ollama:

```bash
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

Generate a reviewable patch suggestion for your own project:

```bash
python setup_local_ai.py --suggest-patch --project . --task "Add input validation" --files README.md --dry-run
```

## Current status

This project is an early v0.2 MVP.

| Capability | Status | Command | Source writes |
| --- | --- | --- | --- |
| Environment check | Done | `--check` | No |
| Continue.dev config | Done | `--merge`, `--install`, `--restore` | Config only |
| Project context | Done | `--project` | Context file only |
| Offline report | Done | `--report` | Report file only |
| Patch suggestion | Done | `--suggest-patch` | No source writes |
| Error repair suggestion | Done | `--fix-error` | No source writes |
| TODO completion suggestion | Done | `--complete-todo` | No source writes |
| Auto-apply patch | Not included | N/A | N/A |
| Full local Claude Code agent | Not included | N/A | N/A |

> **Note:** Patch suggestions are not applied automatically. Review the generated Markdown file and apply any changes manually.

Planned next:

- Similar-module patch generation that follows the current codebase style
- More precise context selection and snippet trimming
- Enterprise deployment and compliance documentation
- More detailed framework/style detection
- Desktop installer prototype

## Requirements

Before using the generated Continue.dev config, install:

1. VS Code
2. Continue.dev extension
3. Ollama
4. Required local models for your chosen profile

Default balanced profile:

```bash
ollama pull deepseek-coder-v2:16b
ollama pull nomic-embed-text
```

Light profile:

```bash
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

Strong profile:

```bash
ollama pull qwen2.5-coder:32b
ollama pull nomic-embed-text
```

### Local model deployment tiers

Cyber-Code-Shield is designed to let teams choose a local model tier that matches their hardware and compliance depth:

| Tier | Typical use | Hardware fit | Example model class |
| --- | --- | --- | --- |
| Light / Trial | Quick local trials, demos, simple fixes, low-friction validation | Developer laptops or low-VRAM test machines | E4B / 7B-class models |
| Deep Compliance | Higher-quality error repair, compliance review, complex patch suggestions | Enterprise workstations or servers with larger VRAM | Gemma 4 26B/31B-class models |

For patch assistant workflows such as `--fix-error` and `--suggest-patch`, stronger 26B/31B-class local models usually provide better reasoning and more stable diffs. Smaller models are still useful for fast checks, especially with `--context-lite`, but users should review `Response warnings` carefully.

Model names depend on the tags configured in your local Ollama, LM Studio, llama.cpp server, or vLLM environment. Use `--chat-model` with the exact local model name exposed by your inference server.

## Quick start

Check your local environment first:

```bash
python setup_local_ai.py --check
```

Preview what will be written without changing files:

```bash
python setup_local_ai.py --dry-run
```

By default, Cyber-Code-Shield writes Continue's current recommended `config.yaml` format. Legacy `config.json` is still available:

```bash
python setup_local_ai.py --config-format json --dry-run
```

Merge the local Continue.dev config into your existing config:

```bash
python setup_local_ai.py --merge
```

Or overwrite the Continue.dev config completely:

```bash
python setup_local_ai.py --install
```

Restore your previous Continue.dev config if needed:

```bash
python setup_local_ai.py --restore
```

If you run the script without arguments, it defaults to install mode:

```bash
python setup_local_ai.py
```

Recommended mode:

- Use `--merge` if you already have Continue.dev configured and want to keep existing providers/settings.
- Use `--install` if you want a clean local-only Continue.dev config.
- Use `--dry-run` with either mode to preview the result first.

The install command will:

1. Detect your operating system.
2. Locate `~/.continue/config.yaml` by default, or `config.json` when `--config-format json` is used.
3. Back up the existing config to `config.yaml.bak` or `config.json.bak` if it exists.
4. Write a local Ollama-based Continue.dev config.

For the current YAML format, `--merge` behaves like safe install because Continue YAML is structured around model roles. For legacy JSON, the merge command will:

1. Read your existing Continue.dev config.
2. Preserve existing config fields and model providers.
3. Add or update the Cyber-Code-Shield local Ollama model entry.
4. Update autocomplete, embeddings, and codebase indexing to local Ollama.

Then restart VS Code and use Continue.dev with `@Codebase`.

## Offline environment report

Generate a local report for developers, IT administrators, or security reviewers:

```bash
python setup_local_ai.py --report
```

Preview the report without writing a file:

```bash
python setup_local_ai.py --report --dry-run
```

Write the report to a custom path:

```bash
python setup_local_ai.py --report --report-output ./local-ai-report.md
```

Generate a machine-readable JSON report:

```bash
python setup_local_ai.py --report --report-format json
```

The default output files are:

```text
CYBER_CODE_SHIELD_REPORT.md
CYBER_CODE_SHIELD_REPORT.json
```

The report includes:

- OS and Python version
- Continue.dev config path and backup path
- Ollama CLI and service status
- selected local model configuration
- required and missing Ollama models
- whether the Ollama API base points to localhost
- whether local autocomplete, embeddings, and codebase indexing are configured
- Continue.dev provider names detected in the config
- cloud provider hints that should be reviewed before strict-compliance use
- common cloud AI API environment variable names if they are present

The script only reports environment variable names, never secret values.

This report is a configuration review aid, not a formal security audit.

## Existing project analysis

Most users will use local AI inside an existing work project, not a blank new project. This feature is also the foundation for the planned local patch assistant, where local models need a compact project summary before generating fixes or code completions.

Generate a local project context summary:

```bash
python setup_local_ai.py --project /path/to/your/project
```

Preview the summary without writing files:

```bash
python setup_local_ai.py --project /path/to/your/project --dry-run
```

The command creates this file inside the target project:

```text
CYBER_CODE_SHIELD_CONTEXT.md
```

It summarizes:

- detected languages
- package managers
- framework and tool hints
- test tools
- directory snapshot
- style hints from a small sample of source files
- guidance for local AI coding inside that project

Safety notes:

- It runs locally.
- It skips common dependency/build folders such as `.git`, `node_modules`, `dist`, `build`, `.venv`, and `target`.
- It does not modify business source code.
- It only writes the generated context markdown file unless `--dry-run` is used.

## Local patch assistant MVP

Cyber-Code-Shield can ask a local model to generate reviewable patch suggestions from project context. Ollama is the default provider; OpenAI-compatible local servers such as LM Studio, llama.cpp server, and vLLM are also supported for patch assistant commands.

Generate a fix suggestion from an error log:

```bash
python setup_local_ai.py --fix-error --project /path/to/project --error-log ./error.log
```

Pass error text directly:

```bash
python setup_local_ai.py --fix-error --project /path/to/project --error-text "NameError: name 'user' is not defined"
```

`--fix-error` can extract focused context from common file/line diagnostics, such as Python tracebacks and `path:line:column` messages:

```text
File "src/app.py", line 42, in login
src/app.py:42:13: NameError: user is not defined
```

Generate a patch suggestion from a task description:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation for empty username"
```

Generate a completion suggestion for explicit TODO or incomplete-code markers:

```bash
python setup_local_ai.py --complete-todo --project /path/to/project --files src/foo.py --chat-model gemma4-local --context-lite --patch-timeout 600
```

`--complete-todo` MVP requires `--files` and detects obvious markers such as `TODO`, `FIXME`, `pass`, `NotImplementedError`, and `throw new Error("TODO")`.

Limit the files shown to the local model:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files src/user.py tests/test_user.py
```

Preview the prompt without calling Ollama or writing files:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --dry-run
```

Write the generated suggestion to a custom path:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --patch-output ./patch-suggestion.md
```

Give large local models more time to load or generate:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --chat-model gemma4-local --patch-timeout 600
```

Use a smaller prompt for local large-model validation:

```bash
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files README.md --chat-model gemma4-local --context-lite --patch-timeout 600
```

Use an OpenAI-compatible local server instead of Ollama:

```bash
# LM Studio default local server
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Add validation" --files src/user.py --inference-provider openai-compatible --api-base http://localhost:1234/v1 --chat-model your-local-model

# llama.cpp server
python setup_local_ai.py --fix-error --project /path/to/project --error-log ./error.log --inference-provider openai-compatible --api-base http://localhost:8080/v1 --chat-model your-local-model

# vLLM OpenAI-compatible server
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --inference-provider openai-compatible --api-base http://localhost:8000/v1 --chat-model your-local-model
```

In local verification, `gemma4-local:latest` produced a good `--fix-error` patch for the bundled Python traceback demo. This is an example model, not a hard requirement.

Try the bundled demos first:

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/error.log --context-lite --dry-run
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

By default, generated suggestions are written inside the target project:

```text
CYBER_CODE_SHIELD_PATCH_FIX_ERROR_YYYYMMDD-HHMMSS.md
CYBER_CODE_SHIELD_PATCH_SUGGEST_PATCH_YYYYMMDD-HHMMSS.md
CYBER_CODE_SHIELD_PATCH_COMPLETE_TODO_YYYYMMDD-HHMMSS.md
```

Safety behavior:

- Patch assistant commands only allow local API bases such as `localhost` or `127.0.0.1`.
- Ollama remains the default; OpenAI-compatible mode is intended for local LM Studio, llama.cpp server, and vLLM endpoints, not cloud APIs.
- They read a limited project summary and capped file snippets.
- They write only a generated Markdown suggestion file.
- They do not modify business source files or apply patches automatically.
- Review the suggested diff before making any source change.
- Use `--patch-timeout` for large models that need longer first-load or generation time.
- Use `--context-lite` to reduce project context, file snippets, and generated length for faster local validation.
- Patch suggestion files include the original request, selected model, timeout, context mode, and note that thinking output is not requested.

Quality guardrails in generated suggestions:

- `Compliance evidence` records tool version, provider, model, model tier, context mode, warning counts, and the fact that source files were not modified automatically.
- `Confidence` should be `High`, `Medium`, or `Low`. Treat `Low` as a signal to provide more context before applying any diff.
- `Missing context` lists files, logs, tests, schemas, or business rules the local model still needs. Add those with `--files` when possible.
- `Response warnings`, when present, are non-blocking checks for suspicious model output such as missing sections, no-op diffs, paths outside the provided context, or a `--fix-error` patch that does not touch the primary error line.
- `Policy warnings` are non-blocking enterprise review signals for dependency changes, network calls, shell execution, secret/env files, CI/CD changes, or sensitive auth/crypto/billing/user-data areas.
- `Risks or assumptions` is the review checklist. Read it before copying any suggested code.
- Local models may still make mistakes. The generated file is a reviewable suggestion, not an autonomous agent result.
- Match model size to task risk: lightweight models are good for quick trials, while 26B/31B-class models are better suited to deeper compliance and patch-generation work.

Patch report options:

```bash
# Record deployment tier metadata in the generated report; this does not switch models automatically.
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --model-tier deep --chat-model gemma4-local:latest

# Disable policy warning scanning for a special workflow.
python setup_local_ai.py --suggest-patch --project /path/to/project --task "Fix bug" --no-policy-warnings
```

## Writing good local-model tasks

Local models work best when the task is small, explicit, and tied to a few relevant files.

Good first tasks:

- Fix one error with a concrete traceback or `path:line:column` diagnostic.
- Complete one TODO, `pass`, or `NotImplementedError` in a selected file.
- Add small input validation to one function or command.
- Generate a similar helper function from nearby code style.
- Explain and suggest a reviewable diff for a narrow bug.

Avoid starting with broad tasks such as:

- "Refactor the whole project."
- "Optimize all performance problems."
- "Implement a full permission system."
- "Understand the business and redesign the architecture."
- "Fix everything" without logs, files, or expected behavior.

A useful task description usually includes:

```text
Goal:
Files:
Current error or incomplete code:
Expected behavior:
Constraints:
```

Choose `--files` narrowly:

- Start with the target file.
- Add only 1-3 directly related files if needed.
- Include a relevant test file when it exists.
- Do not pass the whole project at first.
- If output quality is poor, reduce context before adding more context.

Poor task:

```bash
--task "Fix this project"
```

Better task:

```bash
--task "Fix the NameError in app.py. The function should use the raw_username parameter, strip whitespace, and return lowercase text."
```

Poor task:

```bash
--task "Add validation"
```

Better task:

```bash
--task "In app.py, validate that username is 3-20 characters and contains only letters, digits, or underscores."
```

## Continue.dev config compatibility

Continue.dev now recommends `config.yaml` with model roles such as `chat`, `autocomplete`, and `embed`.

Cyber-Code-Shield therefore defaults to:

```text
~/.continue/config.yaml
```

The generated YAML config defines:

- chat/edit/apply/summarize model roles for local chat and refactoring
- autocomplete role for local Tab completion
- embed role for local codebase embeddings with `nomic-embed-text`

Legacy `config.json` remains available for older Continue.dev setups:

```bash
python setup_local_ai.py --config-format json --install
```

Repository templates:

```text
config.yaml
config.json
configs/continue/config.ollama.deepseek.yaml
configs/continue/config.ollama.deepseek.json
```

## Model profiles

Cyber-Code-Shield defaults to the balanced profile:

```bash
python setup_local_ai.py --profile balanced --install
```

Available profiles:

| Profile | Chat/refactor | Autocomplete | Embedding | Intended machine |
| --- | --- | --- | --- | --- |
| `light` | `qwen2.5-coder:7b` | `qwen2.5-coder:7b` | `nomic-embed-text` | Lower-spec machines |
| `balanced` | `deepseek-coder-v2:16b` | `deepseek-coder-v2:16b` | `nomic-embed-text` | Default MVP setup |
| `strong` | `qwen2.5-coder:32b` | `qwen2.5-coder:32b` | `nomic-embed-text` | High-performance machines |

You can override models directly without editing the script:

```bash
python setup_local_ai.py \
  --chat-model qwen2.5-coder:14b \
  --autocomplete-model qwen2.5-coder:7b \
  --embedding-model nomic-embed-text \
  --install
```

Use a custom Ollama endpoint if needed:

```bash
python setup_local_ai.py --api-base http://127.0.0.1:11434 --check
```

## Examples

The `examples/` directory contains sample outputs and configuration scenarios:

- `continue-before-merge.json`: example existing Continue.dev config before Cyber-Code-Shield merge
- `continue-after-merge.json`: example Continue.dev config after local Ollama settings are merged
- `sample-project-context.md`: example output from `--project PATH`
- `sample-offline-report.md`: example Markdown output from `--report`

These examples are illustrative and do not contain real credentials.

## Product direction

Cyber-Code-Shield is intentionally not trying to clone the full Claude Code agent experience in its first release. The practical near-term direction is narrower: local model driven code repair, TODO completion, and patch generation.

Current MVP workflow examples:

```bash
python setup_local_ai.py --fix-error --project . --error-log error.log --context-lite
python setup_local_ai.py --complete-todo --project . --files src/foo.py --context-lite
python setup_local_ai.py --suggest-patch --project . --task "add input validation to the login flow" --files src/login.py
```

The intended behavior is to produce explanations and reviewable diffs first. Writing changes to the project should require explicit user confirmation, backup, or dry-run style safety checks.

## Known limitations

- Patch suggestions are Markdown suggestions only; they are not applied automatically.
- Cyber-Code-Shield is not a full local Claude Code or Cursor replacement.
- There is no autonomous multi-step agent loop or automatic test execution yet.
- Local model output quality depends on the selected model and available context.
- Context selection is capped and heuristic to keep local inference practical.
- `--complete-todo` currently requires explicit `--files` and only detects obvious incomplete-code markers.
- Offline reports are configuration review aids, not formal security audits.

## Privacy positioning

Cyber-Code-Shield is local-first and does not configure cloud AI providers by default.

However, users and organizations should still verify:

- Ollama is bound to the expected local or internal address.
- Continue.dev has no additional cloud providers configured.
- VS Code and extensions comply with internal security policies.
- The environment is configured according to company compliance requirements.

This project is designed to be air-gap friendly, but does not claim absolute zero-leakage by itself.

## Project direction and release notes

- [PROJECT_DIRECTION.md](PROJECT_DIRECTION.md)
- [CHANGELOG.md](CHANGELOG.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
