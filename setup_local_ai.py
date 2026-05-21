#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cyber-Code-Shield 本地 AI 配置安装脚本。

用途：
1. 自动定位当前用户的 Continue.dev 配置目录：~/.continue/config.yaml 或 config.json
2. 检查本机 Ollama 和本地模型是否准备好
3. 安全备份、安装、合并、恢复 Continue.dev 本地 AI 配置
4. 支持通过 profile 或命令行参数替换本地模型

常用命令：
python setup_local_ai.py --check
python setup_local_ai.py --dry-run
python setup_local_ai.py --install
python setup_local_ai.py --merge
python setup_local_ai.py --restore
python setup_local_ai.py --profile light --dry-run
python setup_local_ai.py --chat-model qwen2.5-coder:14b --embedding-model nomic-embed-text --install
"""

import argparse
import json
import os
import platform
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


DEFAULT_API_BASE = "http://localhost:11434"
DEFAULT_PROFILE = "balanced"
LOCAL_CHAT_TITLE = "Cyber-Code-Shield Local Chat"
LOCAL_AUTOCOMPLETE_TITLE = "Cyber-Code-Shield Local Autocomplete"
DEFAULT_CONFIG_FORMAT = "yaml"
PROJECT_CONTEXT_FILENAME = "CYBER_CODE_SHIELD_CONTEXT.md"
ENVIRONMENT_REPORT_FILENAME = "CYBER_CODE_SHIELD_REPORT.md"
PATCH_SUGGESTION_PREFIX = "CYBER_CODE_SHIELD_PATCH"
PATCH_MAX_FILES = 8
PATCH_MAX_FILE_CHARS = 12000
PATCH_LITE_MAX_FILES = 2
PATCH_LITE_MAX_FILE_CHARS = 3000
PATCH_MAX_ERROR_CHARS = 20000
PATCH_LITE_MAX_ERROR_CHARS = 4000
PATCH_OLLAMA_TIMEOUT_SECONDS = 180
PATCH_NUM_PREDICT = 1600
PATCH_LITE_NUM_PREDICT = 800
CLOUD_PROVIDER_HINTS = {
    "openai",
    "anthropic",
    "azure",
    "gemini",
    "google",
    "mistral",
    "cohere",
    "bedrock",
    "huggingface",
    "together",
    "groq",
    "openrouter",
}
CLOUD_API_ENV_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "HUGGINGFACE_API_KEY",
    "HF_TOKEN",
    "TOGETHER_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
]
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "target",
    "out",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "env",
}
SAMPLE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs"}

# 模型 profile 用于降低用户选择成本；后续如果发现更好的本地模型，优先改这里。
MODEL_PROFILES = {
    "light": {
        "label": "轻量机器",
        "chat_model": "qwen2.5-coder:7b",
        "autocomplete_model": "qwen2.5-coder:7b",
        "embedding_model": "nomic-embed-text",
    },
    "balanced": {
        "label": "默认均衡",
        "chat_model": "deepseek-coder-v2:16b",
        "autocomplete_model": "deepseek-coder-v2:16b",
        "embedding_model": "nomic-embed-text",
    },
    "strong": {
        "label": "高性能机器",
        "chat_model": "qwen2.5-coder:32b",
        "autocomplete_model": "qwen2.5-coder:32b",
        "embedding_model": "nomic-embed-text",
    },
}


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


def merge_continue_yaml(existing_yaml_data, local_yaml_data):
    """把 Cyber-Code-Shield 的 YAML 模型配置合并到已有的 Continue YAML 配置中。"""
    merged = dict(existing_yaml_data)
    merged["schema"] = "v1"
    
    existing_models = merged.get("models", [])
    if not isinstance(existing_models, list):
        existing_models = []
        
    local_models = local_yaml_data.get("models", [])
    if not isinstance(local_models, list):
        local_models = []
        
    ccs_model_names = {model.get("name") for model in local_models if isinstance(model, dict) and model.get("name")}
    
    preserved_models = [
        model for model in existing_models
        if not (isinstance(model, dict) and model.get("name") in ccs_model_names)
    ]
    
    merged["models"] = preserved_models + local_models
    return merged


def detect_os_name():
    """识别当前操作系统，方便终端用户确认脚本运行环境。"""
    system_name = platform.system().lower()

    if system_name == "windows":
        return "Windows"
    if system_name == "darwin":
        return "macOS"
    if system_name == "linux":
        return "Linux"

    return platform.system() or "Unknown"


def resolve_continue_config_path(config_format="yaml"):
    """根据当前用户 Home 目录解析 Continue.dev 的配置文件路径。"""
    home_dir = Path.home()
    continue_dir = home_dir / ".continue"
    filename = "config.yaml" if config_format == "yaml" else "config.json"
    config_path = continue_dir / filename
    backup_path = continue_dir / f"{filename}.bak"
    return continue_dir, config_path, backup_path


def resolve_model_config(args):
    """根据 profile 和命令行参数生成最终模型配置。"""
    profile = MODEL_PROFILES[args.profile].copy()
    profile["api_base"] = args.api_base

    # 命令行显式指定的模型优先级最高，方便后续快速替换模型做测试。
    if args.chat_model:
        profile["chat_model"] = args.chat_model
    if args.autocomplete_model:
        profile["autocomplete_model"] = args.autocomplete_model
    if args.embedding_model:
        profile["embedding_model"] = args.embedding_model

    return profile


def build_continue_yaml(model_config):
    """根据模型配置生成当前推荐的 Continue.dev config.yaml 文本。"""
    api_base = model_config["api_base"]
    chat_model = model_config["chat_model"]
    autocomplete_model = model_config["autocomplete_model"]
    embedding_model = model_config["embedding_model"]
    return f"""name: Cyber-Code-Shield Local Ollama
version: 0.1.0
schema: v1

models:
  - name: Cyber-Code-Shield Chat
    provider: ollama
    model: {chat_model}
    apiBase: {api_base}
    roles:
      - chat
      - edit
      - apply
      - summarize
    defaultCompletionOptions:
      temperature: 0.2
      keepAlive: 1800

  - name: Cyber-Code-Shield Autocomplete
    provider: ollama
    model: {autocomplete_model}
    apiBase: {api_base}
    roles:
      - autocomplete
    autocompleteOptions:
      debounceDelay: 350
      maxPromptTokens: 1024
      onlyMyCode: true
    defaultCompletionOptions:
      temperature: 0.3
      keepAlive: 1800

  - name: Cyber-Code-Shield Embeddings
    provider: ollama
    model: {embedding_model}
    apiBase: {api_base}
    roles:
      - embed
    embedOptions:
      maxChunkSize: 512
      maxBatchSize: 16
