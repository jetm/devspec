import shutil
from pathlib import Path

import click

from devspec.core.resolve import get_data_root


@click.command()
@click.option("--repo", "repo_path", default=None, type=click.Path(exists=True), help="Repository path to clean up.")
def migrate(repo_path: str | None) -> None:
    """Migrate data from openspec/ layout to devspec/ global store."""
    data_root = get_data_root()
    old_root = data_root.parent / "openspec"

    if not old_root.exists():
        if repo_path:
            click.echo(f"Nothing to migrate: {old_root} does not exist.")
            raise SystemExit(1)
        click.echo(f"Nothing to migrate: {old_root} does not exist.")
        return

    if data_root.exists():
        click.echo(f"Target already exists: {data_root}")
        click.echo("Cannot migrate when target directory already exists.")
        raise SystemExit(1)

    # Rename global directory
    old_root.rename(data_root)
    click.echo(f"Renamed: {old_root} -> {data_root}")

    # Rename .openspec.yaml -> .devspec.yaml in all change directories
    renamed_count = 0
    for project_dir in data_root.iterdir():
        if not project_dir.is_dir():
            continue
        changes_dir = project_dir / "changes"
        if not changes_dir.is_dir():
            continue
        for change_dir in changes_dir.iterdir():
            if not change_dir.is_dir():
                continue
            old_meta = change_dir / ".openspec.yaml"
            if old_meta.exists():
                new_meta = change_dir / ".devspec.yaml"
                old_meta.rename(new_meta)
                renamed_count += 1
        # Also check archive subdirectory
        archive_dir = changes_dir / "archive"
        if archive_dir.is_dir():
            for archived in archive_dir.iterdir():
                if not archived.is_dir():
                    continue
                old_meta = archived / ".openspec.yaml"
                if old_meta.exists():
                    new_meta = archived / ".devspec.yaml"
                    old_meta.rename(new_meta)
                    renamed_count += 1

    if renamed_count:
        click.echo(f"Renamed {renamed_count} .openspec.yaml -> .devspec.yaml")

    # Optionally clean up in-repo openspec/ directory
    if repo_path:
        repo = Path(repo_path).resolve()
        openspec_dir = repo / "openspec"
        if openspec_dir.is_dir():
            shutil.rmtree(openspec_dir)
            click.echo(f"Removed: {openspec_dir}")
        else:
            click.echo(f"No openspec/ directory found at {repo}")

    click.echo("Migration complete.")
