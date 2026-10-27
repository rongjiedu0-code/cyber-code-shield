#!/usr/bin/env python3
"""
Cyber-Code-Shield V2: Official Model Context Protocol (MCP) Stdio Server
Author: 度溶解 (rongjiedu0-code)
License: Apache-2.0
Exposes Cyber-Code-Shield V2 as a standard MCP Server over JSON-RPC 2.0 (stdio)
with ZERO third-party dependencies! Can be mounted directly into:
- Cursor IDE (~/.cursor/mcp.json)
- Claude Code / Claude Desktop
- Codex CLI / Continue.dev
"""
from __future__ import annotations
import datetime
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Dict, List
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
MCP_TOOLS = [
    {
        "name": "shield_audit_patch",
        "description": "Audit a code diff or shell command string for security policy violations before execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff_text": {"type": "string", "description": "The git diff text or bash script to analyze."}
            },
            "required": ["diff_text"]
        }
    },
    {
        "name": "shield_sync_agents_context",
        "description": "Append an architectural decision note to AGENTS.md to prevent context drift.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_why": {"type": "string", "description": "Why this architectural change was made."},
                "repo_path": {"type": "string", "description": "Path to local repository root."}
            },
            "required": ["decision_why"]
        }
    }
]
def rpc_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message}}


def handle_json_rpc(request):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return rpc_error(None, -32600, "Invalid Request")
    # JSON-RPC notifications never receive replies and cannot trigger tool writes.
    if "id" not in request:
        return None
    req_id = request["id"]
    if isinstance(req_id, (dict, list, bool)):
        return rpc_error(None, -32600, "Invalid request ID")
    method = request["method"]
    params = request.get("params", {})
    if not isinstance(params, dict):
        return rpc_error(req_id, -32602, "Parameters must be an object")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "cyber-code-shield-mcp", "version": "2.0.0"},
            "capabilities": {"tools": {}}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
    if method != "tools/call":
        return rpc_error(req_id, -32601, "Method not found")
    name = params.get("name")
    args = params.get("arguments", {})
    if not isinstance(args, dict):
        return rpc_error(req_id, -32602, "Arguments must be an object")
    try:
        if name == "shield_audit_patch":
            if not isinstance(args.get("diff_text"), str):
                return rpc_error(req_id, -32602, "diff_text must be a string")
            result = audit_diff(args["diff_text"])
        elif name == "shield_sync_agents_context":
            why = args.get("decision_why")
            path = args.get("repo_path", ".")
            if not isinstance(why, str) or not why.strip() or not isinstance(path, str):
                return rpc_error(req_id, -32602, "Nonempty decision_why and string repo_path required")
            repo_root = pathlib.Path(path).resolve(strict=True)
            if not repo_root.is_dir():
                raise ValueError("repo_path must be a directory")
            agents_file = repo_root / "AGENTS.md"
            if agents_file.is_symlink() or agents_file.resolve().parent != repo_root:
                raise ValueError("AGENTS.md must be a regular file inside repo_path")
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
            # Keep notes on a single ledger line and omit recognizable secrets.
            note = json.dumps(redact_secrets(why), ensure_ascii=False)
            with agents_file.open("a", encoding="utf-8") as stream:
                stream.write(f"\n- [{ts}] ARCH-WHY: {note}\n")
            result = {"path": str(agents_file), "status": "appended"}
        else:
            return rpc_error(req_id, -32602, "Unknown tool")
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}
    except (OSError, ValueError) as exc:
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "isError": True, "content": [{"type": "text", "text": str(exc)}]}}


def run_stdio_server():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except (ValueError, UnicodeError):
            response = rpc_error(None, -32700, "Parse error")
        else:
            response = handle_json_rpc(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    run_stdio_server()