"""


def build_continue_config(model_config):
    """根据模型配置生成 legacy Continue.dev config.json 配置对象。"""
    chat_model = model_config["chat_model"]
    autocomplete_model = model_config["autocomplete_model"]
    embedding_model = model_config["embedding_model"]
    api_base = model_config["api_base"]

    return {
        "models": [
            {
                "title": LOCAL_CHAT_TITLE,
                "provider": "ollama",
                "model": chat_model,
                "apiBase": api_base,
            }
        ],
        "tabAutocompleteModel": {
            "title": LOCAL_AUTOCOMPLETE_TITLE,
            "provider": "ollama",
            "model": autocomplete_model,
            "apiBase": api_base,
        },
        "embeddingsProvider": {
            "provider": "ollama",
            "model": embedding_model,
            "apiBase": api_base,
        },
        "codebaseIndex": {
            "enabled": True,
            "indexingMode": "local",
            "embeddingsProvider": "ollama",
        },
    }


def get_required_models(model_config):
    """汇总当前配置需要的模型，去重后用于环境检查和拉取提示。"""
    model_names = [
        model_config["chat_model"],
        model_config["autocomplete_model"],
        model_config["embedding_model"],
    ]
    return list(dict.fromkeys(model_names))


def format_json(data):
    """统一 JSON 输出格式，确保写入文件和 dry-run 展示一致。"""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def format_config_json(model_config):
    """生成要写入 legacy Continue.dev config.json 的文本。"""
    return format_json(build_continue_config(model_config))


def format_config_text(model_config, config_format):
    """根据格式生成 Continue.dev 配置文本。"""
    if config_format == "yaml":
        return build_continue_yaml(model_config)
    return format_config_json(model_config)


def print_paths(model_config, config_format="yaml"):
    """输出当前系统、配置路径和模型选择，便于用户确认脚本会操作哪里。"""
    continue_dir, config_path, backup_path = resolve_continue_config_path(config_format)
    print(f"检测到操作系统：{detect_os_name()}")
    print(f"Python 版本：{platform.python_version()}")
    print(f"Continue.dev 配置目录：{continue_dir}")
    print(f"目标配置文件：{config_path}")
    print(f"主备份文件路径：{backup_path}")
    print(f"Ollama API 地址：{model_config['api_base']}")
    print(f"Chat 模型：{model_config['chat_model']}")
    print(f"补全模型：{model_config['autocomplete_model']}")
    print(f"Embedding 模型：{model_config['embedding_model']}")


def is_ollama_cli_installed():
    """检查 ollama 命令是否能在当前终端中找到。"""
    return shutil.which("ollama") is not None


def is_ollama_service_running(api_base):
    """检查本机 Ollama 服务是否在指定地址响应。"""
    try:
        with urllib.request.urlopen(f"{api_base}/api/tags", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def get_installed_ollama_models(api_base):
    """通过 Ollama 本地 API 获取已经安装的模型名称。"""
    try:
        with urllib.request.urlopen(f"{api_base}/api/tags", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    models = payload.get("models", [])
    return [model.get("name", "") for model in models if model.get("name")]


def run_check(model_config, config_format="yaml"):
    """执行安装前检查，告诉用户本机环境是否已经准备好。"""
    print_paths(model_config, config_format)
    print("\n环境检查：")

    ollama_cli_ok = is_ollama_cli_installed()
    print(f"[{'OK' if ollama_cli_ok else 'MISSING'}] Ollama 命令：{'已安装' if ollama_cli_ok else '未找到'}")

    ollama_service_ok = is_ollama_service_running(model_config["api_base"])
    print(f"[{'OK' if ollama_service_ok else 'MISSING'}] Ollama 服务：{'运行中' if ollama_service_ok else '未响应'}")

    installed_models = get_installed_ollama_models(model_config["api_base"]) if ollama_service_ok else []
    required_models = get_required_models(model_config)
    for model_name in required_models:
        model_ok = model_name in installed_models
        print(f"[{'OK' if model_ok else 'MISSING'}] 模型 {model_name}：{'已安装' if model_ok else '未找到'}")

    if not ollama_cli_ok:
        print("\n请先安装 Ollama。")

    if ollama_cli_ok and not ollama_service_ok:
        print("\n请先启动 Ollama 服务，然后重新运行检查。")

    missing_models = [model for model in required_models if model not in installed_models]
    if missing_models:
        print("\n缺失模型可用以下命令拉取：")
        for model_name in missing_models:
            print(f"  ollama pull {model_name}")


def choose_backup_path(backup_path):
    """选择备份路径，避免重复运行时覆盖第一次备份。"""
    if not backup_path.exists():
        return backup_path

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return backup_path.with_name(f"config.{timestamp}.bak")


def backup_existing_config(config_path, backup_path):
    """如果已有 Continue 配置，先备份，避免覆盖客户原始配置后无法恢复。"""
    if not config_path.exists():
        return None

    target_backup_path = choose_backup_path(backup_path)
    target_backup_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target_backup_path


def load_existing_config(config_path):
    """读取已有 Continue 配置，merge 模式下必须是合法 JSON。"""
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"现有 config.json 不是合法 JSON，无法安全合并 legacy JSON：{error}")
        return None


def merge_continue_config(existing_config, local_config):
    """把 Cyber-Code-Shield 配置合并到已有 Continue 配置中。"""
    merged_config = dict(existing_config)
    existing_models = merged_config.get("models", [])
    if not isinstance(existing_models, list):
        existing_models = []

    local_chat_model = local_config["models"][0]
    preserved_models = [
        model
        for model in existing_models
        if not (isinstance(model, dict) and model.get("title") == LOCAL_CHAT_TITLE)
    ]
    merged_config["models"] = preserved_models + [local_chat_model]
    merged_config["tabAutocompleteModel"] = local_config["tabAutocompleteModel"]
    merged_config["embeddingsProvider"] = local_config["embeddingsProvider"]
    merged_config["codebaseIndex"] = local_config["codebaseIndex"]
    return merged_config


def write_config(config_path, config_data):
    """写入 Continue.dev 配置文件。"""
    config_path.write_text(format_json(config_data), encoding="utf-8")


def install_config(model_config, dry_run=False, config_format="yaml"):
    """覆盖安装或预览本地 AI 配置。"""
    continue_dir, config_path, backup_path = resolve_continue_config_path(config_format)
    config_text = format_config_text(model_config, config_format)

    print_paths(model_config, config_format)

    if dry_run:
        print("\nDry-run 模式：不会修改任何文件。")
        print("\n覆盖安装将写入的配置内容：")
        print(config_text)
        return 0

    # 确保 ~/.continue 目录存在；parents=True 可自动创建缺失的父目录。
    continue_dir.mkdir(parents=True, exist_ok=True)

    # 如已有配置文件，先备份。第一次备份固定为 config.*.bak，后续备份带时间戳。
    actual_backup_path = backup_existing_config(config_path, backup_path)
    if actual_backup_path:
        print(f"已备份原配置到：{actual_backup_path}")
    else:
        print("未发现旧配置，无需备份。")

    # 覆盖写入本地优先、无云端 provider 的 Continue.dev 配置。
    config_path.write_text(config_text, encoding="utf-8")

    print("已覆盖安装 Cyber-Code-Shield 本地 AI 配置。")
    print_pull_hints(model_config)
    return 0


def merge_config(model_config, dry_run=False, config_format="yaml"):
    """保留已有配置，并追加或更新 Cyber-Code-Shield 本地 AI 配置。"""
    continue_dir, config_path, backup_path = resolve_continue_config_path(config_format)
    
    if config_format == "yaml":
        local_yaml_text = build_continue_yaml(model_config)
        local_yaml_data = parse_yaml_text(local_yaml_text)
        print_paths(model_config, config_format)
        
        if not config_path.exists():
            if dry_run:
                print("\nDry-run 模式：不会修改任何文件。")
                print("\n覆盖安装将写入的配置内容：")
                print(local_yaml_text)
                return 0
            continue_dir.mkdir(parents=True, exist_ok=True)
            config_path.write_text(local_yaml_text, encoding="utf-8")
            print("已创建并安装 Cyber-Code-Shield 本地 AI 配置。")
            print_pull_hints(model_config)
            return 0
            
        try:
            existing_yaml_data = parse_yaml_text(config_path.read_text(encoding="utf-8"))
        except Exception as error:
            print(f"现有 config.yaml 格式错误，无法合并：{error}")
            return 1
            
        merged_data = merge_continue_yaml(existing_yaml_data, local_yaml_data)
        merged_yaml_text = dump_yaml_text(merged_data)
        
        if dry_run:
            print("\nDry-run 模式：不会修改任何文件。")
            print("\n合并后将写入的配置内容：")
            print(merged_yaml_text)
            return 0
            
        continue_dir.mkdir(parents=True, exist_ok=True)
        actual_backup_path = backup_existing_config(config_path, backup_path)
        if actual_backup_path:
            print(f"已备份原配置到：{actual_backup_path}")
        else:
            print("未发现旧配置，将创建新的 Continue.dev 配置。")
            
        config_path.write_text(merged_yaml_text, encoding="utf-8")
        print("已合并 Cyber-Code-Shield 本地 AI 配置，并保留现有配置项。")
        print_pull_hints(model_config)
        return 0

    continue_dir, config_path, backup_path = resolve_continue_config_path(config_format)
    local_config = build_continue_config(model_config)

    print_paths(model_config, config_format)
    existing_config = load_existing_config(config_path)
    if existing_config is None:
        return 1

    merged_config = merge_continue_config(existing_config, local_config)

    if dry_run:
        print("\nDry-run 模式：不会修改任何文件。")
        print("\n合并后将写入的配置内容：")
        print(format_json(merged_config))
        return 0

    continue_dir.mkdir(parents=True, exist_ok=True)
    actual_backup_path = backup_existing_config(config_path, backup_path)
    if actual_backup_path:
        print(f"已备份原配置到：{actual_backup_path}")
    else:
        print("未发现旧配置，将创建新的 Continue.dev 配置。")

    write_config(config_path, merged_config)
    print("已合并 Cyber-Code-Shield 本地 AI 配置，并保留现有配置项。")
    print_pull_hints(model_config)
    return 0


def print_pull_hints(model_config):
    """提示用户拉取当前配置所需模型。"""
    print("请确认 Ollama 已安装，并已提前拉取模型：")
    for model_name in get_required_models(model_config):
        print(f"  ollama pull {model_name}")
    print("完成后重启 VS Code，并在 Continue.dev 中使用 @Codebase 进行离线代码库检索。")


def restore_config(model_config, config_format="yaml"):
    """从 config 备份恢复用户原来的 Continue.dev 配置。"""
    _, config_path, backup_path = resolve_continue_config_path(config_format)
    print_paths(model_config, config_format)

    if not backup_path.exists():
        print(f"未找到备份文件 {backup_path}，无法恢复。")
        return 1

    config_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"已从主备份恢复配置：{backup_path} -> {config_path}")
    return 0


def should_skip_dir(dir_name):
    """跳过依赖、构建产物和版本库目录，避免扫描无关或超大内容。"""
    return dir_name in IGNORED_DIRS


def iter_project_files(project_path):
    """遍历项目文件，排除常见依赖和构建目录。"""
    for path in project_path.rglob("*"):
        if any(should_skip_dir(part) for part in path.relative_to(project_path).parts[:-1]):
            continue
        if path.is_file():
            yield path


def read_json_file(path):
    """读取 JSON 配置文件，失败时返回空字典，避免项目分析中断。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def detect_languages(files):
    """根据文件扩展名粗略识别项目语言。"""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript/React",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cs": "C#",
        ".php": "PHP",
        ".rb": "Ruby",
    }
    counts = {}
    for file_path in files:
        language = extension_map.get(file_path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def detect_package_managers(project_path):
    """通过锁文件和配置文件识别包管理器。"""
    markers = {
        "package-lock.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "requirements.txt": "pip",
        "pyproject.toml": "Poetry/Python packaging",
        "Pipfile": "pipenv",
        "pom.xml": "Maven",
        "build.gradle": "Gradle",
        "build.gradle.kts": "Gradle",
        "go.mod": "Go modules",
        "Cargo.toml": "Cargo",
    }
    found = []
    for marker, manager in markers.items():
        if (project_path / marker).exists():
            found.append(manager)
    return found


def detect_python_packages(project_path):
    """解析 requirements.txt 或 pyproject.toml 查找 Python 依赖包。"""
    packages = set()
    req_path = project_path / "requirements.txt"
    if req_path.exists():
        try:
            for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                match = re.match(r"^([A-Za-z0-9_-]+)", stripped)
                if match:
                    packages.add(match.group(1).lower())
        except OSError:
            pass
            
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'^\s*([A-Za-z0-9_-]+)\s*=\s*[\'"{]', content, re.MULTILINE):
                packages.add(match.group(1).lower())
        except OSError:
            pass
            
    return packages


