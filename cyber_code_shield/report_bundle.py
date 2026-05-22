import uuid
from datetime import datetime

from .constants import REPORT_BUNDLE_PREFIX, __version__
from .hashing import hash_text_sha256
from .patch_report import render_patch_markdown, render_patch_report_by_format
from .serialization import format_json

BUNDLE_ARTIFACTS = (
    "report.md",
    "report.json",
    "reviewed-files.json",
    "policy-warnings.json",
    "validation-warnings.json",
    "environment-summary.json",
)

CONTENT_TYPES = {
    "report.md": "text/markdown",
    "report.json": "application/json",
    "reviewed-files.json": "application/json",
    "policy-warnings.json": "application/json",
    "validation-warnings.json": "application/json",
    "environment-summary.json": "application/json",
}


def get_default_bundle_output_dir(project_path):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return project_path / f"{REPORT_BUNDLE_PREFIX}_{timestamp}"


def build_reviewed_files_artifact(patch_report):
    return {
        "schema_version": "cyber-code-shield.reviewed-files.v1",
        "report_id": patch_report["report_id"],
        "generated_at": patch_report["generated_at"],
        "reviewed_files": patch_report["audit"]["reviewed_files"],
    }


def build_policy_warnings_artifact(patch_report):
    return {
        "schema_version": "cyber-code-shield.policy-warnings.v1",
        "report_id": patch_report["report_id"],
        "generated_at": patch_report["generated_at"],
        "policy": patch_report["policy"],
        "policy_warnings_enabled": patch_report["policy_warnings_enabled"],
        "policy_warning_count": patch_report["audit"]["policy_warning_count"],
        "policy_warnings": patch_report["policy_warnings"],
    }


def build_validation_warnings_artifact(patch_report):
    return {
        "schema_version": "cyber-code-shield.validation-warnings.v1",
        "report_id": patch_report["report_id"],
        "generated_at": patch_report["generated_at"],
        "response_warning_count": patch_report["audit"]["response_warning_count"],
        "response_warnings": patch_report["response_warnings"],
    }


def build_manifest(bundle_id, patch_report, artifacts):
    return {
        "schema_version": "cyber-code-shield.report-bundle.v1",
        "bundle_id": bundle_id,
        "report_id": patch_report["report_id"],
        "generated_at": patch_report["generated_at"],
        "tool": {"name": "Cyber-Code-Shield", "version": __version__},
        "policy": patch_report["policy"],
        "model": patch_report["model"],
        "project": patch_report["project"],
        "source_files_modified_automatically": patch_report["audit"]["source_files_modified_automatically"],
        "reviewed_files": patch_report["audit"]["reviewed_files"],
        "artifacts": artifacts,
        "manifest_hash_excludes_self": True,
    }


def write_text_artifact(bundle_dir, relative_path, content):
    artifact_path = bundle_dir / relative_path
    artifact_path.write_text(content, encoding="utf-8")
    return {
        "path": relative_path,
        "sha256": hash_text_sha256(content),
        "content_type": CONTENT_TYPES[relative_path],
    }


def write_report_bundle(bundle_dir, patch_report, environment_summary):
    if bundle_dir.exists():
        raise FileExistsError(f"Report bundle directory already exists: {bundle_dir}")
    bundle_dir.mkdir(parents=True)

    artifact_entries = []
    artifact_entries.append(write_text_artifact(bundle_dir, "report.md", render_patch_markdown(patch_report)))
    artifact_entries.append(write_text_artifact(bundle_dir, "report.json", render_patch_report_by_format(patch_report, "json")))
    artifact_entries.append(write_text_artifact(bundle_dir, "reviewed-files.json", format_json(build_reviewed_files_artifact(patch_report))))
    artifact_entries.append(write_text_artifact(bundle_dir, "policy-warnings.json", format_json(build_policy_warnings_artifact(patch_report))))
    artifact_entries.append(write_text_artifact(bundle_dir, "validation-warnings.json", format_json(build_validation_warnings_artifact(patch_report))))
    artifact_entries.append(write_text_artifact(bundle_dir, "environment-summary.json", format_json(environment_summary)))

    manifest = build_manifest(f"ccs-bundle-{uuid.uuid4().hex}", patch_report, artifact_entries)
    (bundle_dir / "manifest.json").write_text(format_json(manifest), encoding="utf-8")
    return manifest
