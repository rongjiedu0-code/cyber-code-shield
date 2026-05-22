# Cyber-Code-Shield Release Checklist

Current target: v0.4.1 review-first audit positioning and showcase artifacts.

Use this checklist before publishing the current public release. The v0.1 sections are baseline setup-kit checks, the v0.2 section covers the Local Patch Assistant MVP, v0.3 covers compliance-ready patch reports and policy warnings, v0.4 covers audit trail hardening and JSON patch reports, and v0.4.1 covers product positioning and enterprise evaluation material.

## 1. Product positioning

- [ ] README clearly explains the target user: developers in privacy-sensitive or strong-compliance environments.
- [ ] README does not claim absolute zero leakage.
- [ ] README positions the project as local-first and air-gap friendly.
- [ ] README explains that the report is a configuration review aid, not a formal security audit.

## 2. Core CLI behavior

- [ ] `python setup_local_ai.py --help` works.
- [ ] `python setup_local_ai.py --check` works without modifying files.
- [ ] `python setup_local_ai.py --install --dry-run` previews overwrite install.
- [ ] `python setup_local_ai.py --merge --dry-run` previews merge install.
- [ ] `python setup_local_ai.py --restore` handles missing backup safely.
- [ ] `python setup_local_ai.py --project . --dry-run` previews project context.
- [ ] `python setup_local_ai.py --report --dry-run` previews Markdown report.
- [ ] `python setup_local_ai.py --report --report-format json --dry-run` previews JSON report.

## 3. Config safety

- [ ] Existing `~/.continue/config.yaml` or `config.json` is backed up before writes.
- [ ] First backup uses `config.yaml.bak` or `config.json.bak`.
- [ ] Later backups use timestamped names and do not overwrite the first backup.
- [ ] YAML format is the default Continue.dev config format.
- [ ] Legacy JSON format works with `--config-format json`.
- [ ] `--merge` preserves existing Continue.dev config fields where possible in legacy JSON mode.
- [ ] `--install` is documented as overwrite mode.
- [ ] `--dry-run` does not write files.

## 4. Model profiles

- [ ] `--profile light --dry-run` works.
- [ ] `--profile balanced --dry-run` works.
- [ ] `--profile strong --dry-run` works.
- [ ] Custom `--chat-model`, `--autocomplete-model`, and `--embedding-model` work.
- [ ] Missing model hints show the correct `ollama pull ...` commands.

## 5. Existing-project analysis

- [ ] `--project PATH` skips `.git`, `node_modules`, build outputs, virtualenvs, and caches.
- [ ] `--project PATH` writes only `CYBER_CODE_SHIELD_CONTEXT.md`.
- [ ] Generated context includes language, package manager, framework, test, directory, and style hints.
- [ ] Generated context does not copy large source files into the report.

## 6. Offline report

- [ ] Markdown report writes `CYBER_CODE_SHIELD_REPORT.md` by default.
- [ ] JSON report writes `CYBER_CODE_SHIELD_REPORT.json` by default.
- [ ] Report checks Ollama CLI, service, selected models, required models, and missing models.
- [ ] Report checks whether API base is local.
- [ ] Report detects Continue.dev providers.
- [ ] Report detects common cloud AI environment variable names only.
- [ ] Report never prints secret values.

## 7. Documentation and examples

- [ ] README quick start is accurate.
- [ ] README includes model profiles.
- [ ] README includes `--project` usage.
- [ ] README includes `--report` usage.
- [ ] README includes v0.2 demo commands for `--suggest-patch`, `--fix-error`, and `--complete-todo`.
- [ ] `examples/continue-before-merge.json` is valid JSON.
- [ ] `examples/continue-after-merge.json` is valid JSON.
- [ ] `examples/sample-project-context.md` is readable.
- [ ] `examples/sample-offline-report.md` is readable.
- [ ] `PROJECT_DIRECTION.md` matches current scope.
- [ ] `CHANGELOG.md` includes v0.1.0 notes.

## 8. v0.2.0 Local patch assistant MVP