def detect_frameworks(project_path):
    """基于常见依赖和配置文件识别框架。"""
    frameworks = []
    package_json_path = project_path / "package.json"
    if package_json_path.exists():
        package_json = read_json_file(package_json_path)
        dependencies = {}
        dependencies.update(package_json.get("dependencies", {}))
        dependencies.update(package_json.get("devDependencies", {}))
        dependency_names = set(dependencies.keys())

        framework_markers = {
            "react": "React",
            "next": "Next.js",
            "vue": "Vue",
            "nuxt": "Nuxt",
            "svelte": "Svelte",
            "express": "Express",
            "nestjs": "NestJS",
            "vite": "Vite",
            "jest": "Jest",
            "vitest": "Vitest",
        }
        for dependency, framework in framework_markers.items():
            if dependency in dependency_names:
                frameworks.append(framework)

    python_packages = detect_python_packages(project_path)
    python_framework_markers = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "tornado": "Tornado",
        "streamlit": "Streamlit",
    }
    for pkg, name in python_framework_markers.items():
        if pkg in python_packages:
            frameworks.append(name)

    python_markers = {
        "manage.py": "Django",
        "app.py": "Python app",
        "main.py": "Python app",
    }
    for marker, framework in python_markers.items():
        if (project_path / marker).exists():
            frameworks.append(framework)

    if (project_path / "go.mod").exists():
        frameworks.append("Go")
    if (project_path / "Cargo.toml").exists():
        frameworks.append("Rust")
    if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
        frameworks.append("Java")

    return list(dict.fromkeys(frameworks))


def detect_test_tools(project_path):
    """识别常见测试工具。"""
    tools = []
    package_json_path = project_path / "package.json"
    if package_json_path.exists():
        package_json = read_json_file(package_json_path)
        dependencies = {}
        dependencies.update(package_json.get("dependencies", {}))
        dependencies.update(package_json.get("devDependencies", {}))
        scripts = package_json.get("scripts", {})
        dependency_names = set(dependencies.keys())

        for tool in ["jest", "vitest", "mocha", "playwright", "cypress"]:
            if tool in dependency_names or tool in " ".join(scripts.values()).lower():
                tools.append(tool)

    python_packages = detect_python_packages(project_path)
    if "pytest" in python_packages:
        tools.append("pytest")
    if "unittest" in python_packages:
        tools.append("unittest")

    if (project_path / "pytest.ini").exists() or (project_path / "conftest.py").exists():
        tools.append("pytest")
    if (project_path / "go.mod").exists():
        tools.append("go test")
    if (project_path / "Cargo.toml").exists():
        tools.append("cargo test")

    return list(dict.fromkeys(tools))


def build_directory_snapshot(project_path, max_entries=80):
    """生成轻量目录快照，不展开依赖和构建产物。"""
    entries = []
    for path in sorted(project_path.rglob("*")):
        relative_path = path.relative_to(project_path)
        if any(should_skip_dir(part) for part in relative_path.parts):
            continue
        depth = len(relative_path.parts) - 1
        if depth > 2:
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{'  ' * depth}- {relative_path.name}{suffix}")
        if len(entries) >= max_entries:
            entries.append("- ...")
            break
    return entries


def choose_sample_files(project_path, files, max_files=12):
    """选择少量代表性代码文件，用于推断风格，不读取整个项目。"""
    preferred_parts = ("src", "app", "lib", "components", "pages", "server", "api", "tests", "test")
    candidates = []
    for file_path in files:
        if file_path.suffix.lower() not in SAMPLE_EXTENSIONS:
            continue
        try:
            if file_path.stat().st_size > 80_000:
                continue
        except OSError:
            continue
        relative = file_path.relative_to(project_path)
        score = 0
        if any(part in preferred_parts for part in relative.parts):
            score += 10
        if file_path.name.lower() in {"main.py", "app.py", "index.ts", "index.tsx", "index.js", "main.ts", "main.go"}:
            score += 5
        score -= len(relative.parts)
        candidates.append((score, str(relative), file_path))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [file_path for _, _, file_path in candidates[:max_files]]


def infer_style_from_samples(project_path, sample_files):
    """从少量样例文件中推断缩进、命名和代码组织线索。"""
    indent_tabs = 0
    indent_two_spaces = 0
    indent_four_spaces = 0
    semicolon_lines = 0
    total_code_lines = 0
    naming_clues = set()

    for file_path in sample_files:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:120]
        except OSError:
            continue

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            total_code_lines += 1
            if line.startswith("\t"):
                indent_tabs += 1
            elif line.startswith("    "):
                indent_four_spaces += 1
            elif line.startswith("  "):
                indent_two_spaces += 1
            if stripped.endswith(";"):
                semicolon_lines += 1
            if "const " in line or "let " in line:
                naming_clues.add("JavaScript/TypeScript uses const/let")
            if "function " in line:
                naming_clues.add("Function declarations are present")
            if "class " in line:
                naming_clues.add("Class-based code appears")
            if "interface " in line or "type " in line:
                naming_clues.add("TypeScript type/interface definitions appear")
            if "def " in line:
                naming_clues.add("Python functions use def")

    indent_style = "Not enough sample data"
    indent_counts = [
        (indent_tabs, "tabs"),
        (indent_two_spaces, "2 spaces"),
        (indent_four_spaces, "4 spaces"),
    ]
    best_indent = max(indent_counts, key=lambda item: item[0])
    if best_indent[0] > 0:
        indent_style = best_indent[1]

    semicolon_style = "Not enough sample data"
    if total_code_lines:
        ratio = semicolon_lines / total_code_lines
        semicolon_style = "Semicolons are common" if ratio > 0.25 else "Semicolons are uncommon"

    sample_paths = [str(path.relative_to(project_path)) for path in sample_files]
    return {
        "indent_style": indent_style,
        "semicolon_style": semicolon_style,
        "naming_clues": sorted(naming_clues),
        "sample_paths": sample_paths,
    }


