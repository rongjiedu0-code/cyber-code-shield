import uuid
from datetime import datetime

from .constants import (
    DEFAULT_INFERENCE_PROVIDER,
    DEFAULT_MODEL_TIER,
    PATCH_SUGGESTION_PREFIX,
    __version__,
)
from .hashing import collect_reviewed_file_hashes, hash_text_sha256
from .policy_warnings import format_policy_warnings
from .serialization import format_json


def get_default_patch_output_path(project_path, task_type, patch_report_format="markdown"):
    """生成默认补丁建议输出路径。"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_name = task_type.upper()
    extension = ".json" if patch_report_format == "json" else ".md"
    return project_path / f"{PATCH_SUGGESTION_PREFIX}_{task_name}_{timestamp}{extension}"


def serialize_error_locations(error_locations, project_path):
    """把内部错误位置转换为可序列化报告字段。"""
    serialized = []
    for location in error_locations or []:
        entry = {
            "relative_path": location.get("relative_path"),
            "line": location.get("line"),
            "column": location.get("column"),
            "raw": location.get("raw"),
            "kind": location.get("kind"),
        }
        file_path = location.get("file_path")
        if file_path:
            try:
                entry["relative_path"] = str(file_path.relative_to(project_path)).replace("\\", "/")
            except ValueError:
                entry["relative_path"] = str(file_path)
        serialized.append(entry)
    return serialized


def build_patch_report_data(task_type, project_path, model_config, selected_files, model_response, user_request, context_lite, patch_timeout, num_predict, prompt_text=None, error_locations=None, validation_warnings=None, policy_warnings=None, policy_warnings_enabled=True):
    """构建补丁建议报告的结构化审计数据。"""
    task_titles = {
        "fix_error": "Fix Error",
        "suggest_patch": "Suggest Patch",
        "complete_todo": "Complete TODO",
    }
    validation_warnings = validation_warnings or []
    policy_warnings = policy_warnings or []
    reviewed_files = collect_reviewed_file_hashes(project_path, selected_files)
    generated_at = datetime.now().isoformat(timespec="seconds")
    task_title = task_titles.get(task_type, "Suggest Patch")
    return {
        "schema_version": "cyber-code-shield.patch-report.v1",
        "report_id": f"ccs-patch-{uuid.uuid4().hex}",
        "generated_at": generated_at,
        "tool": {
            "name": "Cyber-Code-Shield",
            "version": __version__,
        },
        "task": {
            "type": task_type,
            "title": task_title,
        },
        "project": {
            "path": str(project_path),
        },
        "model": {
            "chat_model": model_config["chat_model"],
            "model_tier": model_config.get("model_tier", DEFAULT_MODEL_TIER),
            "inference_provider": model_config.get("inference_provider", DEFAULT_INFERENCE_PROVIDER),
            "api_base": model_config["api_base"],
            "context_mode": "lite" if context_lite else "full",
            "context_lite": context_lite,
            "timeout_seconds": patch_timeout,
            "max_generated_tokens": num_predict,
            "thinking_output_requested": False,
        },
        "audit": {
            "prompt_sha256": hash_text_sha256(prompt_text) if prompt_text is not None else None,
            "model_response_sha256": hash_text_sha256(model_response),
            "source_files_modified_automatically": False,
            "files_reviewed_count": len(selected_files),
            "detected_error_locations_count": len(error_locations or []),
            "response_warning_count": len(validation_warnings),
            "policy_warning_count": len(policy_warnings),
            "policy_scan_status": "enabled" if policy_warnings_enabled else "disabled",
            "reviewed_files": reviewed_files,
        },
        "user_request": user_request.strip(),
        "error_locations": serialize_error_locations(error_locations or [], project_path),
        "policy_warnings_enabled": policy_warnings_enabled,
        "policy_warnings": policy_warnings,
        "response_warnings": validation_warnings,
        "safety_notes": [
            "This is a patch suggestion, not an applied change.",
            "Review the diff and validation suggestions before editing source files.",
            "The output depends on the selected local model and provided context.",
        ],
        "model_response": model_response.strip(),
    }


def render_patch_markdown(report):
    """把结构化补丁报告渲染成 Markdown。"""
    model = report["model"]
    audit = report["audit"]
    lines = [
        "# Cyber-Code-Shield Patch Suggestion",
        "",
        "This file was generated locally by Cyber-Code-Shield.",
        "Source files were not modified automatically.",
        "",
        "## Metadata",
        "",
        f"- Report ID: `{report['report_id']}`",
        f"- Task type: {report['task']['title']}",
        f"- Project path: `{report['project']['path']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Model: `{model['chat_model']}`",
        f"- Model tier: `{model['model_tier']}`",
        f"- Inference provider: `{model['inference_provider']}`",
        f"- API base: `{model['api_base']}`",
        f"- Context lite: `{'yes' if model['context_lite'] else 'no'}`",
        f"- Timeout seconds: `{model['timeout_seconds']}`",
        f"- Max generated tokens: `{model['max_generated_tokens']}`",
        "- Thinking output requested: `no`",
        f"- Prompt SHA-256: `{audit['prompt_sha256'] or 'unavailable'}`",
        f"- Model response SHA-256: `{audit['model_response_sha256']}`",
        "",
        "## Compliance evidence",
        "",
        f"- Report ID: `{report['report_id']}`",
        f"- Schema version: `{report['schema_version']}`",
        f"- Tool version: `{report['tool']['version']}`",
        f"- Task type: `{report['task']['title']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Inference provider: `{model['inference_provider']}`",
        f"- Model: `{model['chat_model']}`",
        f"- Model tier: `{model['model_tier']}`",
        f"- API base: `{model['api_base']}`",
        f"- Context mode: `{model['context_mode']}`",
        f"- Timeout seconds: `{model['timeout_seconds']}`",
        f"- Max generated tokens: `{model['max_generated_tokens']}`",
        "- Thinking output requested: `no`",
        "- Source files modified automatically: `no`",
        f"- Prompt SHA-256: `{audit['prompt_sha256'] or 'unavailable'}`",
        f"- Model response SHA-256: `{audit['model_response_sha256']}`",
        f"- Reviewed file hash count: `{len(audit['reviewed_files'])}`",
        f"- Files reviewed count: `{audit['files_reviewed_count']}`",
        f"- Detected error locations count: `{audit['detected_error_locations_count']}`",
        f"- Response warning count: `{audit['response_warning_count']}`",
        f"- Policy warning count: `{audit['policy_warning_count']}`",
        f"- Policy scan status: `{audit['policy_scan_status']}`",
        "",
        "## User request",
        "",
        report["user_request"],
        "",
    ]

    if report["error_locations"]:
        lines.extend(["## Detected error locations", ""])
        for location in report["error_locations"]:
            suffix = ""
            if location.get("line"):
                suffix += f":{location['line']}"
            if location.get("column"):
                suffix += f":{location['column']}"
            lines.append(f"- `{location['relative_path']}{suffix}` — {location['kind']}")
        lines.append("")

    lines.extend(["## Files reviewed", ""])
    if audit["reviewed_files"]:
        for reviewed_file in audit["reviewed_files"]:
            if reviewed_file.get("sha256"):
                lines.append(f"- `{reviewed_file['path']}` sha256=`{reviewed_file['sha256']}` size_bytes=`{reviewed_file['size_bytes']}`")
            else:
                lines.append(f"- `{reviewed_file['path']}` sha256=`unavailable` read_error=`{reviewed_file.get('read_error', 'unknown')}`")
    else:
        lines.append("- No project files were selected")

    lines.extend(["", "## Policy warnings", ""])
    if report["policy_warnings_enabled"]:
        lines.extend(format_policy_warnings(report["policy_warnings"]))
    else:
        lines.append("- Policy warning scan disabled by user.")
    lines.append("")

    if report["response_warnings"]:
        lines.extend(["## Response warnings", ""])
        for warning in report["response_warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(["## Safety notes", ""])
    for note in report["safety_notes"]:
        lines.append(f"- {note}")
    lines.extend(["", "## Model response", "", report["model_response"], ""])
    return "\n".join(lines)


def render_patch_report_by_format(report, patch_report_format):
    """按用户选择输出补丁建议报告。"""
    if patch_report_format == "json":
        return format_json(report)
    return render_patch_markdown(report)


def render_patch_suggestion(task_type, project_path, model_config, selected_files, model_response, user_request, context_lite, patch_timeout, num_predict, error_locations=None, validation_warnings=None, policy_warnings=None, policy_warnings_enabled=True, prompt_text=None):
    """把模型输出包装成补丁建议 Markdown。"""
    report = build_patch_report_data(
        task_type,
        project_path,
        model_config,
        selected_files,
        model_response,
        user_request,
        context_lite,
        patch_timeout,
        num_predict,
        prompt_text=prompt_text,
        error_locations=error_locations,
        validation_warnings=validation_warnings,
        policy_warnings=policy_warnings,
        policy_warnings_enabled=policy_warnings_enabled,
    )
    return render_patch_markdown(report)
