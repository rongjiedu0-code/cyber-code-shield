from .constants import DEFAULT_POLICY_PROFILE, POLICY_PROFILE_NAMES

POLICY_PROFILE_RULES_VERSION = "cyber-code-shield.policy-profiles.v1"
POLICY_PROFILE_DISCLAIMER = "Policy profiles are review and evidence helpers, not formal compliance certifications."

POLICY_PROFILE_DEFINITIONS = {
    "basic": {
        "profile": "basic",
        "label": "Basic",
        "description": "Default policy warning behavior for local AI coding review.",
    },
    "enterprise-strict": {
        "profile": "enterprise-strict",
        "label": "Enterprise Strict",
        "description": "Stricter review profile for enterprise-controlled code changes.",
    },
    "china-privacy": {
        "profile": "china-privacy",
        "label": "China Privacy Review",
        "description": "Review profile focused on personal information, logging, cloud-provider, and data-flow signals.",
    },
    "supply-chain": {
        "profile": "supply-chain",
        "label": "Software Supply Chain Review",
        "description": "Review profile focused on dependency, build, package script, and CI/CD changes.",
    },
}


def normalize_policy_profile(policy_profile):
    if policy_profile in POLICY_PROFILE_NAMES:
        return policy_profile
    return DEFAULT_POLICY_PROFILE


def get_policy_profile_definition(policy_profile):
    profile_name = normalize_policy_profile(policy_profile)
    definition = dict(POLICY_PROFILE_DEFINITIONS[profile_name])
    definition["rules_version"] = POLICY_PROFILE_RULES_VERSION
    definition["disclaimer"] = POLICY_PROFILE_DISCLAIMER
    return definition


def escalate_warning(warning, severity="high"):
    updated = dict(warning)
    updated["severity"] = severity
    return updated


def warning_codes(warnings):
    return {warning["code"] for warning in warnings}


def add_warning_once(warnings, warning):
    if warning["code"] not in warning_codes(warnings):
        warnings.append(warning)


def apply_policy_profile(warnings, normalized_paths, added_text, make_policy_warning, policy_profile=DEFAULT_POLICY_PROFILE):
    profile_name = normalize_policy_profile(policy_profile)
    if profile_name == "basic":
        return warnings

    profiled_warnings = [dict(warning) for warning in warnings]

    if profile_name == "enterprise-strict":
        escalation_codes = {"DEPENDENCY_CHANGE", "CI_CD_CHANGE", "SENSITIVE_AREA"}
        profiled_warnings = [
            escalate_warning(warning) if warning["code"] in escalation_codes else warning
            for warning in profiled_warnings
        ]
        if profiled_warnings:
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "ENTERPRISE_REVIEW_REQUIRED",
                    "review",
                    "Enterprise strict profile selected; route this AI-assisted change through the configured human review process.",
                ),
            )
        return profiled_warnings

    if profile_name == "china-privacy":
        privacy_patterns = (
            "phone", "email", "id_card", "identity", "address", "real_name", "personal", "pii",
            "user_data", "userdata", "手机号", "身份证", "个人信息", "姓名", "地址",
        )
        logging_patterns = (
            "logger.", "logging.", "console.log", "print(", "telemetry", "analytics", "track(", "sentry",
        )
        cloud_patterns = (
            "openai", "anthropic", "azure", "google", "aws", "s3", "gemini", "mistral",
            "cohere", "openrouter",
        )
        if any(pattern in added_text for pattern in privacy_patterns):
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "PRIVACY_DATA_FLOW",
                    "high",
                    "Patch appears to touch personal-information or user-data handling; review privacy and data-flow impact.",
                ),
            )
        if any(pattern in added_text for pattern in logging_patterns):
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "LOGGING_OR_TELEMETRY",
                    "review",
                    "Patch appears to add logging, telemetry, analytics, or tracking behavior; review sensitive-data exposure.",
                ),
            )
        if any(pattern in added_text for pattern in cloud_patterns) or "NETWORK_CALL" in warning_codes(profiled_warnings):
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "CLOUD_PROVIDER_OR_EGRESS",
                    "high",
                    "Patch appears to reference cloud providers or outbound data paths; review local-only and data-egress requirements.",
                ),
            )
        return profiled_warnings

    if profile_name == "supply-chain":
        escalation_codes = {"DEPENDENCY_CHANGE", "CI_CD_CHANGE"}
        profiled_warnings = [
            escalate_warning(warning) if warning["code"] in escalation_codes else warning
            for warning in profiled_warnings
        ]
        package_script_patterns = ('"scripts"', '"postinstall"', '"preinstall"', '"prepare"', "postinstall", "preinstall")
        if any(path.endswith("package.json") for path in normalized_paths) and any(pattern in added_text for pattern in package_script_patterns):
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "PACKAGE_SCRIPT_CHANGE",
                    "high",
                    "Patch appears to add or modify package scripts; review install/build-time execution risk.",
                    ", ".join(normalized_paths),
                ),
            )
        build_chain_keywords = (
            "dockerfile", "docker-compose", ".github/workflows", ".gitlab-ci.yml", "jenkinsfile",
            "azure-pipelines.yml", "makefile", "build.gradle", "pom.xml",
        )
        if any(any(keyword in path.lower() for keyword in build_chain_keywords) for path in normalized_paths):
            add_warning_once(
                profiled_warnings,
                make_policy_warning(
                    "BUILD_CHAIN_CHANGE",
                    "high",
                    "Patch touches build, container, or pipeline configuration; review software supply-chain impact.",
                    ", ".join(normalized_paths),
                ),
            )
        return profiled_warnings

    return profiled_warnings
