# Cyber-Code-Shield Enterprise Pilot Checklist

Use this checklist to evaluate Cyber-Code-Shield as a review-first audit layer for local AI coding in privacy-sensitive or strong-compliance environments.

This checklist is a planning and review aid. It is not a formal security certification and does not claim absolute zero leakage.

## 1. Pilot goal

- [ ] Define the target team, project type, and pilot duration.
- [ ] Confirm the pilot goal is reviewable local AI coding, not autonomous code modification.
- [ ] Decide whether the pilot evaluates environment setup, patch reports, policy warnings, or all of them.
- [ ] Identify who reviews generated patch reports: developer, team lead, AppSec, compliance, or IT.

## 2. Environment boundary

- [ ] Confirm the workstation or server is approved for local AI coding experiments.
- [ ] Confirm operating system telemetry, editor telemetry, terminal logs, and network controls meet internal policy.
- [ ] Confirm no production secrets are used in demo prompts, logs, or sample reports.
- [ ] Confirm generated reports are stored according to internal data-retention rules.

## 3. Local inference setup

- [ ] Confirm Ollama or the approved local OpenAI-compatible service is installed.
- [ ] Confirm the inference API base points to `localhost`, `127.0.0.1`, `::1`, or an approved internal host.
- [ ] Confirm selected local models are approved for the pilot.
- [ ] Confirm model logs, cache directories, and service access controls are reviewed separately.

## 4. Continue.dev configuration review

- [ ] Run `python setup_local_ai.py --check`.
- [ ] Run `python setup_local_ai.py --report --dry-run`.
- [ ] Run `python setup_local_ai.py --report --report-format json --dry-run`.
- [ ] Review whether Continue.dev config contains unexpected cloud providers.
- [ ] Review whether cloud AI API environment variable names are present on the pilot machine.

## 5. Patch report evidence review

- [ ] Generate a dry-run patch prompt first with `--dry-run`.
- [ ] Generate a Markdown patch report for a toy or low-risk task.
- [ ] Generate a JSON patch report with `--patch-report-format json`.
- [ ] Confirm the patch report includes a report ID.
- [ ] Confirm the report includes prompt SHA-256 and model response SHA-256 fingerprints.
- [ ] Confirm reviewed files are represented by relative path, SHA-256, and byte size rather than full file contents in audit metadata.
- [ ] Confirm `source_files_modified_automatically` is `false`.

## 6. Policy warning review

- [ ] Review dependency-file, network-call, shell-execution, secret/env-file, CI/CD, and sensitive-area warnings.
- [ ] Confirm warning severities are treated as advisory review signals, not automatic approval or rejection.
- [ ] Decide which warning categories require AppSec or compliance review during the pilot.
- [ ] Record any organization-specific policy categories that are missing.

## 7. Human review workflow

- [ ] Confirm developers do not copy suggested diffs without human review.
- [ ] Confirm reviewers inspect `Missing context`, `Response warnings`, `Policy warnings`, and `Risks or assumptions`.
- [ ] Confirm source changes are applied manually in normal development workflow.
- [ ] Confirm tests and code review happen after applying any suggested patch.

## 8. Data handling rules

- [ ] Do not paste secrets, customer data, production credentials, or confidential incident logs into prompts during the pilot.
- [ ] Treat user requests and model responses as part of the review artifact.
- [ ] Treat hashes as audit fingerprints, not encryption or anonymization.
- [ ] Review generated reports before sharing them outside the pilot team.

## 9. Success criteria

- [ ] Developers can generate useful local patch suggestions for narrow tasks.
- [ ] Security or compliance reviewers can inspect JSON patch report fields.
- [ ] The pilot produces no automatic source modifications.
- [ ] Reviewers understand what the tool does and does not prove.
- [ ] The team can decide whether to continue with v0.5 architecture split, policy profiles, or risk scoring.

## 10. Known non-goals

- Cyber-Code-Shield is not a formal security audit.
- Cyber-Code-Shield is not a full autonomous coding agent.
- Cyber-Code-Shield does not install or approve models by itself.
- Cyber-Code-Shield does not guarantee absolute zero leakage.
- Cyber-Code-Shield does not replace organization-specific AppSec, compliance, or legal review.
