# Cyber-Code-Shield Offline Environment Report

This report was generated locally by Cyber-Code-Shield.
It is intended for developers, IT administrators, and security reviewers evaluating a local-first AI coding setup.

## Summary

- Generated at: `2026-05-19T10:30:00`
- OS: `Windows`
- Platform: `Windows-10-10.0.26200-SP0`
- Python version: `3.11.9`
- Ollama CLI installed: `True`
- Ollama service running: `True`
- Ollama API base: `http://localhost:11434`
- Ollama API base is local: `True`

## Continue.dev configuration

- Continue config path: `C:\\Users\\example\\.continue\\config.json`
- Main backup path: `C:\\Users\\example\\.continue\\config.json.bak`
- Config exists: `True`
- Config valid JSON: `True`
- Cyber-Code-Shield local chat model configured: `True`
- Local Ollama autocomplete configured: `True`
- Local Ollama embeddings configured: `True`
- Codebase index enabled: `True`
- Codebase indexing mode: `local`

## Providers detected in Continue config

- ollama

## Cloud provider hints

- None detected in Continue config

## Cloud API environment variables present

Only variable names are reported; secret values are never read or printed.

- None detected

## Selected local model configuration

- Chat/refactor model: `deepseek-coder-v2:16b`
- Autocomplete model: `deepseek-coder-v2:16b`
- Embedding model: `nomic-embed-text`

## Required models

- deepseek-coder-v2:16b
- nomic-embed-text

## Installed Ollama models

- deepseek-coder-v2:16b
- nomic-embed-text

## Missing required models

- None

## Local-first review notes

- This report checks configuration signals only; it is not a formal security audit.
- A local Ollama endpoint should normally use `localhost`, `127.0.0.1`, or an approved internal host.
- Cloud provider hints and cloud API environment variables should be reviewed before strict-compliance use.
- VS Code, extensions, operating system telemetry, and network controls should be reviewed separately by the organization.
- Cyber-Code-Shield does not claim absolute zero leakage; it helps configure and document a local-first AI coding workflow.
