from pathlib import Path

import click

from devspec.core.archive import archive_change


@click.command()
@click.argument("name")
@click.option("--skip-specs", is_flag=True, help="Skip spec sync before archiving.")
@click.option("--yes", "force", is_flag=True, help="Archive even if artifacts are incomplete.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def archive(name: str, skip_specs: bool, force: bool, project_path: str) -> None:
    """Archive a completed change."""
    root = Path(project_path).resolve()

    try:
        result = archive_change(root, name, skip_specs=skip_specs, force=force)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo(f"Archived: {result.change_name}")
    click.echo(f"  Location: {result.archive_path.relative_to(root)}")
    click.echo(f"  Specs synced: {'yes' if result.specs_synced else 'no'}")
