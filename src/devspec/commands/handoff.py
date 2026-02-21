import sys
from pathlib import Path

import click

from devspec.core.handoff import read_handoff_bundle, write_handoff
from devspec.core.resolve import resolve_project_data_dir


@click.group()
def handoff() -> None:
    """Context bridge for skill transitions."""


@handoff.command()
@click.argument("name")
@click.option("--file", "input_file", type=click.Path(exists=True), help="Read from file instead of stdin.")
@click.option("--project", "project", default=None, help="Project name override.")
def write(name: str, input_file: str | None, project: str | None) -> None:
    """Write handoff content for a change."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    change_dir = data_dir / "changes" / name

    if not change_dir.exists():
        click.echo(f"Change not found: {name}")
        raise SystemExit(1)

    if input_file:
        content = Path(input_file).read_text()
    else:
        content = sys.stdin.read()

    path = write_handoff(change_dir, content)
    click.echo(f"Handoff written: {path.relative_to(data_dir)}")


@handoff.command()
@click.argument("name")
@click.option("--project", "project", default=None, help="Project name override.")
def read(name: str, project: str | None) -> None:
    """Read handoff + all artifacts for a change."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    change_dir = data_dir / "changes" / name

    if not change_dir.exists():
        click.echo(f"Change not found: {name}")
        raise SystemExit(1)

    bundle = read_handoff_bundle(change_dir)
    if bundle:
        click.echo(bundle)
    else:
        click.echo("No handoff or artifacts found.")
