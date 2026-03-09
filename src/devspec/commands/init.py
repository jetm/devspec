import re
from pathlib import Path

import click

from devspec.core.resolve import KEBAB_CASE_RE, MARKER_FILE, get_data_root


def _sanitize_basename(name: str) -> str:
    """Convert a directory basename to a kebab-case project name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@click.command()
@click.option("--name", "project_name", default=None, help="Project name (defaults to directory basename).")
def init(project_name: str | None) -> None:
    """Initialize a devspec project with global data directory and marker file."""
    cwd = Path.cwd()

    # Check for existing marker
    marker = cwd / MARKER_FILE
    if marker.exists():
        click.echo(f".devspec marker already exists at {marker}")
        raise SystemExit(1)

    # Determine project name
    if project_name is None:
        project_name = _sanitize_basename(cwd.name)

    if not project_name or not KEBAB_CASE_RE.match(project_name):
        click.echo(f"Invalid project name: {project_name!r}. Use kebab-case (e.g., 'my-project').")
        raise SystemExit(1)

    # Create global data directory
    data_dir = get_data_root() / project_name
    if data_dir.exists():
        click.echo(f"Project data directory already exists: {data_dir}")
        raise SystemExit(1)

    data_dir.mkdir(parents=True)
    (data_dir / "specs").mkdir()
    (data_dir / "changes").mkdir()
    (data_dir / "changes" / "archive").mkdir()

    # Create marker file in cwd
    marker.write_text(project_name + "\n")

    click.echo(f"Initialized project: {project_name}")
    click.echo(f"  Data: {data_dir}")
    click.echo(f"  Marker: {marker}")
    click.echo()
    click.echo("Next: run /devspec-memory to populate Claude Code auto memory for this project.")
