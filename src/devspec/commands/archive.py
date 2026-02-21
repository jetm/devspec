import click

from devspec.core.archive import archive_change
from devspec.core.resolve import resolve_project_data_dir


@click.command()
@click.argument("name")
@click.option("--skip-specs", is_flag=True, help="Skip spec sync before archiving.")
@click.option("--yes", "force", is_flag=True, help="Archive even if artifacts are incomplete.")
@click.option("--project", "project", default=None, help="Project name override.")
def archive(name: str, skip_specs: bool, force: bool, project: str | None) -> None:
    """Archive a completed change."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        click.echo(str(e))
        raise SystemExit(1)

    try:
        result = archive_change(data_dir, name, skip_specs=skip_specs, force=force)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo(f"Archived: {result.change_name}")
    click.echo(f"  Location: {result.archive_path.relative_to(data_dir)}")
    click.echo(f"  Specs synced: {'yes' if result.specs_synced else 'no'}")
