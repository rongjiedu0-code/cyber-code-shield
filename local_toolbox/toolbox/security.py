import os
from pathlib import Path
import re
from .shield_core import audit
from .shield_rules import redact_secrets

ASSIGNMENT = re.compile(r'''(?ix)(\b(?:api[_-]?key|access[_-]?token|secret|password|passwd)\b\s*[:=]\s*)["']([^"'\r\n]{8,})["']''')
EXCLUDE = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'runtime', 'build', 'dist'}
EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs'}


def redact_all(text):
    return ASSIGNMENT.sub(lambda m: m.group(1) + '"[已脱敏]"', redact_secrets(text))


def scan_code(content, name='输入代码.py'):
    report = audit(content)
    findings = list(report['warnings'])
    for number, line in enumerate(content.splitlines(), 1):
        if ASSIGNMENT.search(line):
            findings.append(dict(rule_id='CN-SECRET-011', severity='HIGH', line=number,
                snippet=redact_all(line), cwe_id='CWE-798', remediation='移至环境变量或密钥管理，撤销并轮换已暴露密钥'))
        if re.search(r'\b(?:eval|Function)\s*\(|child_process\.(?:exec|execSync)\s*\(', line):
            findings.append(dict(rule_id='CN-JS-012', severity='HIGH', line=number, snippet=redact_all(line),
                cwe_id='CWE-94', remediation='避免执行不可信字符串，使用固定参数与输入校验'))
        if re.search(r'''(?i)(?:execute|query)\s*\([^\n]*(?:f["']|\+\s*(?:user|input|req|name))''', line):
            findings.append(dict(rule_id='CN-SQL-013', severity='HIGH', line=number, snippet=redact_all(line),
                cwe_id='CWE-89', remediation='使用参数化 SQL，不拼接用户输入'))
    rows = []
    for item in findings:
        rows.append({'文件': redact_all(name), '行号': item['line'],
            '级别': {'HIGH': '高危', 'CRITICAL': '严重'}.get(item['severity'], '提示'),
            '规则': item['rule_id'], 'CWE': item.get('cwe_id', ''),
            '代码片段': redact_all(item['snippet'])[:200],
            '修复建议': redact_all(item.get('remediation', '请人工复核')), '异常': '是',
            '检查方式': 'Python AST + 正则' if name.endswith('.py') else '正则（非 Python AST）'})
    if not rows:
        rows.append({'文件': redact_all(name), '行号': '', '级别': '未命中规则', '规则': '', 'CWE': '',
            '代码片段': '', '修复建议': '静态规则未命中不等于代码安全，请继续人工审查', '异常': '否',
            '检查方式': 'Python AST + 正则' if name.endswith('.py') else '正则（非 Python AST）'})
    return rows


def scan_path(path):
    path = Path(path).resolve()
    if not path.exists():
        raise ValueError('扫描路径不存在')
    files = []
    if path.is_file():
        files = [path]
        root = path.parent
    else:
        root = path
        for folder, dirs, names in os.walk(path, followlinks=False):
            dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDE and not (Path(folder)/d).is_symlink()]
            files.extend(Path(folder)/n for n in sorted(names) if Path(n).suffix.lower() in EXTENSIONS)
            if len(files) > 5000:
                raise ValueError('当前版本单次最多扫描 5000 个源码文件')
    rows = []
    for file in files:
        if file.is_symlink() or file.suffix.lower() not in EXTENSIONS:
            continue
        relative = str(file.relative_to(root))
        try:
            if file.stat().st_size > 1024*1024:
                raise ValueError('文件超过 1MB，未扫描')
            rows.extend(scan_code(file.read_text(encoding='utf-8-sig'), relative))
        except (OSError, ValueError) as error:
            rows.append({'文件': relative, '级别': '未扫描', '异常': '是', '说明': str(error)})
    if not rows:
        raise ValueError('未找到可扫描的 Python / JS / TS 源码文件')
    return rows
