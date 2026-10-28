"""Static analysis only: never execute submitted code or open submitted paths."""
import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote

from .common import stable_id, integer
from .shield_rules import audit_diff, redact_secrets

RULES = [
    ('CCS-INJECT-004', 'CRITICAL', 'command-injection', re.compile(r'\$\([^\n]*\)|`[^`\n]+`'),
     'Reject shell command substitution; pass fixed argument arrays with shell=False.'),
    ('CCS-PATH-005', 'CRITICAL', 'path-traversal', re.compile(r'(?:\.\.[/\\])|(?:/(?:etc/(?:passwd|shadow)|root/\.ssh))|(?:[A-Za-z]:\\Windows\\System32)', re.I),
     'Resolve requested paths and verify they stay within an authorized root.'),
    ('CCS-EXEC-006', 'HIGH', 'dynamic-execution', re.compile(r'\b(?:eval|exec)\s*\(|\b(?:python[\d.]*|node|perl|ruby)\s+-[ce]\b|\bos\.system\s*\(', re.I),
     'Avoid dynamic evaluators and interpreter bypasses in command allowlists.'),
    ('CCS-DESERIALIZE-007', 'HIGH', 'unsafe-deserialization', re.compile(r'\bpickle\.loads?\s*\(|yaml\.load\s*\('),
     'Use safe formats/loaders for untrusted serialized data.'),
]


def added_lines(text):
    lines = text.splitlines()
    is_diff = any(line.startswith(('diff --git ', '@@ ', '+++ ')) for line in lines)
    return [(number, line[1:] if is_diff else line)
            for number, line in enumerate(lines, 1)
            if not is_diff or (line.startswith('+') and not line.startswith('+++'))]


def _has_guard(call):
    for keyword in call.keywords:
        if keyword.arg == 'dependencies' and any(
                isinstance(node, ast.Call) and
                ((isinstance(node.func, ast.Name) and node.func.id in {'Depends', 'Security'}) or
                 (isinstance(node.func, ast.Attribute) and node.func.attr in {'Depends', 'Security'}))
                for node in ast.walk(keyword.value)):
            return True
    return False


def unauthenticated_routes(code):
    """Flag concrete FastAPI-style route declarations with no visible dependency.

    Dependency presence is a signal, not proof of a correct authorization policy.
    Middleware, external gateways and ownership checks need human review.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    global_guard = any(isinstance(node, ast.Call) and
                       ((isinstance(node.func, ast.Name) and node.func.id in {'FastAPI', 'APIRouter'}) or
                        (isinstance(node.func, ast.Attribute) and node.func.attr in {'FastAPI', 'APIRouter'}))
                       and _has_guard(node) for node in ast.walk(tree))
    if global_guard:
        return []
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in {'get', 'post', 'put', 'delete', 'patch', 'api_route'}):
                guarded = _has_guard(decorator) or any(
                    isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id in {'Depends', 'Security'}
                    for child in ast.walk(node.args))
                if not guarded:
                    results.append((decorator.lineno, 'Route ' + node.name + ' has no visible authentication dependency'))
    return results


def audit(content):
    base = audit_diff(content)
    findings = list(base['warnings'])
    lines = added_lines(content)
    for number, line in lines:
        decoded = unquote(unquote(line))
        for rule_id, severity, category, pattern, remediation in RULES:
            if pattern.search(decoded):
                findings.append(dict(rule_id=rule_id, severity=severity, category=category,
                                     line=number, snippet=redact_secrets(line.strip())[:120], remediation=remediation))
    code = '\n'.join(line for _, line in lines)
    for number, message in unauthenticated_routes(code):
        findings.append(dict(rule_id='CCS-AUTH-008', severity='HIGH', category='missing-authentication',
                             line=lines[number - 1][0], snippet=message,
                             remediation='Require authentication and per-owner authorization on every agent-management endpoint.'))
    parse_status = 'parsed'
    try:
        tree = ast.parse(code)
    except SyntaxError:
        tree = None
        parse_status = 'not_valid_python; regex and diff checks still performed'
    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else '')
            if name in {'run', 'Popen', 'call', 'check_output', 'check_call'} and any(
                    keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in node.keywords):
                findings.append(dict(rule_id='CCS-AST-009', severity='HIGH', category='command-injection',
                    line=lines[node.lineno - 1][0], snippet=redact_secrets(ast.get_source_segment(code, node) or '')[:120],
                    remediation='Pass argument arrays with shell=False; validate untrusted arguments.', cwe_id='CWE-78'))
            if name in {'read_text', 'read_bytes', 'write_text', 'write_bytes', 'open'} and isinstance(func, ast.Attribute) and isinstance(func.value, ast.BinOp):
                findings.append(dict(rule_id='CCS-AST-010', severity='HIGH', category='path-traversal',
                    line=lines[node.lineno - 1][0], snippet=redact_secrets(ast.get_source_segment(code, node) or '')[:120],
                    remediation='Resolve the constructed path and enforce containment before file access.', cwe_id='CWE-22'))
    mapping = {'CCS-SH-001': 'CWE-78', 'CCS-SEC-002': 'CWE-798', 'CCS-NET-003': 'CWE-200',
               'CCS-INJECT-004': 'CWE-78', 'CCS-PATH-005': 'CWE-22', 'CCS-EXEC-006': 'CWE-94',
               'CCS-DESERIALIZE-007': 'CWE-502', 'CCS-AUTH-008': 'CWE-306'}
    for finding in findings:
        finding.setdefault('cwe_id', mapping.get(finding['rule_id']))
        if finding['rule_id'] == 'CCS-NET-003' and re.search(r'shell\s*=\s*True', finding['snippet']):
            finding['cwe_id'] = 'CWE-78'
    critical = sum(item['severity'] == 'CRITICAL' for item in findings)
    return dict(verdict='BLOCK' if critical else ('WARN' if findings else 'PASS'),
                total_warnings=len(findings), critical_count=critical, warnings=findings,
                diff_sha256=base['diff_sha256'],
                analysis_method='Python AST + regex; no execution', ast_parse_status=parse_status,
                cwe_ids=sorted({row['cwe_id'] for row in findings if row.get('cwe_id')}), cve_ids=[],
                cve_match_status='No CVE asserted: no affected product/version or advisory match was established.',
                limitations='Static heuristic audit. PASS is not proof of safety; review authorization and data flows.')
