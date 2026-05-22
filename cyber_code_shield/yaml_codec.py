def parse_yaml_text(text):
    """
    一个轻量但对 Continue.dev config.yaml 足够鲁棒的 YAML 解析器。
    它支持缩进嵌套的 Map (dict)、List (list) 以及基本标量（bool, int, float, str）。
    """
    lines = []
    for line in text.splitlines():
        comment_idx = line.find('#')
        if comment_idx != -1:
            if comment_idx == 0 or line[comment_idx - 1].isspace():
                line = line[:comment_idx]
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(' '))
        lines.append((indent, stripped))

    if not lines:
        return {}

    def parse_value(val_str):
        val_str = val_str.strip()
        if not val_str:
            return None
        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            return val_str[1:-1]
        if val_str.lower() in ('true', 'yes', 'on'):
            return True
        if val_str.lower() in ('false', 'no', 'off'):
            return False
        if val_str.lower() == 'null':
            return None
        try:
            if '.' in val_str:
                return float(val_str)
            return int(val_str)
        except ValueError:
            return val_str

    def helper(index, parent_indent):
        if index >= len(lines):
            return None, index

        indent, content = lines[index]

        if content.startswith('-'):
            result = []
            while index < len(lines):
                cur_indent, cur_content = lines[index]
                if cur_indent < parent_indent:
                    break
                if cur_indent == parent_indent and cur_content.startswith('-'):
                    list_item_str = cur_content[1:].strip()
                    if not list_item_str:
                        if index + 1 < len(lines) and lines[index + 1][0] > cur_indent:
                            val, next_idx = helper(index + 1, lines[index + 1][0])
                            result.append(val)
                            index = next_idx
                        else:
                            result.append(None)
                            index += 1
                    elif ':' in list_item_str:
                        k, v = list_item_str.split(':', 1)
                        sub_map = {k.strip(): parse_value(v)}
                        index += 1
                        while index < len(lines):
                            sub_indent, sub_content = lines[index]
                            if sub_indent > cur_indent:
                                if ':' in sub_content:
                                    sk, sv = sub_content.split(':', 1)
                                    if not sv.strip() and index + 1 < len(lines) and lines[index + 1][0] > sub_indent:
                                        sval, next_idx = helper(index + 1, lines[index + 1][0])
                                        sub_map[sk.strip()] = sval
                                        index = next_idx
                                    else:
                                        sub_map[sk.strip()] = parse_value(sv)
                                        index += 1
                                else:
                                    index += 1
                            else:
                                break
                        result.append(sub_map)
                    else:
                        result.append(parse_value(list_item_str))
                        index += 1
                else:
                    break
            return result, index
        else:
            result = {}
            while index < len(lines):
                cur_indent, cur_content = lines[index]
                if cur_indent < parent_indent:
                    break
                if cur_indent == parent_indent:
                    if ':' in cur_content:
                        key, val_str = cur_content.split(':', 1)
                        key = key.strip()
                        val_str = val_str.strip()
                        if not val_str:
                            if index + 1 < len(lines) and lines[index + 1][0] > cur_indent:
                                val, next_idx = helper(index + 1, lines[index + 1][0])
                                result[key] = val
                                index = next_idx
                            else:
                                result[key] = None
                                index += 1
                        else:
                            result[key] = parse_value(val_str)
                            index += 1
                    else:
                        index += 1
                else:
                    index += 1
            return result, index

    root_indent = lines[0][0]
    res, _ = helper(0, root_indent)
    return res


def dump_yaml_text(data, indent=0):
    """
    将 Python 对象序列化为简单 YAML 格式的字符串。
    """
    lines = []
    spaces = " " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if value is None:
                lines.append(f"{spaces}{key}:")
            elif isinstance(value, (dict, list)):
                lines.append(f"{spaces}{key}:")
                lines.append(dump_yaml_text(value, indent + 2))
            else:
                if isinstance(value, bool):
                    val_str = "true" if value else "false"
                elif isinstance(value, str):
                    if ":" in value or "#" in value or "-" in value or " " in value:
                        val_str = f'"{value}"'
                    else:
                        val_str = value
                else:
                    val_str = str(value)
                lines.append(f"{spaces}{key}: {val_str}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{spaces}-")
                    continue
                first = True
                for key, value in item.items():
                    if first:
                        prefix = f"{spaces}- {key}:"
                        first = False
                    else:
                        prefix = f"{spaces}  {key}:"

                    if value is None:
                        lines.append(prefix)
                    elif isinstance(value, (dict, list)):
                        lines.append(prefix)
                        lines.append(dump_yaml_text(value, indent + 4))
                    else:
                        if isinstance(value, bool):
                            val_str = "true" if value else "false"
                        elif isinstance(value, str):
                            if ":" in value or "#" in value or "-" in value or " " in value:
                                val_str = f'"{value}"'
                            else:
                                val_str = value
                        else:
                            val_str = str(value)
                        lines.append(f"{prefix} {val_str}")
            elif isinstance(item, list):
                lines.append(f"{spaces}-")
                lines.append(dump_yaml_text(item, indent + 2))
            else:
                if isinstance(item, bool):
                    val_str = "true" if item else "false"
                elif isinstance(item, str):
                    if ":" in item or "#" in item or "-" in item or " " in item:
                        val_str = f'"{item}"'
                    else:
                        val_str = item
                else:
                    val_str = str(item)
                lines.append(f"{spaces}- {val_str}")
    else:
        if isinstance(data, bool):
            lines.append("true" if data else "false")
        else:
            lines.append(str(data))

    return "\n".join(lines)
