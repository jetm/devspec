"""CLI command for environment pre-flight checks."""

import json

import click

from devspec.core.preflight import run_preflight
from devspec.core.resolve import resolve_project_data_dir

STATUS_ICONS = {"ok": "\u2713", "warn": "!", "error": "\u2717"}
STATUS_COLORS = {"ok": "green", "warn": "yellow", "error": "red"}


@click.command()
@click.option("--project", "project", default=None, help="Project name override.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def preflight(project: str | None, as_json: bool) -> None:
    """Run environment pre-flight checks before starting work."""
    try:
        data_dir = resolve_project_data_dir(project)
    except FileNotFoundError as e:
        if as_json:
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(str(e))
        raise SystemExit(1)

    report = run_preflight(data_dir)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "passed": report.passed,
                    "summary": report.summary,
                    "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in report.checks],
                }
            )
        )
    else:
        for check in report.checks:
            icon = STATUS_ICONS[check.status]
            color = STATUS_COLORS[check.status]
            click.echo(click.style(f"  [{icon}] ", fg=color) + f"{check.name}: {check.detail}")

        s = report.summary
        click.echo()
        if report.passed:
            click.echo(click.style("Preflight passed", fg="green") + f" ({s['ok']} ok, {s['warn']} warn)")
        else:
            click.echo(
                click.style("Preflight failed", fg="red") + f" ({s['error']} error, {s['warn']} warn, {s['ok']} ok)"
            )
            raise SystemExit(1)