def build_project_context(project_path):
    """生成现有项目的本地上下文摘要。"""
    files = list(iter_project_files(project_path))
    languages = detect_languages(files)
    package_managers = detect_package_managers(project_path)
    frameworks = detect_frameworks(project_path)
    test_tools = detect_test_tools(project_path)
    directory_snapshot = build_directory_snapshot(project_path)
    sample_files = choose_sample_files(project_path, files)
    style_summary = infer_style_from_samples(project_path, sample_files)

    return {
        "project_path": str(project_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "file_count_scanned": len(files),
        "languages": languages,
        "package_managers": package_managers,
        "frameworks": frameworks,
        "test_tools": test_tools,
        "directory_snapshot": directory_snapshot,
        "style_summary": style_summary,
    }


def render_project_context(context):
    """把项目上下文摘要渲染成 Markdown，方便用户和本地 AI 阅读。"""
    languages = context["languages"] or [("Unknown", 0)]
    package_managers = context["package_managers"] or ["Not detected"]
    frameworks = context["frameworks"] or ["Not detected"]
    test_tools = context["test_tools"] or ["Not detected"]
    style_summary = context["style_summary"]

    lines = [
        "# Cyber-Code-Shield Project Context",
        "",
        "This file was generated locally by Cyber-Code-Shield.",
        "It is intended to help a local AI coding assistant follow the existing project's structure and style.",
        "",
        "## Project metadata",
        "",
        f"- Project path: `{context['project_path']}`",
        f"- Generated at: `{context['generated_at']}`",
        f"- Files scanned: `{context['file_count_scanned']}`",
        "",
        "## Detected languages",
        "",
    ]

    for language, count in languages:
        lines.append(f"- {language}: {count} files")

    lines.extend(["", "## Package managers", ""])
    for manager in package_managers:
        lines.append(f"- {manager}")

    lines.extend(["", "## Framework and tool hints", ""])
    for framework in frameworks:
        lines.append(f"- {framework}")

    lines.extend(["", "## Test tools", ""])
    for tool in test_tools:
        lines.append(f"- {tool}")

    lines.extend([
        "",
        "## Directory snapshot",
        "",
        "```text",
        *context["directory_snapshot"],
        "```",
        "",
        "## Style hints",
        "",
        f"- Indentation: {style_summary['indent_style']}",
        f"- Semicolon usage: {style_summary['semicolon_style']}",
    ])

    if style_summary["naming_clues"]:
        lines.append("- Code clues:")
        for clue in style_summary["naming_clues"]:
            lines.append(f"  - {clue}")

    lines.extend(["", "## Sample files used for style inference", ""])
    if style_summary["sample_paths"]:
        for sample_path in style_summary["sample_paths"]:
            lines.append(f"- `{sample_path}`")
    else:
        lines.append("- No suitable sample files found")

    lines.extend([
        "",
        "## Guidance for local AI coding",
        "",
        "- Prefer existing directory structure over introducing new top-level folders.",
        "- Match the detected language, framework, and package manager choices.",
        "- Follow the indentation and semicolon style summarized above.",
        "- Before adding new dependencies, check whether the project already has an equivalent utility or pattern.",
        "- Keep changes small and aligned with the current codebase style.",
        "",
    ])
    return "\n".join(lines)


def analyze_project(project_arg, dry_run=False):
    """分析已有项目，并生成本地上下文摘要文件。"""
    project_path = Path(project_arg).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"项目路径不存在或不是目录：{project_path}")
        return 1

    context = build_project_context(project_path)
    rendered_context = render_project_context(context)
    output_path = project_path / PROJECT_CONTEXT_FILENAME

    print(f"项目路径：{project_path}")
    print(f"扫描文件数：{context['file_count_scanned']}")
    print(f"上下文文件：{output_path}")

    if dry_run:
        print("\nDry-run 模式：不会写入项目文件。")
        print("\n将生成的项目上下文摘要：")
        print(rendered_context)
        return 0

    output_path.write_text(rendered_context, encoding="utf-8")
    print(f"已生成项目上下文摘要：{output_path}")
    return 0


def truncate_text(text, max_chars):
    """限制提供给本地模型的文本长度，避免一次塞入过多内容。"""
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[Truncated by Cyber-Code-Shield]", True