- [ ] `python setup_local_ai.py --fix-error --project . --error-text "NameError: name 'x' is not defined" --dry-run` builds a prompt without writing files.
- [ ] `python setup_local_ai.py --suggest-patch --project . --task "Add validation" --dry-run` builds a prompt without writing files.
- [ ] Patch commands refuse non-local `--api-base` values.
- [ ] `--inference-provider openai-compatible` appears in help and targets local LM Studio/llama.cpp/vLLM style endpoints.
- [ ] Patch commands require `--project`.
- [ ] `--fix-error` requires exactly one of `--error-log` or `--error-text`.
- [ ] `--fix-error` extracts Python traceback file/line locations in dry-run output.
- [ ] `--fix-error` extracts generic `path:line:column` locations in dry-run output.
- [ ] Existing `--fix-error --files` dry-run still works.
- [ ] `--suggest-patch` requires `--task`.
- [ ] `--complete-todo --dry-run` works when a marker exists in a specified file.
- [ ] `--complete-todo` requires `--files` for the MVP.
- [ ] `--complete-todo` returns a clear message when no TODO/pass/NotImplemented marker is found.
- [ ] `--files` cannot escape the project root.
- [ ] `--patch-timeout` appears in help and can be used by patch commands.
- [ ] `--context-lite` appears in help and reduces prompt size for patch commands.
- [ ] Patch suggestion files record original request, inference provider, context mode, timeout, generated token cap, and disabled thinking output.
- [ ] Generated patch suggestions are ignored by git.
- [ ] Patch commands do not modify business source files.

## 9. v0.3.0 Compliance-ready patch reports

- [ ] Generated patch reports include `## Compliance evidence`.
- [ ] Generated patch reports include `## Policy warnings`.
- [ ] `--model-tier {light,deep,custom}` appears in help and records metadata only.
- [ ] `--no-policy-warnings` appears in help and records disabled policy scan status.
- [ ] Policy warnings detect dependency-file changes.
- [ ] Policy warnings detect network-call additions.
- [ ] Policy warnings detect shell-execution additions.
- [ ] Policy warnings detect secret/env file changes.
- [ ] Policy warnings detect CI/CD changes.
- [ ] Policy warnings detect sensitive auth/crypto/billing/user-data paths.
- [ ] Policy warnings are advisory and do not block report generation.

## 10. v0.4.0 Audit-hardened patch reports

- [ ] Generated patch reports include a `Report ID`.
- [ ] Generated patch reports include prompt SHA-256 and model response SHA-256 fingerprints.
- [ ] Generated patch reports include reviewed file SHA-256 hashes and byte sizes.
- [ ] `--patch-report-format {markdown,json}` appears in help.
- [ ] `--patch-report-format json` uses `.json` default patch report filenames.
- [ ] JSON patch reports are machine-readable and include structured metadata, audit fields, warnings, and model response.
- [ ] JSON patch reports do not include the full internal prompt text.
- [ ] Policy warnings include differentiated severities.
- [ ] Hash documentation clearly says fingerprints are not encryption or anonymization.
- [ ] Patch assistant commands still do not modify business source files or apply patches automatically.

## 11. v0.4.1 Review-first audit positioning

- [ ] README first screen positions Cyber-Code-Shield as a review-first audit layer for local AI coding.
- [ ] README clearly says the project is not a full autonomous coding agent.
- [ ] README links sanitized Markdown and JSON sample patch reports.
- [ ] Chinese README matches the English positioning.
- [ ] PROJECT_DIRECTION.md uses the review-first audit/governance framing.
- [ ] PROJECT_DIRECTION.md changes v0.5 from desktop installer to architecture split.
- [ ] CHANGELOG.md includes v0.4.1 planned/unreleased notes.
- [ ] Enterprise pilot checklist exists and does not overclaim formal security certification.
- [ ] Sample JSON patch report is valid JSON.
- [ ] Sample reports do not contain local absolute paths, secrets, or generated timestamped filenames.

## 12. v0.5 Architecture split readiness

- [ ] Current CLI behavior is documented before splitting.
- [ ] Patch report schema/rendering responsibilities are identified.
- [ ] Policy warning detection responsibilities are identified.
- [ ] Local inference client responsibilities are identified.
- [ ] Project context collection responsibilities are identified.
- [ ] Tests cover behavior before module extraction begins.

