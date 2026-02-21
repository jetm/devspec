"""devspec MCP resource handlers for data store access."""

from __future__ import annotations

import importlib.resources

from devspec.core.resolve import resolve_project_data_dir
from devspec.mcp.server import mcp


def _data_dir(project: str | None = None):
    return resolve_project_data_dir(project)


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
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return f"Error: Change not found: {name}"

    artifact_path = change_dir / artifact
    if not artifact_path.exists():
        return f"Error: Artifact not found: {artifact}"

    return artifact_path.read_text(encoding="utf-8")


@mcp.resource("devspec://changes/{name}/specs/{capability}")
def get_delta_spec(name: str, capability: str) -> str:
    """Return the content of a capability's delta spec file."""
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
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    spec_file = data_dir / "specs" / capability / "spec.md"
    if not spec_file.exists():
        return f"Error: Spec not found: specs/{capability}/spec.md"

    return spec_file.read_text(encoding="utf-8")


@mcp.resource("devspec://learnings/{category}")
def get_learnings(category: str) -> str:
    """Return learning entries for a category."""
    try:
        data_dir = _data_dir()
    except FileNotFoundError as e:
        return f"Error: {e}"

    category_dir = data_dir / "learnings" / category
    if not category_dir.exists():
        return f"Error: Learning category not found: {category}"

    parts = []
    for learning_file in sorted(category_dir.iterdir()):
        if learning_file.suffix == ".md":
            parts.append(f"# {learning_file.name}\n\n{learning_file.read_text(encoding='utf-8')}")

    return "\n\n---\n\n".join(parts) if parts else f"No learning files found in category: {category}"


@mcp.resource("devspec://schema")
def get_schema() -> str:
    """Return the current devspec schema definition."""
    bundled_data_dir = importlib.resources.files("devspec.data")
    return (bundled_data_dir / "schema.yaml").read_text(encoding="utf-8")
