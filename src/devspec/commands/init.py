from pathlib import Path

import click
import yaml


@click.command()
@click.option("--path", "project_path", default=".", help="Project root directory.")
def init(project_path: str) -> None:
    """Scaffold an openspec/ directory with config.yaml."""
    root = Path(project_path).resolve()
    openspec_dir = root / "openspec"

    if openspec_dir.exists():
        click.echo(f"openspec/ already exists at {openspec_dir}")
        raise SystemExit(1)

    openspec_dir.mkdir()
    (openspec_dir / "specs").mkdir()
    (openspec_dir / "changes").mkdir()
    (openspec_dir / "changes" / "archive").mkdir()

    config = {"schema": "spec-driven-custom"}
    (openspec_dir / "config.yaml").write_text(yaml.dump(config, default_flow_style=False))

    click.echo(f"Initialized openspec/ at {openspec_dir}")
