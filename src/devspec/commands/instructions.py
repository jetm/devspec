import json
from pathlib import Path

import click

from devspec.core.instructions import generate_instructions


@click.command()
@click.argument("artifact_id")
@click.option("--change", "change_name", required=True, help="Change name.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--path", "project_path", default=".", help="Project root directory.")
def instructions(artifact_id: str, change_name: str, as_json: bool, project_path: str) -> None:
    """Get enriched instructions for creating an artifact."""
    root = Path(project_path).resolve()

    try:
        bundle = generate_instructions(root, artifact_id, change_name)
    except ValueError as e:
        click.echo(str(e))
        raise SystemExit(1)

    if as_json:
        data = {
            "artifactId": bundle.artifact_id,
            "template": bundle.template,
            "instruction": bundle.instruction,
            "outputPath": bundle.output_path,
            "dependencies": bundle.dependencies,
            "context": bundle.context,
            "rules": bundle.rules,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Artifact: {bundle.artifact_id}")
        click.echo(f"Output: {bundle.output_path}")
        click.echo()
        click.echo("--- Template ---")
        click.echo(bundle.template)
        click.echo()
        click.echo("--- Instruction ---")
        click.echo(bundle.instruction)
        if bundle.context:
            click.echo()
            click.echo("--- Context ---")
            click.echo(bundle.context)
        if bundle.rules:
            click.echo()
            click.echo("--- Rules ---")
            for rule in bundle.rules:
                click.echo(f"  - {rule}")
