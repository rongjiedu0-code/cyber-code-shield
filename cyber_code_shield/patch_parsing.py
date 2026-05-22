import re


def extract_diff_paths(response):
    """提取 unified diff 中声明的文件路径。"""
    paths = []
    for line in response.splitlines():
        if not line.startswith(("--- ", "+++ ")):
            continue
        path = line[4:].strip()
        if path == "/dev/null":
            continue
        if path.startswith(("a/", "b/")):
            path = path[2:]
        paths.append(path)
    return list(dict.fromkeys(paths))


def extract_section_body(response, heading):
    """提取指定二级标题下的内容。"""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(response)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", response[match.end():], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(response)
    return response[match.end():end].strip()


def extract_effective_diff_changes(response):
    """提取 diff 中实际删除和新增的代码行，忽略文件头。"""
    removed = []
    added = []
    for line in response.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    return removed, added


def get_added_diff_lines(response):
    """提取 diff 新增行，忽略文件头。"""
    added_lines = []
    for line in response.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            added_lines.append(line[1:])
    return added_lines
