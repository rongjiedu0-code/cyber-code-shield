import json


def format_json(data):
    """统一 JSON 输出格式，确保写入文件和 dry-run 展示一致。"""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