## 13. v0.6 Policy profile and report bundle readiness

- [ ] README describes v0.6 as policy profiles plus report bundles, not an autonomous coding agent.
- [ ] PROJECT_DIRECTION.md defines `basic`, `enterprise-strict`, `china-privacy`, and `supply-chain` profiles.
- [ ] Policy profile wording avoids claiming formal legal compliance certification.
- [ ] Report bundle manifest fields are defined before implementation begins.
- [ ] Report bundle keeps source files manual-review-first and does not apply patches automatically.
- [ ] Planned bundle artifacts include Markdown/JSON reports, reviewed-file hashes, policy warnings, validation warnings, environment summary, and manifest.

## 14. Validation commands

Run before release:

```bash
python -m py_compile setup_local_ai.py
python -m json.tool config.json >/dev/null
python -m json.tool configs/continue/config.ollama.deepseek.json >/dev/null
python setup_local_ai.py --config-format yaml --dry-run
python setup_local_ai.py --config-format json --dry-run
python -m json.tool examples/continue-before-merge.json >/dev/null
python -m json.tool examples/continue-after-merge.json >/dev/null
python -m json.tool examples/sample-patch-report.json
python setup_local_ai.py --help
python setup_local_ai.py --check
python setup_local_ai.py --merge --dry-run
python setup_local_ai.py --project . --dry-run
python setup_local_ai.py --report --dry-run
python setup_local_ai.py --report --report-format json --dry-run
python setup_local_ai.py --fix-error --project . --error-text "NameError: name 'model_config' is not defined" --files setup_local_ai.py --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Improve the offline report wording without changing behavior" --files setup_local_ai.py README.md --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test non-local API refusal" --api-base http://example.com:11434 --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test timeout option" --files README.md --chat-model gemma4-local --patch-timeout 600 --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test lite context" --files README.md --chat-model gemma4-local --context-lite --patch-timeout 600 --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test OpenAI-compatible local provider" --files README.md --inference-provider openai-compatible --api-base http://localhost:1234/v1 --chat-model local-model --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test model tier metadata" --files README.md --model-tier deep --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test JSON patch report format" --files README.md --patch-report-format json --dry-run
python setup_local_ai.py --suggest-patch --project . --task "Test disabled policy warnings" --files README.md --no-policy-warnings --dry-run
python -m unittest discover -s tests
```

For `--complete-todo`, create a temporary sample first:

```bash
python - <<'PY'
from pathlib import Path
p = Path('tmp_complete_todo_sample.py')
p.write_text('def add(a, b):\n    pass\n', encoding='utf-8')
PY
python setup_local_ai.py --complete-todo --project . --files tmp_complete_todo_sample.py --chat-model gemma4-local --context-lite --patch-timeout 600 --dry-run
rm -f tmp_complete_todo_sample.py
```

## 14. Release packaging

- [ ] Remove local generated files before publishing.
- [ ] Confirm `.gitignore` excludes generated context/report/patch files.
- [ ] Confirm no `CYBER_CODE_SHIELD_*` generated files remain in the project root.
- [ ] Confirm README has v0.4.1 review-first positioning, sample patch report links, and enterprise pilot guidance.
- [ ] Confirm `LICENSE` is Apache-2.0.
- [ ] Tag release as `v0.4.1` after final validation.
- [ ] Include known limitations in release notes.

## 15. Known limitations for v0.4.1

- Patch suggestions are Markdown or JSON reports only; there is no automatic apply mode.
- The tool is not a full autonomous local Claude Code agent.
- `--complete-todo` requires explicit `--files` in the MVP.
- Context selection is heuristic and intentionally capped.
- Output quality depends on the selected local model and available context.
- OpenAI-compatible support is local-endpoint only; provider auto-detection and streaming responses are not included.
- Continue.dev currently recommends `config.yaml`; legacy `config.json` support is retained for older setups.
- Project analysis is heuristic and lightweight; it is not a full AST/code intelligence engine.
- Offline report is a configuration review aid, not a security audit.
- The tool does not install Ollama, VS Code, Continue.dev, or models automatically.
- The tool does not fine-tune or train models.
