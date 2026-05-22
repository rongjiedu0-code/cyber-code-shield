# Changelog

All notable changes to Cyber-Code-Shield will be documented in this file.

## [0.4.1] - Unreleased

v0.4.1 repositions Cyber-Code-Shield as a review-first audit layer for local AI coding and adds showcase material for enterprise evaluation.

### Added

- Added sanitized sample Markdown patch report.
- Added sanitized sample JSON patch report.
- Added enterprise pilot checklist for privacy-sensitive and strong-compliance teams.

### Changed

- Repositioned README messaging around review-first local AI coding governance and audit evidence.
- Updated product direction to prioritize audit/report/policy architecture before desktop installer work.
- Clarified that Cyber-Code-Shield is not a full autonomous coding agent or Cursor/Claude Code replacement.

### Safety

- Sample reports use sanitized project paths and synthetic model output.
- Patch suggestions remain manual-review-first and are not applied automatically.

## [0.4.0] - Unreleased

v0.4 hardens Local Patch Assistant reports as audit-friendly review artifacts while keeping the workflow local-first and manual-review-first.

### Added

- Added stable patch report IDs for generated patch suggestion reports.
- Added SHA-256 audit fingerprints for the internal prompt, model response, and reviewed project files.
- Added optional machine-readable JSON patch report output via `--patch-report-format json`.
- Added differentiated policy warning severities for higher-risk network, shell execution, and secret/env-file changes.
- Added unit tests for audit hashes, structured patch report data, JSON patch report rendering, policy severities, and parser support.

### Safety

- Patch report hashes are audit fingerprints, not encryption or anonymization.
- JSON patch reports do not include the full internal prompt, but they do include the user request and model response as review evidence.
- Patch assistant commands still do not apply patches or modify source files automatically.

## [0.3.0] - Unreleased

v0.3 strengthens the Local Patch Assistant with compliance-ready Markdown evidence and non-blocking policy warnings for enterprise review.

### Added

- Added `Compliance evidence` metadata to generated patch suggestion reports.
- Added non-blocking `Policy warnings` for dependency changes, network calls, shell execution, secret/env files, CI/CD changes, and sensitive auth/crypto/billing/user-data areas.
- Added `--model-tier {light,deep,custom}` to record deployment tier metadata in patch reports without changing model selection.
- Added `--no-policy-warnings` for workflows that need to suppress policy warning scanning.
- Added unit tests for policy warning detection and compliance report rendering.

### Safety

- Policy warnings are advisory review signals only; patches are still never applied automatically.
- v0.3 remains Markdown-report-only; JSON report output and blocking policy gates are deferred.

## [0.2.0] - Unreleased

v0.2 introduces the first Local Patch Assistant MVP on top of the local AI setup kit. It can generate reviewable Markdown suggestions for user-described changes, error fixes, and TODO completion using local Ollama models.

### Added

- Added custom lightweight YAML parser and serializer (`parse_yaml_text`, `dump_yaml_text`) to support zero-dependency YAML configuration parsing and merging.
- Added support for merging Continue.dev `config.yaml` with user configuration preservation (retaining custom slash commands, custom prompts, etc.).
- Added YAML config analysis in environment reports, mapping schema `v1` roles to local AI findings.
- Enhanced Python project dependency and framework detection by reading `requirements.txt` and `pyproject.toml` (enabling recognition of FastAPI, Flask, Django, Streamlit, unittest, and pytest).
- Added local patch assistant MVP with `--fix-error`, `--suggest-patch`, and `--complete-todo`.
- Added local Ollama `/api/chat` generation for patch suggestions with thinking output disabled.
- Added generated Markdown patch suggestion files.
- Added dry-run prompt preview for patch assistant commands.
- Added `--patch-timeout` for large local models that need longer load or generation time.
- Added `--context-lite` to reduce prompt size for faster local large-model validation.
- Added patch suggestion metadata for original request, context mode, timeout, generated token cap, and disabled thinking output.
- Added `--complete-todo` MVP for selected files with TODO/pass/NotImplemented-style markers.
- Added demo projects for first-run `--fix-error` and `--complete-todo` workflows.
- Added guidance for writing high-quality local-model tasks.
- Added lightweight quality guardrails with `Confidence` and `Missing context` sections in patch suggestions.
- Added non-blocking `Response warnings` for suspicious local-model output such as missing sections, no-op diffs, paths outside selected context, and `--fix-error` patches that miss the primary error line.
- Enhanced `--fix-error` to extract file/line locations and focused snippets from common error logs.
- Enhanced `--fix-error` prompt context with a primary error location for Python traceback repair.
- Added OpenAI-compatible local inference support for patch assistant commands, enabling LM Studio, llama.cpp server, and vLLM via `--inference-provider openai-compatible`.
- Added minimal standard-library unit tests for response validation and OpenAI-compatible helper behavior.

