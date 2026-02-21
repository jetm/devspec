import click

from devspec.core.change import create_change
from devspec.core.resolve import resolve_project_data_dir


@click.command()
@click.argument("name")
@click.option("--project", "project", default=None, help="Project name override.")
def new(name: str, project: str | None) -> None:
    """Create a new change directory."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    try:
        change_dir, schema_name = create_change(data_dir / "changes", name)
    except (FileNotFoundError, ValueError) as e:
        click.echo(str(e))
        raise SystemExit(1)

    click.echo(f"Created change: {name}")
    click.echo(f"  Directory: changes/{name}/")
    click.echo(f"  Schema: {schema_name}")
    click.echo("  Next: create proposal.md")
