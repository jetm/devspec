"""devspec MCP tool handlers wrapping core module functions."""

from __future__ import annotations

import datetime
import re
from dataclasses import asdict
from pathlib import Path

import yaml

from devspec.core.analyzer import analyze_change
from devspec.core.archive import archive_change
from devspec.core.graph import ArtifactGraph
from devspec.core.handoff import build_context, read_handoff_bundle, write_handoff
from devspec.core.instructions import generate_instructions
from devspec.core.resolve import KEBAB_CASE_RE, resolve_project_data_dir
from devspec.core.schema import load_schema
from devspec.core.state import detect_completed, detect_task_progress
from devspec.core.validator import validate_change_delta_specs
from devspec.mcp.server import mcp


def _get_data_dir(project: str | None = None) -> Path:
    return resolve_project_data_dir(project)


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@mcp.tool()
def devspec_list(project: str | None = None) -> dict:
    """List all active devspec changes with their schema and status."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    changes_dir = data_dir / "changes"
    if not changes_dir.exists():
        return _error("no_changes_dir", "No changes/ directory. Run devspec init first.")

    schema = load_schema()
    graph = ArtifactGraph(schema)
    changes = []

    for entry in sorted(changes_dir.iterdir()):
        if not entry.is_dir() or entry.name == "archive":
            continue

        meta_path = entry / ".devspec.yaml"
        meta: dict = {}
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text()) or {}

        completed = detect_completed(schema, entry)
        is_complete = graph.is_complete(completed)

        if is_complete:
            done, total = detect_task_progress(entry, schema.apply.tracks)
            status = "planned" if (total > 0 and done < total) else "complete"
        else:
            status = "incomplete"

        changes.append(
            {
                "name": entry.name,
                "schema": meta.get("schema", "unknown"),
                "status": status,
                "created": meta.get("created", ""),
            }
        )

    return {"changes": changes}


@mcp.tool()
def devspec_new(name: str, project: str | None = None) -> dict:
    """Create a new devspec change directory."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    if not name or not name.strip():
        return _error("invalid_name", "Change name must not be empty.")

    if not KEBAB_CASE_RE.match(name):
        return _error("invalid_name", f"Invalid change name: {name!r}. Use kebab-case (e.g., 'add-feature').")

    changes_dir = data_dir / "changes"
    if not changes_dir.exists():
        return _error("no_changes_dir", "No changes/ directory. Run devspec init first.")

    change_dir = changes_dir / name
    if change_dir.exists():
        return _error("already_exists", f"Change already exists: {name}")

    try:
        schema = load_schema()
        change_dir.mkdir()
        meta = {"schema": schema.name, "created": datetime.date.today().isoformat()}
        (change_dir / ".devspec.yaml").write_text(yaml.dump(meta, default_flow_style=False))
        (change_dir / "specs").mkdir()
    except Exception as e:
        return _error("internal_error", f"Failed to create change: {e}")

    return {"created": name, "directory": str(change_dir), "schema": schema.name}


@mcp.tool()
def devspec_status(name: str, project: str | None = None) -> dict:
    """Show artifact completion status for a change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    try:
        schema = load_schema()
        graph = ArtifactGraph(schema)
        completed = detect_completed(schema, change_dir)
        statuses = graph.get_status(completed)
    except Exception as e:
        return _error("internal_error", str(e))

    return {
        "schemaName": schema.name,
        "isComplete": graph.is_complete(completed),
        "artifacts": [{"id": a.id, "status": statuses[a.id], "requiresIds": a.requires} for a in schema.artifacts],
        "applyRequires": schema.apply.requires,
    }


@mcp.tool()
def devspec_instructions(artifact_id: str, name: str, project: str | None = None) -> dict:
    """Get enriched instructions for creating an artifact."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    try:
        bundle = generate_instructions(data_dir, artifact_id, name)
    except ValueError as e:
        return _error("invalid_artifact", str(e))
    except Exception as e:
        return _error("internal_error", str(e))

    return {
        "artifactId": bundle.artifact_id,
        "template": bundle.template,
        "instruction": bundle.instruction,
        "outputPath": bundle.output_path,
        "dependencies": bundle.dependencies,
        "context": bundle.context,
        "rules": bundle.rules,
    }


