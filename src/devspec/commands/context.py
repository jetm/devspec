from pathlib import Path

import click

from devspec.core.handoff import build_context


@click.command()
@click.argument("name")
@click.option("--max-tokens", type=int, default=None, help="Token budget for context dump.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def context(name: str, max_tokens: int | None, project_path: str) -> None:
    """Token-budgeted context dump for a change."""
    root = Path(project_path).resolve()

    try:
        output = build_context(root, name, max_tokens=max_tokens)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo(output)
