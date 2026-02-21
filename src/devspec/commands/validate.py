from pathlib import Path

import click

from devspec.core.validator import validate_change_delta_specs, validate_spec_content


@click.command()
@click.argument("name", required=False)
@click.option("--path", "project_path", default=".", help="Project root directory.")
def validate(name: str | None, project_path: str) -> None:
    """Validate specs or a specific change's delta specs."""
    root = Path(project_path).resolve()

    if name:
        # Validate a specific change's delta specs
        change_dir = root / "openspec" / "changes" / name
        if not change_dir.exists():
            click.echo(f"Change not found: {name}")
            raise SystemExit(1)

        report = validate_change_delta_specs(change_dir)
        _print_report(report, f"Change: {name}")
        if not report.valid:
            raise SystemExit(1)
    else:
        # Validate all main specs
        specs_dir = root / "openspec" / "specs"
        if not specs_dir.exists():
            click.echo("No openspec/specs/ directory.")
            raise SystemExit(1)

        all_valid = True
        for spec_dir in sorted(specs_dir.iterdir()):
            if not spec_dir.is_dir():
                continue
            spec_file = spec_dir / "spec.md"
            if not spec_file.exists():
                continue
            content = spec_file.read_text()
            report = validate_spec_content(spec_dir.name, content)
            if not report.valid:
                all_valid = False
                _print_report(report, f"Spec: {spec_dir.name}")

        if all_valid:
            click.echo("All specs valid.")
        else:
            raise SystemExit(1)


def _print_report(report, label: str) -> None:
    icon = "+" if report.valid else "x"
    click.echo(f"[{icon}] {label}")
    for issue in report.issues:
        level_icon = {"ERROR": "x", "WARNING": "!", "INFO": "i"}[issue.level]
        click.echo(f"  [{level_icon}] {issue.path}: {issue.message}")
    if report.valid:
        click.echo("  Valid.")
    else:
        s = report.summary
        click.echo(f"  {s['errors']} errors, {s['warnings']} warnings")
