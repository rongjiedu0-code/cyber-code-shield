# AI Code Security Shield: AST + Regex Audit

Zero input really scans three built-in code examples during this run: shell execution with `shell=True`, a constructed-path file read, and an agent-management route with no visible authentication dependency. These are explicitly identified as built-in analysis inputs, not claims of newly discovered vulnerabilities in a live repository.

Supply `files` with inline `name` and `content` values to scan your own code or diffs. File names are labels; submitted code is never executed and submitted paths are never opened. Python AST checks supplement the original regex policies. Git diffs are checked on added lines; plain snippets are examined in full.

```json
{"mode":"audit","files":[{"name":"review.py","content":"import subprocess
subprocess.run(command, shell=True)"}],"maxItems":3}
```

Reports include verdicts, rule IDs, redacted snippets, line numbers, `analysis_method`, `ast_parse_status`, CWE mappings and content hashes. Supported weaknesses include CWE-78, CWE-22, CWE-306 and CWE-502. `cve_ids` stays empty unless a verified affected-product/version/advisory match exists; this release does not invent CVE numbers.

Set the environment variable `OFFLINE_MODE=1` only for three labeled free demonstration records. The live default is actual analysis, not canned findings. Submitted INPUT remains in your account storage; sanitize real credentials before submitting. Static PASS is not a guarantee of safety or complete authorization analysis.

Suggested pricing: `actor-start` $0.02 per real-result run plus `security-audit-file` $0.01 per unique code-content scan. Identical content under different labels in the same run is billed once. Safe real scans are still actual work and can be charged.

## Billing and fallback safety

The Actor charges `actor-start` only after its first real result exists, followed by one custom event per real item. Demo/fixture markers are checked before either charge; fallback-only runs never call `Actor.charge()`. Keep the default Dataset item event free. The SDK's short idempotency cache is supplemented with run-scoped KV receipts. Uncertain prior charges fail closed for reconciliation; a crash can duplicate an output row, so consumers should deduplicate on `id`.

If the Actor is not monetized yet, real results can be returned without custom PPE charges. In PPE mode both event definitions must be configured with positive flat prices. Suggested prices are configuration examples, not a claim that monetization or Store publication has already been enabled.

## Local verification

Python 3.11+: `pip install -r requirements-dev.txt`, then `python -m unittest discover -s tests -p "test_*.py" -v`.
Tests use deterministic HTTP boundaries and the real SDK local charging mode; a separate live acceptance probe checks actual public endpoints.
For an explicit free offline run, set `OFFLINE_MODE=1` and `ACTOR_TEST_PAY_PER_EVENT=true`, then run `python -m src`.
For real local collection, use `OFFLINE_MODE=0` with the SDK local test flag. Local simulated fees do not bill money; normal platform compute/storage terms apply when running in the cloud.

Each `.actor/actor.json` sets `dockerContextDir` to `..` relative to the definition so the standalone ZIP and a Git monorepo subdirectory use the same build context. Apache-2.0 attribution is retained in LICENSE, NOTICE and src/vendor.
