import json
from pathlib import Path

import click
import yaml

from devspec.core.graph import ArtifactGraph
from devspec.core.schema import load_schema
from devspec.core.state import detect_completed, detect_task_progress


@click.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def list_changes(as_json: bool, project_path: str) -> None:
    """List active changes."""
    root = Path(project_path).resolve()
    changes_dir = root / "openspec" / "changes"

    if not changes_dir.exists():
        click.echo("No openspec/changes/ directory. Run `devspec init` first.")
        raise SystemExit(1)

    schema = load_schema()
    graph = ArtifactGraph(schema)
    changes = []

    for entry in sorted(changes_dir.iterdir()):
        if not entry.is_dir() or entry.name == "archive":
            continue

        meta_path = entry / ".openspec.yaml"
        meta = {}
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text()) or {}

        completed = detect_completed(schema, entry)
        is_complete = graph.is_complete(completed)

        if is_complete:
            done, total = detect_task_progress(entry, schema.apply.tracks)
            if total > 0 and done < total:
                status = "planned"
            else:
                status = "complete"
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

    if as_json:
        click.echo(json.dumps(changes, indent=2, default=str))
    elif not changes:
        click.echo("No active changes.")
    else:
        for c in changes:
            icon = {"complete": "+", "planned": "~", "incomplete": "-"}[c["status"]]
            click.echo(f"  [{icon}] {c['name']} ({c['schema']}) — {c['status']}")
