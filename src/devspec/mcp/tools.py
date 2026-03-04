"""devspec MCP tool handlers wrapping core module functions."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from devspec.core.analyzer import analyze_change
from devspec.core.archive import archive_change
from devspec.core.change import create_change
from devspec.core.graph import ArtifactGraph
from devspec.core.handoff import build_context, read_handoff_bundle, write_handoff
from devspec.core.instructions import generate_instructions
from devspec.core.preflight import run_preflight
from devspec.core.resolve import KEBAB_CASE_RE, resolve_project_data_dir
from devspec.core.schema import load_schema
from devspec.core.state import detect_completed, detect_task_progress, mark_task
from devspec.core.validator import validate_change_delta_specs
from devspec.mcp.server import mcp

_cached_data_dir: Path | None = None


def _get_data_dir(project: str | None = None) -> Path:
    """Resolve project data dir with caching for the MCP server process.

    In a long-lived stdio MCP server, cwd never changes, so the default
    project resolution is stable and safe to cache.
    """
    global _cached_data_dir
    if project is not None:
        return resolve_project_data_dir(project)
    if _cached_data_dir is None:
        _cached_data_dir = resolve_project_data_dir(None)
    return _cached_data_dir


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _validate_name(name: str) -> dict | None:
    """Validate change name is kebab-case. Returns error dict if invalid, None if valid."""
    if not name or not KEBAB_CASE_RE.match(name):
        return _error("invalid_name", f"Invalid change name: {name!r}. Use kebab-case (e.g., 'add-feature').")
    return None


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

    try:
        change_dir, schema_name = create_change(data_dir / "changes", name)
    except FileNotFoundError as e:
        return _error("no_changes_dir", str(e))
    except ValueError as e:
        code = "already_exists" if "already exists" in str(e) else "invalid_name"
        return _error(code, str(e))
    except Exception as e:
        return _error("internal_error", f"Failed to create change: {e}")

    return {"created": name, "directory": str(change_dir), "schema": schema_name}


@mcp.tool()
def devspec_status(name: str, project: str | None = None) -> dict:
    """Show artifact completion status for a change."""
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    }


@mcp.tool()
def devspec_context(name: str, max_tokens: int | None = None, project: str | None = None) -> dict:
    """Build a token-budgeted context dump for a change."""
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
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
    if err := _validate_name(name):
        return err
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    change_dir = data_dir / "changes" / name
    if not change_dir.exists():
        return _error("not_found", f"Change not found: {name}")

    schema = load_schema()
    try:
        tasks_file = mark_task(change_dir, schema.apply.tracks, task_index, done)
    except FileNotFoundError as e:
        return _error("not_found", str(e))
    except IndexError as e:
        return _error("out_of_range", str(e))

    return {"taskIndex": task_index, "done": done, "tasksFile": str(tasks_file.relative_to(data_dir))}


@mcp.tool()
def devspec_preflight(project: str | None = None) -> dict:
    """Run pre-flight environment checks."""
    try:
        data_dir = _get_data_dir(project)
    except FileNotFoundError as e:
        return _error("project_not_found", str(e))

    report = run_preflight(data_dir)
    return {
        "passed": report.passed,
        "summary": report.summary,
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in report.checks],
    }
