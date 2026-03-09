"""devspec MCP resource handlers for data store access.

Note: Resource handlers return plain strings (including error messages as
"Error: ..." strings) per MCP resource conventions. This differs from tool
handlers which return structured {"error": {...}} dicts.
"""

from __future__ import annotations

import importlib.resources
import re

from devspec.core.resolve import KEBAB_CASE_RE, resolve_project_data_dir
from devspec.mcp.server import mcp

_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


_cached_data_dir = None


def _data_dir(project: str | None = None):
    """Resolve project data dir with caching for the MCP server process."""
    global _cached_data_dir
    if project is not None:
        return resolve_project_data_dir(project)
    if _cached_data_dir is None:
        _cached_data_dir = resolve_project_data_dir(None)
    return _cached_data_dir


def _validate_path_param(value: str, param_name: str) -> str | None:
    """Validate a URI template parameter is safe for path construction.

    Returns error string if invalid, None if valid.
    """
    if not value or "/" in value or "\\" in value or ".." in value:
        return f"Error: Invalid {param_name}: {value!r}"
    return None


@mcp.resource("devspec://changes/")
def list_changes() -> str:
    """List all active change names."""
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    changes_dir = data_dir / "changes"
    if not changes_dir.exists():
        return "No changes directory found."

    names = [entry.name for entry in sorted(changes_dir.iterdir()) if entry.is_dir() and entry.name != "archive"]
    return "\n".join(names) if names else "No active changes."


@mcp.resource("devspec://changes/{name}/{artifact}")
def get_artifact(name: str, artifact: str) -> str:
    """Return the content of a change artifact file (e.g. proposal.md, design.md, tasks.md)."""
    if not KEBAB_CASE_RE.match(name):
        return f"Error: Invalid change name: {name!r}"
    if err := _validate_path_param(artifact, "artifact"):
        return err
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return f"Error: Change not found: {name}"

    artifact_path = (change_dir / artifact).resolve()
    if not artifact_path.is_relative_to(change_dir.resolve()):
        return f"Error: Invalid artifact path: {artifact}"

    # Fallback: try adding .md extension if path doesn't exist
    if not artifact_path.exists() and not artifact.endswith(".md"):
        md_path = artifact_path.with_suffix(".md")
        if md_path.exists() and md_path.is_file():
            artifact_path = md_path

    # Directory handling: concatenate all .md files
    if artifact_path.is_dir():
        md_files = sorted(artifact_path.rglob("*.md"))
        if not md_files:
            return f"Error: No markdown files found in: {artifact}"
        parts = []
        for f in md_files:
            rel = f.relative_to(artifact_path)
            parts.append(f"# {rel}\n\n{f.read_text(encoding='utf-8')}")
        return "\n\n---\n\n".join(parts)

    if not artifact_path.exists():
        return f"Error: Artifact not found: {artifact}"
    if not artifact_path.is_file():
        return f"Error: Artifact not found: {artifact}"

    return artifact_path.read_text(encoding="utf-8")


@mcp.resource("devspec://changes/{name}/specs/{capability}")
def get_delta_spec(name: str, capability: str) -> str:
    """Return the content of a capability's delta spec file."""
    if not KEBAB_CASE_RE.match(name):
        return f"Error: Invalid change name: {name!r}"
    if err := _validate_path_param(capability, "capability"):
        return err
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    spec_file = data_dir / "changes" / name / "specs" / capability / "spec.md"
    if not spec_file.exists():
        return f"Error: Spec not found: changes/{name}/specs/{capability}/spec.md"

    return spec_file.read_text(encoding="utf-8")


@mcp.resource("devspec://specs/{capability}")
def get_main_spec(capability: str) -> str:
    """Return the content of a main spec file."""
    if err := _validate_path_param(capability, "capability"):
        return err
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    spec_file = data_dir / "specs" / capability / "spec.md"
    if not spec_file.exists():
        return f"Error: Spec not found: specs/{capability}/spec.md"

    return spec_file.read_text(encoding="utf-8")


@mcp.resource("devspec://schema")
def get_schema() -> str:
    """Return the current devspec schema definition."""
    bundled_data_dir = importlib.resources.files("devspec.data")
    return (bundled_data_dir / "schema.yaml").read_text(encoding="utf-8")