def read_limited_text(path, max_chars):
    """读取文本文件并限制长度。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return truncate_text(text, max_chars)


def is_path_inside(parent, child):
    """确认 child 路径位于 parent 内部。"""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_ignored_project_path(project_path, candidate_path):
    """判断候选文件是否位于应跳过的项目目录中。"""
    try:
        relative = candidate_path.relative_to(project_path)
    except ValueError:
        return True
    return any(should_skip_dir(part) for part in relative.parts[:-1])


def resolve_project_file(project_path, file_arg):
    """解析用户指定的项目文件，并拒绝项目外或忽略目录中的文件。"""
    candidate = Path(file_arg).expanduser()
    if not candidate.is_absolute():
        candidate = project_path / candidate
    candidate = candidate.resolve()

    if not is_path_inside(project_path, candidate):
        raise ValueError(f"文件不在项目目录内：{file_arg}")
    if is_ignored_project_path(project_path, candidate):
        raise ValueError(f"文件位于忽略目录中：{file_arg}")
    if not candidate.exists() or not candidate.is_file():
        raise ValueError(f"文件不存在或不是普通文件：{file_arg}")

    return candidate


def build_error_location(project_path, file_arg, line, column, raw, kind):
    """把错误日志中的路径和行号解析为安全的项目内位置。"""
    file_path = resolve_project_file(project_path, file_arg.strip())
    return {
        "file_path": file_path,
        "relative_path": str(file_path.relative_to(project_path)),
        "line": int(line) if line else None,
        "column": int(column) if column else None,
        "raw": raw.strip(),
        "kind": kind,
    }


def extract_error_locations_from_text(project_path, text):
    """从错误文本中提取结构化文件、行号和列号信息。"""
    locations = []
    seen = set()
    patterns = [
        ("python_traceback", re.compile(r'File "([^"]+)", line (\d+)(?:, in [^\n]+)?')),
        ("python_traceback", re.compile(r"File '([^']+)', line (\d+)(?:, in [^\n]+)?")),
        ("node_stack", re.compile(r"\bat\s+(?:[^()\n]+\()?([^()\s]+\.[A-Za-z0-9_]+):(\d+):(\d+)\)?")),
        ("generic_diagnostic", re.compile(r"(?<![A-Za-z0-9_./\\:-])((?:[A-Za-z]:[\\/])?[^\s:()]+\.(?:py|js|jsx|ts|tsx|java|go|rs|cs|php|rb|mjs|cjs|mts|cts|vue|svelte)):(\d+)(?::(\d+))?")),
    ]

    for line_text in text.splitlines():
        for kind, pattern in patterns:
            for match in pattern.finditer(line_text):
                file_arg = match.group(1)
                line_number = match.group(2) if len(match.groups()) >= 2 else None
                column = match.group(3) if len(match.groups()) >= 3 else None
                try:
                    location = build_error_location(project_path, file_arg, line_number, column, line_text, kind)
                except ValueError:
                    continue
                key = (location["file_path"], location["line"], location["column"])
                if key in seen:
                    continue
                seen.add(key)
                locations.append(location)

    return locations


def extract_file_mentions_from_text(project_path, text):
    """从错误文本中提取可能的项目文件路径。"""
    candidates = [location["file_path"] for location in extract_error_locations_from_text(project_path, text)]
    patterns = [
        r'File "([^"]+)"',
        r"File '([^']+)'",
        r"([A-Za-z]:[\\/][^\s:]+\.[A-Za-z0-9_]+)",
        r"((?:\.?\.?[\\/])?[^\s:]+\.(?:py|js|jsx|ts|tsx|java|go|rs|cs|php|rb))",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text):
            try:
                candidates.append(resolve_project_file(project_path, match.strip()))
            except ValueError:
                continue

    return list(dict.fromkeys(candidates))


def collect_patch_files(project_path, explicit_files, request_text, context_lite=False):
    """为补丁助手选择少量上下文文件。"""
    max_files = PATCH_LITE_MAX_FILES if context_lite else PATCH_MAX_FILES
    if explicit_files:
        selected = [resolve_project_file(project_path, file_arg) for file_arg in explicit_files]
        return list(dict.fromkeys(selected))[:max_files]

    mentioned_files = extract_file_mentions_from_text(project_path, request_text)
    if mentioned_files:
        return mentioned_files[:max_files]

    files = list(iter_project_files(project_path))
    return choose_sample_files(project_path, files, max_files=max_files)


def find_todo_markers(project_path, file_paths, max_markers=20):
    """在用户指定文件中查找明显的 TODO 或未实现标记。"""
    marker_patterns = [
        re.compile(r"\bTODO\b", re.IGNORECASE),
        re.compile(r"\bFIXME\b", re.IGNORECASE),
        re.compile(r"^\s*pass\s*(?:#.*)?$"),
        re.compile(r"raise\s+NotImplementedError\b"),
        re.compile(r"NotImplementedError\s*\("),
        re.compile(r"throw\s+new\s+Error\s*\(\s*['\"](?:TODO|Not implemented)['\"]\s*\)", re.IGNORECASE),
    ]
    markers = []

    for file_path in file_paths:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for index, line in enumerate(lines):
            if not any(pattern.search(line) for pattern in marker_patterns):
                continue

            start = max(0, index - 4)
            end = min(len(lines), index + 9)
            snippet_lines = [
                f"{line_number + 1}: {lines[line_number]}"
                for line_number in range(start, end)
            ]
            markers.append({
                "file_path": file_path,
                "relative_path": str(file_path.relative_to(project_path)),
                "line_number": index + 1,
                "line": line.strip(),
                "snippet": "\n".join(snippet_lines),
            })
            if len(markers) >= max_markers:
                return markers

    return markers


def render_todo_markers(markers):
    """把 TODO/未实现标记渲染成给本地模型使用的任务上下文。"""
    sections = []
    for marker in markers:
        sections.extend([
            f"## Marker: {marker['relative_path']}:{marker['line_number']}",
            "",
            f"Matched line: `{marker['line']}`",
            "",
            "```text",
            marker["snippet"],
            "```",
            "",
        ])
    return "\n".join(sections)


def format_error_location(location):
    """格式化错误位置，供 dry-run 和报告展示。"""
    suffix = ""
    if location.get("line"):
        suffix += f":{location['line']}"
    if location.get("column"):
        suffix += f":{location['column']}"
    return f"{location['relative_path']}{suffix}"


def render_error_location_list(locations):
    """渲染检测到的错误位置列表。"""
    if not locations:
        return "No structured error locations detected."
    return "\n".join(
        f"- `{format_error_location(location)}` — {location['kind']}"
        for location in locations
    )


def render_error_location_snippets(project_path, locations, context_radius=6, max_locations=8):
    """渲染错误行附近的聚焦代码片段。"""
    if not locations:
        return ""

    sections = []
    for location in locations[:max_locations]:
        title = format_error_location(location)
        sections.extend([
            f"## Error location: {title}",
            "",
            f"Raw diagnostic: {location['raw']}",
            "",
        ])

        line_number = location.get("line")
        if not line_number:
            sections.append("No line number was detected for this location.")
            sections.append("")
            continue

        try:
            lines = location["file_path"].read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as error:
            sections.append(f"Could not read file: {error}")
            sections.append("")
            continue

        index = line_number - 1
        start = max(0, index - context_radius)
        end = min(len(lines), index + context_radius + 1)
        snippet_lines = []
        for current_index in range(start, end):
            marker = ">" if current_index == index else " "
            snippet_lines.append(f"{marker} {current_index + 1}: {lines[current_index]}")

        sections.extend([
            "```text",
            *snippet_lines,
            "```",
            "",
        ])

    return "\n".join(sections)


def render_file_snippets(project_path, file_paths, context_lite=False):
    """把选中的项目文件渲染成受限代码片段。"""
    max_file_chars = PATCH_LITE_MAX_FILE_CHARS if context_lite else PATCH_MAX_FILE_CHARS
    if not file_paths:
        return "No project files were selected."

    sections = []
    for file_path in file_paths:
        relative_path = file_path.relative_to(project_path)
        try:
            content, truncated = read_limited_text(file_path, max_file_chars)
        except OSError as error:
            content = f"[Could not read file: {error}]"
            truncated = False

        sections.extend([
            f"## File: {relative_path}",
            "",
            "```text",
            content,
            "```",
        ])
        if truncated:
            sections.append("[File content was truncated by Cyber-Code-Shield]")
        sections.append("")

    return "\n".join(sections)


def render_lite_project_context(context):
    """渲染适合本地大模型快速验证的精简项目上下文。"""
    languages = context["languages"] or [("Unknown", 0)]
    style_summary = context["style_summary"]
    lines = [
        "# Project Context Lite",
        "",
        f"- Project path: `{context['project_path']}`",
        f"- Files scanned: `{context['file_count_scanned']}`",
        "- Languages: " + ", ".join(f"{language} ({count})" for language, count in languages[:5]),
        "- Frameworks: " + ", ".join(context["frameworks"][:5] or ["Not detected"]),
        "- Test tools: " + ", ".join(context["test_tools"][:5] or ["Not detected"]),
        f"- Indentation: {style_summary['indent_style']}",
        f"- Semicolon usage: {style_summary['semicolon_style']}",
        "",
        "## Directory snapshot",
        "",
        "```text",
        *context["directory_snapshot"][:30],
        "```",
    ]
    return "\n".join(lines)


def build_patch_prompt(task_type, project_context_markdown, user_request, file_snippets):
    """构建本地补丁助手提示词。"""
    task_labels = {
        "fix_error": "Fix an error",
        "suggest_patch": "Suggest a patch",
        "complete_todo": "Complete TODO or incomplete implementation",
    }
    task_label = task_labels.get(task_type, "Suggest a patch")
    todo_rules = """
TODO completion rules:
- Complete only the detected TODO/pass/NotImplemented marker unless the user explicitly asks for a broader change.
- Prefer the smallest implementation that matches surrounding code style.
- Do not invent broader architecture or unrelated files.
- Keep validation examples consistent with the docstring, comments, and stated constraints.
- Prefer reusing examples already present in the code comments or docstring.
- Do not invent additional validation examples unless they are trivial and you have checked them against every stated constraint.
- Do not label an example valid if it violates a length, type, format, or allowed-character constraint.
- The completed function should enforce its own documented constraints instead of relying on callers to pre-normalize or pre-validate input.
- If a constraint says lowercase ASCII letters only, do not use broad checks that also accept uppercase or Unicode letters.
- If you are unsure about edge cases, say what is uncertain instead of inventing examples.
""" if task_type == "complete_todo" else ""
    return f"""You are Cyber-Code-Shield Local Patch Assistant.

You run in a local-first coding workflow. You are not an autonomous agent and you must not claim that you modified files.

Task type: {task_label}

Rules:
- Generate a small, human-reviewable patch suggestion.
- Prefer fixing only the files shown in the context.
- Do not invent new files unless clearly necessary.
- Do not add dependencies unless the user explicitly asks for them.
- Follow the existing project structure and style hints.
- If there is not enough context, state what is missing instead of guessing.
- If confidence is low, explain what is missing before suggesting a patch.
- Do not invent files, APIs, tests, or business rules to make a patch look complete.
- Output a unified diff when possible, but do not force a diff when missing context makes it unsafe.
{todo_rules}
Required response sections:
1. Confidence
   - Use High, Medium, or Low.
   - Briefly explain the rating.
