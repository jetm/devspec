import json
from pathlib import Path

import click

from devspec.core.graph import ArtifactGraph
from devspec.core.schema import load_schema
from devspec.core.state import detect_completed


@click.command()
@click.option("--change", "change_name", required=True, help="Change name.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def status(change_name: str, as_json: bool, project_path: str) -> None:
    """Show artifact completion status for a change."""
    root = Path(project_path).resolve()
    change_dir = root / "openspec" / "changes" / change_name

    if not change_dir.exists():
        click.echo(f"Change not found: {change_name}")
        raise SystemExit(1)

    schema = load_schema()
    graph = ArtifactGraph(schema)
    completed = detect_completed(schema, change_dir)
    statuses = graph.get_status(completed)

    if as_json:
        data = {
            "schemaName": schema.name,
            "isComplete": graph.is_complete(completed),
            "artifacts": [{"id": a.id, "status": statuses[a.id], "requiresIds": a.requires} for a in schema.artifacts],
            "applyRequires": schema.apply.requires,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Change: {change_name}")
        click.echo(f"Schema: {schema.name}")
        click.echo(f"Complete: {'yes' if graph.is_complete(completed) else 'no'}")
        click.echo()
        for a in schema.artifacts:
            s = statuses[a.id]
            icon = {"done": "+", "ready": "~", "blocked": "x"}[s]
            click.echo(f"  [{icon}] {a.id}: {s}")
