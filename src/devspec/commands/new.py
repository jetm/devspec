import datetime
from pathlib import Path

import click
import yaml

from devspec.core.schema import load_schema


@click.command()
@click.argument("name")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def new(name: str, project_path: str) -> None:
    """Create a new change directory."""
    root = Path(project_path).resolve()
    changes_dir = root / "openspec" / "changes"

    if not changes_dir.exists():
        click.echo("No openspec/changes/ directory. Run `devspec init` first.")
        raise SystemExit(1)

    change_dir = changes_dir / name
    if change_dir.exists():
        click.echo(f"Change already exists: {name}")
        raise SystemExit(1)

    schema = load_schema()
    change_dir.mkdir()

    # Create .openspec.yaml metadata
    meta = {"schema": schema.name, "created": datetime.date.today().isoformat()}
    (change_dir / ".openspec.yaml").write_text(yaml.dump(meta, default_flow_style=False))

    # Create specs subdirectory
    (change_dir / "specs").mkdir()

    click.echo(f"Created change: {name}")
    click.echo(f"  Directory: openspec/changes/{name}/")
    click.echo(f"  Schema: {schema.name}")
    click.echo("  Next: create proposal.md")