### Safety

- Patch assistant commands do not modify business source files.
- Patch assistant commands refuse non-local inference API bases.
- Patch context is capped to a small number of project files.
- Generated suggestions are intended for manual review and application.

### Known limitations

- Patch suggestions are Markdown suggestions only; there is no automatic apply mode.
- The tool is not a full autonomous local Claude Code agent.
- `--complete-todo` requires explicit `--files` in the MVP.
- Context selection is heuristic and intentionally capped.
- Output quality depends on the selected local model and available context.
- OpenAI-compatible support is intended for local endpoints only; provider auto-detection and streaming responses are not included.

## [0.1.0] - Unreleased

### Added

- Defined the project direction as a local-first AI coding setup kit that will evolve into a local code repair and patch assistant.
- Added local-first Continue.dev configuration for Ollama.
- Added current Continue.dev `config.yaml` template with model roles.
- Retained legacy `config.json` template for older Continue.dev setups.
- Added default balanced model profile:
  - `deepseek-coder-v2:16b` for chat/refactor
  - `deepseek-coder-v2:16b` for tab autocomplete
  - `nomic-embed-text` for embeddings
- Added replaceable model profiles:
  - `light`
  - `balanced`
  - `strong`
- Added custom model CLI flags:
  - `--chat-model`
  - `--autocomplete-model`
  - `--embedding-model`
  - `--api-base`
- Added `--check` environment diagnostics.
- Added `--install` overwrite installation mode.
- Added `--merge` safe merge mode for existing Continue.dev configs.
- Added `--config-format yaml/json`; YAML is the default and JSON is legacy.
- Added `--restore` from `config.yaml.bak` or `config.json.bak`.
- Added `--dry-run` previews for install, merge, project analysis, and reports.
- Added safe backup behavior:
  - first backup: `config.yaml.bak` or `config.json.bak`
  - later backups: timestamped `config.YYYYMMDD-HHMMSS.bak`
- Added `--project PATH` existing-project analysis.
- Added generated project context file:
  - `CYBER_CODE_SHIELD_CONTEXT.md`
- Added `--report` offline environment reports.
- Added Markdown report output:
  - `CYBER_CODE_SHIELD_REPORT.md`
- Added JSON report output:
  - `CYBER_CODE_SHIELD_REPORT.json`
- Added cloud provider hints from Continue.dev config providers.
- Added cloud AI API environment variable name detection without printing secret values.
- Added examples for merge config, project context, and offline reports.
- Added Apache-2.0 license.

### Security and privacy notes

- The project is local-first and does not configure cloud AI providers by default.
- The tool does not claim absolute zero leakage.
- The offline report is a configuration review aid, not a formal security audit.
- Environment variable checks only report variable names, never secret values.

### Known limitations

- The first release is not a full local Claude Code replacement; local patch assistant commands are introduced in v0.2.
- Continue.dev currently recommends `config.yaml`; legacy `config.json` is retained for older setups.
- Project analysis is heuristic and lightweight.
- The tool does not install Ollama, VS Code, Continue.dev, or local models automatically.
- The tool does not fine-tune or train models.
