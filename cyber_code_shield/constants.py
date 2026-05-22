__version__ = "0.6.0"
DEFAULT_API_BASE = "http://localhost:11434"
DEFAULT_INFERENCE_PROVIDER = "ollama"
INFERENCE_PROVIDERS = ("ollama", "openai-compatible")
MODEL_TIERS = ("light", "deep", "custom")
DEFAULT_MODEL_TIER = "custom"
PATCH_REPORT_FORMATS = ("markdown", "json")
POLICY_WARNING_SEVERITIES = ("info", "review", "high")
POLICY_PROFILE_NAMES = ("basic", "enterprise-strict", "china-privacy", "supply-chain")
DEFAULT_POLICY_PROFILE = "basic"
REPORT_BUNDLE_PREFIX = "CYBER_CODE_SHIELD_BUNDLE"
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
