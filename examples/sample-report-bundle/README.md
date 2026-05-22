# Sample Cyber-Code-Shield Report Bundle

This directory is a sanitized v0.6 example of a Cyber-Code-Shield report bundle.

It shows the artifact layout produced by `--report-bundle`:

- `report.md` — human-readable patch suggestion report
- `report.json` — machine-readable patch suggestion report
- `reviewed-files.json` — reviewed file paths, hashes, and sizes
- `policy-warnings.json` — selected policy profile and warning list
- `validation-warnings.json` — local model response validation warnings
- `environment-summary.json` — local environment signals without secret values
- `manifest.json` — bundle index with artifact hashes and review metadata

All paths, hashes, model names, timestamps, and code snippets in this directory are synthetic examples. This bundle is documentation material, not a formal security audit or compliance certification.