@mcp.tool()
def devspec_context(name: str, max_tokens: int | None = None, project: str | None = None) -> dict:
    """Build a token-budgeted context dump for a change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    try:
        content = build_context(data_dir, name, max_tokens=max_tokens)
    except FileNotFoundError as e:
        return _error("not_found", str(e))
    except Exception as e:
        return _error("internal_error", str(e))

    return {"content": content}


@mcp.tool()
def devspec_validate(name: str, project: str | None = None) -> dict:
    """Validate delta specs for a change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    try:
        report = validate_change_delta_specs(change_dir)
    except Exception as e:
        return _error("internal_error", str(e))

    return {
        "valid": report.valid,
        "summary": report.summary,
        "issues": [{"level": i.level, "path": i.path, "message": i.message} for i in report.issues],
    }


@mcp.tool()
def devspec_analyze(name: str, project: str | None = None) -> dict:
    """Analyze cross-artifact consistency for a change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    try:
        report = analyze_change(change_dir)
    except Exception as e:
        return _error("internal_error", str(e))

    return asdict(report)


@mcp.tool()
def devspec_handoff_read(name: str, project: str | None = None) -> dict:
    """Read handoff and all artifacts for a change as a single bundle."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    try:
        bundle = read_handoff_bundle(change_dir)
    except Exception as e:
        return _error("internal_error", str(e))

    return {"content": bundle}


@mcp.tool()
def devspec_handoff_write(name: str, content: str, project: str | None = None) -> dict:
    """Write handoff content for a change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    try:
        path = write_handoff(change_dir, content)
    except Exception as e:
        return _error("internal_error", str(e))

    return {"written": str(path.relative_to(data_dir))}


@mcp.tool()
def devspec_archive(
    name: str,
    skip_specs: bool = False,
    force: bool = False,
    project: str | None = None,
) -> dict:
    """Archive a completed change."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    try:
        result = archive_change(data_dir, name, skip_specs=skip_specs, force=force)
    except FileNotFoundError as e:
        return _error("not_found", str(e))
    except ValueError as e:
        return _error("incomplete", str(e))
    except Exception as e:
        return _error("internal_error", str(e))

    return {
        "archived": result.change_name,
        "archivePath": str(result.archive_path),
        "specsSync": result.specs_synced,
    }


@mcp.tool()
def devspec_task_mark(name: str, task_index: int, done: bool = True, project: str | None = None) -> dict:
    """Mark a task as complete or incomplete in tasks.md by 1-based index.

    task_index: 1-based index of the task checkbox to toggle.
    done: True to mark complete ([x]), False to mark incomplete ([ ]).
    """
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    schema = load_schema()
    tasks_file = change_dir / schema.apply.tracks
    if not tasks_file.exists():
        return _error("not_found", f"Tasks file not found: {schema.apply.tracks}")

    content = tasks_file.read_text(encoding="utf-8")
    checkbox_re = re.compile(r"^(- \[)[ x](\] )", re.MULTILINE)
    matches = list(checkbox_re.finditer(content))

    if task_index < 1 or task_index > len(matches):
        return _error("out_of_range", f"Task index {task_index} out of range (1-{len(matches)})")

    match = matches[task_index - 1]
    mark = "x" if done else " "
    new_content = content[: match.start()] + match.group(1) + mark + match.group(2) + content[match.end() :]
    tasks_file.write_text(new_content, encoding="utf-8")

    return {"taskIndex": task_index, "done": done, "tasksFile": str(tasks_file.relative_to(data_dir))}
