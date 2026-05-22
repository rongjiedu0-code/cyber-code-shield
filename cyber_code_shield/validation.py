import re

from .error_locations import format_error_location, get_primary_error_location
from .patch_parsing import (
    extract_diff_paths,
    extract_effective_diff_changes,
    extract_section_body,
    get_added_diff_lines,
)


def patch_text_has_added_placeholder(suggested_patch):
    """判断补丁是否新增了明显占位内容。"""
    for line in get_added_diff_lines(suggested_patch):
        lowered = line.lower()
        if "todo" in lowered or "placeholder" in lowered:
            return True
    return False


def patch_text_uses_broad_unicode_character_checks(response_text, suggested_patch):
    """判断补丁是否可能用宽松 Unicode 字符判断实现 ASCII-only 约束。"""
    if "ascii" not in response_text.lower():
        return False
    lowered_patch = suggested_patch.lower()
    broad_checks = (".islower(", ".isalpha(", ".isalnum(")
    return any(check in lowered_patch for check in broad_checks)


def validate_patch_response(response, selected_files, project_path, error_locations=None):
    """对本地模型输出做非阻断校验，提示用户人工复核风险。"""
    warnings = []
    required_sections = [
        "Confidence",
        "Missing context",
        "Files to change",
        "Explanation",
        "Suggested patch",
        "Validation steps",
        "Risks or assumptions",
    ]
    for section in required_sections:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", response, re.IGNORECASE | re.MULTILINE):
            warnings.append(f"模型输出缺少必需章节：{section}")

    suggested_patch = extract_section_body(response, "Suggested patch")
    if not suggested_patch:
        warnings.append("模型输出的 Suggested patch 章节为空。")
    elif patch_text_has_added_placeholder(suggested_patch):
        warnings.append("Suggested patch 中可能新增占位内容，请人工确认。")
    if patch_text_uses_broad_unicode_character_checks(response, suggested_patch):
        warnings.append("Suggested patch 可能用宽松 Unicode 字符判断实现 ASCII-only 约束，请人工确认。")
    removed_lines = []
    added_lines = []
    if suggested_patch and "```diff" in suggested_patch:
        removed_lines, added_lines = extract_effective_diff_changes(suggested_patch)
        if not removed_lines and not added_lines:
            warnings.append("diff 代码块中没有实际新增或删除的代码行。")
        elif removed_lines == added_lines:
            warnings.append("diff 新增和删除内容相同，可能是无效 no-op patch。")
        if added_lines and all(line.strip().startswith("#") or "#" in line for line in added_lines):
            warnings.append("diff 的新增内容主要是注释，可能没有修复实际代码。")

    primary_error_location = get_primary_error_location(error_locations or [])
    if primary_error_location and removed_lines:
        changed_text = "\n".join(removed_lines + added_lines)
        line_number = primary_error_location.get("line")
        try:
            source_lines = primary_error_location["file_path"].read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            source_lines = []
        if line_number and 1 <= line_number <= len(source_lines):
            primary_line = source_lines[line_number - 1].strip()
            if primary_line not in changed_text:
                warnings.append(f"diff 可能没有触及主故障行：{format_error_location(primary_error_location)}")

    allowed_paths = {str(path.relative_to(project_path)).replace("\\", "/") for path in selected_files}
    for diff_path in extract_diff_paths(response):
        normalized_path = diff_path.replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", normalized_path) or normalized_path.startswith("/"):
            warnings.append(f"diff 引用了绝对路径：{diff_path}")
        elif allowed_paths and normalized_path not in allowed_paths:
            warnings.append(f"diff 引用了未提供上下文的文件：{diff_path}")

    return warnings