2. Missing context
   - List needed files, logs, tests, schemas, or business rules.
   - Write "None identified" only when the shown context is enough for the suggestion.
3. Explanation
4. Suggested patch
5. Validation suggestions
6. Risks or assumptions

# User request or error

```text
{user_request}
```

# Project context

{project_context_markdown}

# Relevant file snippets

{file_snippets}
"""


def call_ollama_chat(api_base, model_name, prompt, timeout_seconds=PATCH_OLLAMA_TIMEOUT_SECONDS, num_predict=PATCH_NUM_PREDICT):
    """调用本地 Ollama 生成补丁建议。"""
    endpoint = api_base.rstrip("/") + "/api/chat"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "无法调用本地 Ollama 生成补丁建议。请确认 ollama serve 已启动、--api-base 正确、模型已 pull。"
            f"\n原始错误：{error}"
        ) from error

    message = data.get("message") if isinstance(data, dict) else None
    model_response = message.get("content") if isinstance(message, dict) else None
    if not model_response:
        raise RuntimeError("Ollama 响应中没有 message.content 字段，无法生成补丁建议。")
    return model_response


def get_default_patch_output_path(project_path, task_type):
    """生成默认补丁建议输出路径。"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_name = task_type.upper()
    return project_path / f"{PATCH_SUGGESTION_PREFIX}_{task_name}_{timestamp}.md"


def render_patch_suggestion(task_type, project_path, model_config, selected_files, model_response, user_request, context_lite, patch_timeout, num_predict, error_locations=None):
    """把模型输出包装成补丁建议 Markdown。"""
    task_titles = {
        "fix_error": "Fix Error",
        "suggest_patch": "Suggest Patch",
        "complete_todo": "Complete TODO",
    }
    task_title = task_titles.get(task_type, "Suggest Patch")
    lines = [
        "# Cyber-Code-Shield Patch Suggestion",
        "",
        "This file was generated locally by Cyber-Code-Shield.",
        "Source files were not modified automatically.",
        "",
        "## Metadata",
        "",
        f"- Task type: {task_title}",
        f"- Project path: `{project_path}`",
        f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- Model: `{model_config['chat_model']}`",
        f"- API base: `{model_config['api_base']}`",
        f"- Context lite: `{'yes' if context_lite else 'no'}`",
        f"- Timeout seconds: `{patch_timeout}`",
        f"- Max generated tokens: `{num_predict}`",
        "- Thinking output requested: `no`",
        "",
        "## User request",
        "",
        "```text",
        user_request.strip(),
        "```",
        "",
    ]

    if error_locations:
        lines.extend([
            "## Detected error locations",
            "",
            render_error_location_list(error_locations),
            "",
        ])

    lines.extend([
        "## Files reviewed",
        "",
    ])

    if selected_files:
        for file_path in selected_files:
            lines.append(f"- `{file_path.relative_to(project_path)}`")
    else:
        lines.append("- No project files were selected")

    lines.extend([
        "",
        "## Safety notes",
        "",
        "- This is a patch suggestion, not an applied change.",
        "- Review the diff and validation suggestions before editing source files.",
        "- The output depends on the selected local model and provided context.",
        "",
        "## Model response",
        "",
        model_response.strip(),
        "",
    ])
    return "\n".join(lines)


def resolve_patch_output_path(project_path, output_arg, task_type):
    """解析补丁建议输出路径。"""
    if output_arg:
        return Path(output_arg).expanduser().resolve()
    return get_default_patch_output_path(project_path, task_type)


def preview_patch_prompt(project_path, output_path, selected_files, prompt, error_locations=None):
    """打印补丁助手 dry-run 预览。"""
    print(f"项目路径：{project_path}")
    print(f"补丁建议文件：{output_path}")
    print("参考文件：")
    if selected_files:
        for file_path in selected_files:
            print(f"- {file_path.relative_to(project_path)}")
    else:
        print("- 未选择项目文件")
    if error_locations:
        print("\n检测到的错误位置：")
        print(render_error_location_list(error_locations))
    print("\nDry-run 模式：不会调用 Ollama，也不会写入补丁建议文件。")
    print("\n将发送给本地模型的提示词预览：")
    print(prompt)


def run_patch_assistant(model_config, task_type, project_arg, user_request, files_arg, patch_output_arg, dry_run, patch_timeout, context_lite, error_locations=None):
    """运行本地补丁助手通用流程。"""
    if not project_arg:
        print("补丁助手命令需要指定 --project。")
        return 1
    if not is_local_api_base(model_config["api_base"]):
        print("补丁助手只允许使用本机 Ollama API，请将 --api-base 指向 localhost、127.0.0.1 或 ::1。")
        return 1

    project_path = Path(project_arg).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"项目路径不存在或不是目录：{project_path}")
        return 1

    try:
        selected_files = collect_patch_files(project_path, files_arg, user_request, context_lite=context_lite)
    except ValueError as error:
        print(f"文件选择无效：{error}")
        return 1

    context = build_project_context(project_path)
    project_context_markdown = render_lite_project_context(context) if context_lite else render_project_context(context)
    file_snippets = render_file_snippets(project_path, selected_files, context_lite=context_lite)
    prompt = build_patch_prompt(task_type, project_context_markdown, user_request, file_snippets)
    output_path = resolve_patch_output_path(project_path, patch_output_arg, task_type)

    if dry_run:
        preview_patch_prompt(project_path, output_path, selected_files, prompt, error_locations=error_locations)
        return 0

    try:
        num_predict = PATCH_LITE_NUM_PREDICT if context_lite else PATCH_NUM_PREDICT
        model_response = call_ollama_chat(model_config["api_base"], model_config["chat_model"], prompt, patch_timeout, num_predict)
    except RuntimeError as error:
        print(error)
        return 1

    rendered_suggestion = render_patch_suggestion(
        task_type,
        project_path,
        model_config,
        selected_files,
        model_response,
        user_request,
        context_lite,
        patch_timeout,
        num_predict,
        error_locations=error_locations,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_suggestion, encoding="utf-8")
    print(f"已生成本地补丁建议：{output_path}")
    print("未自动修改任何源码文件，请人工审查后再应用建议。")
    return 0


def run_fix_error(model_config, project_arg, error_log_arg, error_text_arg, files_arg, patch_output_arg, dry_run, patch_timeout, context_lite):
    """根据错误日志生成本地修复建议。"""
    if bool(error_log_arg) == bool(error_text_arg):
        print("--fix-error 需要且只能指定 --error-log 或 --error-text 其中一个。")
        return 1
    if not project_arg:
        print("--fix-error 需要指定 --project。")
        return 1

    project_path = Path(project_arg).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"项目路径不存在或不是目录：{project_path}")
        return 1

    if error_log_arg:
        error_log_path = Path(error_log_arg).expanduser().resolve()
        if not error_log_path.exists() or not error_log_path.is_file():
            print(f"错误日志不存在或不是普通文件：{error_log_path}")
            return 1
        try:
            max_error_chars = PATCH_LITE_MAX_ERROR_CHARS if context_lite else PATCH_MAX_ERROR_CHARS
            raw_error, truncated = read_limited_text(error_log_path, max_error_chars)
        except OSError as error:
            print(f"无法读取错误日志：{error}")
            return 1
        if truncated:
            print("错误日志较长，已截断后提供给本地模型。")
    else:
        max_error_chars = PATCH_LITE_MAX_ERROR_CHARS if context_lite else PATCH_MAX_ERROR_CHARS
        raw_error, truncated = truncate_text(error_text_arg, max_error_chars)
        if truncated:
            print("错误文本较长，已截断后提供给本地模型。")

    error_locations = extract_error_locations_from_text(project_path, raw_error)
    focused_snippets = render_error_location_snippets(project_path, error_locations)
    structured_sections = [
        "Raw error:",
        "```text",
        raw_error,
        "```",
    ]
    if error_locations:
        structured_sections.extend([
            "",
            "Detected error locations:",
            render_error_location_list(error_locations),
        ])
    if focused_snippets:
        structured_sections.extend([
            "",
            "Focused error snippets:",
            focused_snippets,
        ])
    user_request = "\n".join(structured_sections)

    location_files = [str(location["file_path"].relative_to(project_path)) for location in error_locations]
    files_for_context = files_arg or location_files or None

    return run_patch_assistant(
        model_config,
        "fix_error",
        project_arg,
        user_request,
        files_for_context,
        patch_output_arg,
        dry_run,
        patch_timeout,
        context_lite,
        error_locations=error_locations,
    )


