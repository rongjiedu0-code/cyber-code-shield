def format_error_location(location):
    """格式化错误位置，供 dry-run 和报告展示。"""
    suffix = ""
    if location.get("line"):
        suffix += f":{location['line']}"
    if location.get("column"):
        suffix += f":{location['column']}"
    return f"{location['relative_path']}{suffix}"


def get_primary_error_location(locations):
    """选择最可能需要修改的错误位置。"""
    if not locations:
        return None
    traceback_locations = [location for location in locations if location.get("kind") == "python_traceback"]
    if traceback_locations:
        return traceback_locations[-1]
    return locations[0]
