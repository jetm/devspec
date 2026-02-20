import sys
from pathlib import Path

import click

from devspec.core.handoff import read_handoff_bundle, write_handoff


@click.group()
def handoff() -> None:
    """Context bridge for skill transitions."""


@handoff.command()
@click.argument("name")
@click.option("--file", "input_file", type=click.Path(exists=True), help="Read from file instead of stdin.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def write(name: str, input_file: str | None, project_path: str) -> None:
    """Write handoff content for a change."""
    root = Path(project_path).resolve()
    change_dir = root / "openspec" / "changes" / name

    if not change_dir.exists():
        click.echo(f"Change not found: {name}")
        raise SystemExit(1)

    if input_file:
        content = Path(input_file).read_text()
    else:
        content = sys.stdin.read()

    path = write_handoff(change_dir, content)
    click.echo(f"Handoff written: {path.relative_to(root)}")


@handoff.command()
@click.argument("name")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def read(name: str, project_path: str) -> None:
    """Read handoff + all artifacts for a change."""
    root = Path(project_path).resolve()
    change_dir = root / "openspec" / "changes" / name

    if not change_dir.exists():
        click.echo(f"Change not found: {name}")
        raise SystemExit(1)

    bundle = read_handoff_bundle(change_dir)
    if bundle:
        click.echo(bundle)
    else:
        click.echo("No handoff or artifacts found.")