def run_suggest_patch(model_config, project_arg, task_arg, files_arg, patch_output_arg, dry_run, patch_timeout, context_lite):
    """根据用户任务描述生成本地补丁建议。"""
    if not task_arg:
        print("--suggest-patch 需要指定 --task。")
        return 1

    return run_patch_assistant(
        model_config,
        "suggest_patch",
        project_arg,
        task_arg,
        files_arg,
        patch_output_arg,
        dry_run,
        patch_timeout,
        context_lite,
    )


def run_complete_todo(model_config, project_arg, task_arg, files_arg, patch_output_arg, dry_run, patch_timeout, context_lite):
    """根据选中文件中的 TODO/未实现标记生成补全建议。"""
    if not project_arg:
        print("--complete-todo 需要指定 --project。")
        return 1
    if not files_arg:
        print("--complete-todo MVP 需要指定 --files，暂不自动扫描整个项目。")
        return 1

    project_path = Path(project_arg).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"项目路径不存在或不是目录：{project_path}")
        return 1

    try:
        selected_files = [resolve_project_file(project_path, file_arg) for file_arg in files_arg]
        selected_files = list(dict.fromkeys(selected_files))
    except ValueError as error:
        print(f"文件选择无效：{error}")
        return 1

    markers = find_todo_markers(project_path, selected_files)
    if not markers:
        print("未在指定文件中找到 TODO、FIXME、pass 或 NotImplemented 标记。")
        return 1

    guidance = task_arg.strip() if task_arg else "Complete the detected TODO or incomplete implementation."
    user_request = "\n\n".join([
        "Complete TODO or incomplete implementation markers in the selected files.",
        f"User guidance: {guidance}",
        "Detected markers:",
        render_todo_markers(markers),
    ])

    return run_patch_assistant(
        model_config,
        "complete_todo",
        project_arg,
        user_request,
        [str(path.relative_to(project_path)) for path in selected_files],
        patch_output_arg,
        dry_run,
        patch_timeout,
        context_lite,
    )


def is_local_api_base(api_base):
    """判断 Ollama API 地址是否指向本机地址。"""
    parsed = urlparse(api_base)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def collect_continue_config_findings(config_format="yaml"):
    """读取 Continue.dev 配置，并检查是否存在云端 provider 线索。"""
    _, config_path, backup_path = resolve_continue_config_path(config_format)
    findings = {
        "config_path": str(config_path),
        "backup_path": str(backup_path),
        "config_exists": config_path.exists(),
        "config_valid_json": False,
        "providers": [],
        "cloud_provider_hints": [],
        "has_local_chat_model": False,
        "has_local_autocomplete": False,
        "has_local_embeddings": False,
        "codebase_index_enabled": False,
        "codebase_indexing_mode": "Not configured",
    }

    if not config_path.exists():
        return findings

    try:
        if config_format == "yaml":
            config_data = parse_yaml_text(config_path.read_text(encoding="utf-8"))
            findings["config_valid_json"] = True
        else:
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            findings["config_valid_json"] = True
    except Exception:
        findings["config_valid_json"] = False
        return findings

    if not isinstance(config_data, dict):
        return findings

    models = config_data.get("models", [])
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue
            provider = str(model.get("provider", "")).lower()
            title = str(model.get("title", ""))
            if provider:
                findings["providers"].append(provider)
            
            if config_format == "yaml":
                roles = model.get("roles", [])
                if isinstance(roles, list):
                    if "chat" in roles and provider == "ollama":
                        findings["has_local_chat_model"] = True
                    if "autocomplete" in roles and provider == "ollama":
                        findings["has_local_autocomplete"] = True
                    if "embed" in roles and provider == "ollama":
                        findings["has_local_embeddings"] = True
            else:
                if title == LOCAL_CHAT_TITLE and provider == "ollama":
                    findings["has_local_chat_model"] = True

    if config_format == "json":
        autocomplete = config_data.get("tabAutocompleteModel", {})
        if isinstance(autocomplete, dict):
            findings["has_local_autocomplete"] = autocomplete.get("provider") == "ollama"
            autocomplete_provider = str(autocomplete.get("provider", "")).lower()
            if autocomplete_provider:
                findings["providers"].append(autocomplete_provider)

        embeddings = config_data.get("embeddingsProvider", {})
        if isinstance(embeddings, dict):
            findings["has_local_embeddings"] = embeddings.get("provider") == "ollama"
            embeddings_provider = str(embeddings.get("provider", "")).lower()
            if embeddings_provider:
                findings["providers"].append(embeddings_provider)

    codebase_index = config_data.get("codebaseIndex", {})
    if isinstance(codebase_index, dict):
        findings["codebase_index_enabled"] = bool(codebase_index.get("enabled"))
        findings["codebase_indexing_mode"] = str(codebase_index.get("indexingMode", "Not configured"))

    providers = sorted(set(provider for provider in findings["providers"] if provider))
    findings["providers"] = providers
    findings["cloud_provider_hints"] = sorted(provider for provider in providers if provider in CLOUD_PROVIDER_HINTS)
    return findings


def collect_cloud_api_env_vars():
    """只检测常见云端 AI 环境变量是否存在，不读取或输出密钥值。"""
    return [name for name in CLOUD_API_ENV_VARS if os.environ.get(name)]


def build_environment_report(model_config, config_format="yaml"):
    """收集本机 AI 环境状态，生成离线报告数据。"""
    continue_dir, config_path, backup_path = resolve_continue_config_path(config_format)
    api_base = model_config["api_base"]
    ollama_cli_ok = is_ollama_cli_installed()
    ollama_service_ok = is_ollama_service_running(api_base)
    installed_models = get_installed_ollama_models(api_base) if ollama_service_ok else []
    required_models = get_required_models(model_config)
    continue_findings = collect_continue_config_findings(config_format)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "os": detect_os_name(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "continue_dir": str(continue_dir),
        "continue_config_path": str(config_path),
        "continue_backup_path": str(backup_path),
        "api_base": api_base,
        "api_base_is_local": is_local_api_base(api_base),
        "ollama_cli_installed": ollama_cli_ok,
        "ollama_service_running": ollama_service_ok,
        "selected_models": {
            "chat": model_config["chat_model"],
            "autocomplete": model_config["autocomplete_model"],
            "embedding": model_config["embedding_model"],
        },
        "required_models": required_models,
        "installed_models": installed_models,
        "missing_models": [model for model in required_models if model not in installed_models],
        "continue_findings": continue_findings,
        "cloud_api_env_vars_present": collect_cloud_api_env_vars(),
    }


