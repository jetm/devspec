import click

from devspec.core.handoff import build_context
from devspec.core.resolve import resolve_project_data_dir


@click.command()
@click.argument("name")
@click.option("--max-tokens", type=int, default=None, help="Token budget for context dump.")
@click.option("--project", "project", default=None, help="Project name override.")
def context(name: str, max_tokens: int | None, project: str | None) -> None:
    """Token-budgeted context dump for a change."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    try:
        output = build_context(data_dir, name, max_tokens=max_tokens)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo(output)
