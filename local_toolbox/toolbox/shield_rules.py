"""Original local security policy rules and redaction helpers."""

import re

import hashlib

from typing import Dict, List, Any

POLICY_RULES = [
    {
        "rule_id": "CCS-SH-001",
        "severity": "CRITICAL",
        "category": "shell",
        "pattern": re.compile(r"(rm\s+-rf\s+/|curl\s+[^|]+\|\s*(?:ba)?sh|wget\s+[^|]+\|\s*(?:ba)?sh|chmod\s+777)", re.I),
        "remediation": "Block destructive root deletions or unverified pipe-to-shell execution.",
    },
    {
        "rule_id": "CCS-SEC-002",
        "severity": "CRITICAL",
        "category": "secret",
        "pattern": re.compile(r"(sk-[a-zA-Z0-9_-]{20,}|AIza[0-9A-Za-z\-_]{35}|ghp_[0-9a-zA-Z]{36}|AKIA[0-9A-Z]{16})"),
        "remediation": "Move API keys and tokens to .env excluded by .gitignore.",
    },
    {
        "rule_id": "CCS-NET-003",
        "severity": "HIGH",
        "category": "network",
        "pattern": re.compile(r"(0\.0\.0\.0|ngrok\.io|webhook\.site|subprocess\.(?:Popen|run|call)\([^)]*shell\s*=\s*True)", re.I),
        "remediation": "Bind local debug/MCP daemons strictly to 127.0.0.1 and avoid shell=True.",
    },
]

def redact_secrets(text: str) -> str:
    return POLICY_RULES[1]["pattern"].sub("[REDACTED]", text)

def audit_diff(diff_text: str) -> Dict[str, Any]:
    warnings: List[Dict[str, Any]] = []
    is_diff = any(line.startswith(("diff --git ", "@@ ", "+++ ")) for line in diff_text.splitlines())
    for idx, line in enumerate(diff_text.splitlines(), start=1):
        if is_diff and not line.startswith("+"):
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        clean = line[1:] if line.startswith("+") else line
        for rule in POLICY_RULES:
            if rule["pattern"].search(clean):
                warnings.append({
                    "rule_id": rule["rule_id"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "line": idx,
                    "snippet": redact_secrets(clean.strip())[:120],
                    "remediation": rule["remediation"],
                })
    crit = sum(1 for w in warnings if w["severity"] == "CRITICAL")
    verdict = "BLOCK" if crit > 0 else ("WARN" if warnings else "PASS")
    return {
        "verdict": verdict,
        "diff_sha256": hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
        "total_warnings": len(warnings),
        "critical_count": crit,
        "warnings": warnings,
    }