def render_environment_report(report):
    """把离线环境检查结果渲染成 Markdown 报告。"""
    findings = report["continue_findings"]
    cloud_hints = findings["cloud_provider_hints"] or ["None detected in Continue config"]
    providers = findings["providers"] or ["None detected"]
    installed_models = report["installed_models"] or ["Not available or Ollama service not running"]
    missing_models = report["missing_models"] or ["None"]
    env_vars_present = report["cloud_api_env_vars_present"] or ["None detected"]

    lines = [
        "# Cyber-Code-Shield Offline Environment Report",
        "",
        "This report was generated locally by Cyber-Code-Shield.",
        "It is intended for developers, IT administrators, and security reviewers evaluating a local-first AI coding setup.",
        "",
        "## Summary",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- OS: `{report['os']}`",
        f"- Platform: `{report['platform']}`",
        f"- Python version: `{report['python_version']}`",
        f"- Ollama CLI installed: `{report['ollama_cli_installed']}`",
        f"- Ollama service running: `{report['ollama_service_running']}`",
        f"- Ollama API base: `{report['api_base']}`",
        f"- Ollama API base is local: `{report['api_base_is_local']}`",
        "",
        "## Continue.dev configuration",
        "",
        f"- Continue config path: `{report['continue_config_path']}`",
        f"- Main backup path: `{report['continue_backup_path']}`",
        f"- Config exists: `{findings['config_exists']}`",
        f"- Config valid JSON: `{findings['config_valid_json']}`",
        f"- Cyber-Code-Shield local chat model configured: `{findings['has_local_chat_model']}`",
        f"- Local Ollama autocomplete configured: `{findings['has_local_autocomplete']}`",
        f"- Local Ollama embeddings configured: `{findings['has_local_embeddings']}`",
        f"- Codebase index enabled: `{findings['codebase_index_enabled']}`",
        f"- Codebase indexing mode: `{findings['codebase_indexing_mode']}`",
        "",
        "## Providers detected in Continue config",
        "",
    ]

    for provider in providers:
        lines.append(f"- {provider}")

    lines.extend(["", "## Cloud provider hints", ""])
    for provider in cloud_hints:
        lines.append(f"- {provider}")

    lines.extend([
        "",
        "## Cloud API environment variables present",
        "",
        "Only variable names are reported; secret values are never read or printed.",
        "",
    ])
    for env_var in env_vars_present:
        lines.append(f"- {env_var}")

    lines.extend([
        "",
        "## Selected local model configuration",
        "",
        f"- Chat/refactor model: `{report['selected_models']['chat']}`",
        f"- Autocomplete model: `{report['selected_models']['autocomplete']}`",
        f"- Embedding model: `{report['selected_models']['embedding']}`",
        "",
        "## Required models",
        "",
    ])
    for model in report["required_models"]:
        lines.append(f"- {model}")

    lines.extend(["", "## Installed Ollama models", ""])
    for model in installed_models:
        lines.append(f"- {model}")

    lines.extend(["", "## Missing required models", ""])
    for model in missing_models:
        lines.append(f"- {model}")

    lines.extend([
        "",
        "## Local-first review notes",
        "",
        "- This report checks configuration signals only; it is not a formal security audit.",
        "- A local Ollama endpoint should normally use `localhost`, `127.0.0.1`, or an approved internal host.",
        "- Cloud provider hints and cloud API environment variables should be reviewed before strict-compliance use.",
        "- VS Code, extensions, operating system telemetry, and network controls should be reviewed separately by the organization.",
        "- Cyber-Code-Shield does not claim absolute zero leakage; it helps configure and document a local-first AI coding workflow.",
        "",
    ])
    return "\n".join(lines)


def get_default_report_filename(report_format):
    """根据报告格式选择默认文件名。"""
    if report_format == "json":
        return "CYBER_CODE_SHIELD_REPORT.json"
    return ENVIRONMENT_REPORT_FILENAME


def render_report_by_format(report, report_format):
    """按用户选择输出 Markdown 或 JSON 报告。"""
    if report_format == "json":
        return format_json(report)
    return render_environment_report(report)


def generate_environment_report(model_config, output_arg=None, dry_run=False, report_format="markdown", config_format="yaml"):
    """生成离线环境报告，可预览或写入 Markdown/JSON 文件。"""
    report = build_environment_report(model_config, config_format=config_format)
    rendered_report = render_report_by_format(report, report_format)
    default_filename = get_default_report_filename(report_format)
    output_path = Path(output_arg).expanduser().resolve() if output_arg else Path.cwd() / default_filename

    print(f"离线报告文件：{output_path}")
    print(f"离线报告格式：{report_format}")

    if dry_run:
        print("\nDry-run 模式：不会写入报告文件。")
        print("\n将生成的离线环境报告：")
        print(rendered_report)
        return 0

    output_path.write_text(rendered_report, encoding="utf-8")
    print(f"已生成离线环境报告：{output_path}")
    return 0


def build_parser():
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="Cyber-Code-Shield 本地 AI 编程环境配置工具"
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true", help="检查 Ollama、模型和 Continue 配置路径")
    actions.add_argument("--install", action="store_true", help="备份旧配置并覆盖安装本地 AI 配置")
    actions.add_argument("--merge", action="store_true", help="保留已有配置，并合并本地 AI 配置")
    actions.add_argument("--restore", action="store_true", help="从 config.yaml.bak 或 config.json.bak 恢复旧配置")
    actions.add_argument("--report", action="store_true", help="生成本地 AI 环境离线报告")
    actions.add_argument("--fix-error", action="store_true", help="根据本地错误日志和项目上下文生成可审查修复建议")
    actions.add_argument("--suggest-patch", action="store_true", help="根据用户描述和项目上下文生成可审查补丁建议")
    actions.add_argument("--complete-todo", action="store_true", help="根据指定文件中的 TODO/pass/NotImplemented 标记生成补全建议")

    parser.add_argument(
        "--config-format",
        choices=("yaml", "json"),
        default=DEFAULT_CONFIG_FORMAT,
        help="选择 Continue 配置格式，默认 yaml；json 为 legacy config.json",
    )
    parser.add_argument("--project", help="分析已有项目路径；也用于本地补丁助手命令")
    parser.add_argument("--error-log", help="错误日志文件路径，用于 --fix-error")
    parser.add_argument("--error-text", help="直接传入错误文本，用于 --fix-error")
    parser.add_argument("--task", help="补丁任务描述，用于 --suggest-patch；也可作为 --complete-todo 的额外指导")
    parser.add_argument("--files", nargs="+", help="限定提供给本地模型参考的项目文件")
    parser.add_argument("--patch-output", help="指定补丁建议 Markdown 输出路径")
    parser.add_argument(
        "--patch-timeout",
        type=int,
        default=PATCH_OLLAMA_TIMEOUT_SECONDS,
        help="补丁助手调用 Ollama 的超时时间，默认 180 秒；大模型首次加载可调大",
    )
    parser.add_argument("--context-lite", action="store_true", help="使用更短项目上下文，适合本地大模型快速验证")
    parser.add_argument("--report-output", help="指定离线报告输出路径，默认当前目录 CYBER_CODE_SHIELD_REPORT.md 或 .json")
    parser.add_argument(
        "--report-format",
        choices=("markdown", "json"),
        default="markdown",
        help="选择离线报告格式，默认 markdown",
    )
    parser.add_argument("--dry-run", action="store_true", help="预览将写入的配置、项目上下文或报告，不修改文件")
    parser.add_argument(
        "--profile",
        choices=sorted(MODEL_PROFILES.keys()),
        default=DEFAULT_PROFILE,
        help="选择预设模型档位，默认 balanced",
    )
    parser.add_argument("--chat-model", help="自定义 chat/refactor 模型，例如 qwen2.5-coder:14b")
    parser.add_argument("--autocomplete-model", help="自定义 Tab 补全模型，不填则使用 profile 默认值")
    parser.add_argument("--embedding-model", help="自定义 embedding 模型，例如 nomic-embed-text")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Ollama API 地址，默认 http://localhost:11434")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    model_config = resolve_model_config(args)

    if args.fix_error:
        return run_fix_error(
            model_config,
            args.project,
            args.error_log,
            args.error_text,
            args.files,
            args.patch_output,
            args.dry_run,
            args.patch_timeout,
            args.context_lite,
        )

    if args.suggest_patch:
        return run_suggest_patch(
            model_config,
            args.project,
            args.task,
            args.files,
            args.patch_output,
            args.dry_run,
            args.patch_timeout,
            args.context_lite,
        )

    if args.complete_todo:
        return run_complete_todo(
            model_config,
            args.project,
            args.task,
            args.files,
            args.patch_output,
            args.dry_run,
            args.patch_timeout,
            args.context_lite,
        )

    if args.project:
        return analyze_project(args.project, dry_run=args.dry_run)

    if args.report:
        return generate_environment_report(
            model_config,
            output_arg=args.report_output,
            dry_run=args.dry_run,
            report_format=args.report_format,
            config_format=args.config_format,
        )

    if args.check:
        run_check(model_config, config_format=args.config_format)
        return 0

    if args.restore:
        return restore_config(model_config, config_format=args.config_format)

    if args.merge:
        return merge_config(model_config, dry_run=args.dry_run, config_format=args.config_format)

    # 默认行为保持低门槛：不传动作时等同于 --install；--dry-run 单独使用时预览覆盖安装。
    return install_config(model_config, dry_run=args.dry_run, config_format=args.config_format)


if __name__ == "__main__":
    sys.exit(main())
