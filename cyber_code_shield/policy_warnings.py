from pathlib import Path

from .constants import POLICY_WARNING_SEVERITIES
from .patch_parsing import extract_diff_paths, get_added_diff_lines


def normalize_policy_severity(severity):
    """把未知 severity 收敛到默认人工审查级别。"""
    if severity in POLICY_WARNING_SEVERITIES:
        return severity
    return "review"


def make_policy_warning(code, severity, message, evidence=None):
    """创建非阻断 policy warning。"""
    warning = {"code": code, "severity": normalize_policy_severity(severity), "message": message}
    if evidence:
        warning["evidence"] = evidence
    return warning


def path_contains_any(path_text, keywords):
    """判断路径是否包含任一关键词。"""
    lowered = path_text.lower().replace("\\", "/")
    return any(keyword in lowered for keyword in keywords)


def detect_policy_warnings(response_text, selected_files, project_path, error_locations=None):
    """检测企业审查相关的非阻断 policy warning。"""
    warnings = []
    diff_paths = extract_diff_paths(response_text)
    normalized_paths = [path.replace("\\", "/") for path in diff_paths]
    added_text = "\n".join(get_added_diff_lines(response_text)).lower()

    dependency_names = {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
    }
    if any(Path(path).name.lower() in dependency_names for path in normalized_paths):
        warnings.append(make_policy_warning(
            "DEPENDENCY_CHANGE",
            "review",
            "Patch touches dependency or lock files; review supply-chain and approval impact.",
            ", ".join(normalized_paths),
        ))

    network_patterns = ("requests.", "fetch(", "urllib", "http.client", "socket", "curl ", "wget ")
    if any(pattern in added_text for pattern in network_patterns):
        warnings.append(make_policy_warning(
            "NETWORK_CALL",
            "high",
            "Patch appears to add network access; review data-flow and egress policy.",
        ))

    shell_patterns = ("subprocess", "os.system", "exec(", "eval(", "child_process", "spawn(")
    if any(pattern in added_text for pattern in shell_patterns):
        warnings.append(make_policy_warning(
            "SHELL_EXECUTION",
            "high",
            "Patch appears to add shell or dynamic code execution; review command-injection risk.",
        ))

    if any(path_contains_any(path, (".env", "secret", "credential", "token", "key", "cert")) for path in normalized_paths):
        warnings.append(make_policy_warning(
            "SECRET_OR_ENV_FILE",
            "high",
            "Patch touches secret, credential, key, token, cert, or environment files; review sensitive-data handling.",
            ", ".join(normalized_paths),
        ))

    ci_keywords = (".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile", "dockerfile")
    if any(path_contains_any(path, ci_keywords) for path in normalized_paths):
        warnings.append(make_policy_warning(
            "CI_CD_CHANGE",
            "review",
            "Patch touches CI/CD or container build configuration; review deployment and pipeline impact.",
            ", ".join(normalized_paths),
        ))

    sensitive_keywords = ("auth", "permission", "policy", "crypto", "billing", "payment", "user_data", "userdata")
    if any(path_contains_any(path, sensitive_keywords) for path in normalized_paths):
        warnings.append(make_policy_warning(
            "SENSITIVE_AREA",
            "review",
            "Patch touches an authentication, authorization, cryptography, billing, payment, policy, or user-data area.",
            ", ".join(normalized_paths),
        ))

    return warnings


def format_policy_warnings(policy_warnings):
    """渲染 policy warnings。"""
    if not policy_warnings:
        return ["- None detected"]
    lines = []
    for warning in policy_warnings:
        line = f"- [{warning['severity']}] {warning['code']}: {warning['message']}"
        if warning.get("evidence"):
            line += f" Evidence: `{warning['evidence']}`"
        lines.append(line)
    return lines
