import json

import click

from devspec.core.graph import ArtifactGraph
from devspec.core.resolve import resolve_project_data_dir
from devspec.core.schema import load_schema
from devspec.core.state import detect_completed


@click.command()
@click.argument("name", required=False, default=None)
@click.option("--change", "change_name", default=None, help="Change name (alternative to positional arg).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--project", "project", default=None, help="Project name override.")
def status(name: str | None, change_name: str | None, as_json: bool, project: str | None) -> None:
    """Show artifact completion status for a change."""
    change_name = name or change_name
    if not change_name:
        click.echo("Usage: devspec status <name> [--json]")
        raise SystemExit(1)
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    change_dir = data_dir / "changes" / change_name

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
