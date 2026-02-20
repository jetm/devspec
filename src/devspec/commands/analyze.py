import json
from dataclasses import asdict
from pathlib import Path

import click

from devspec.core.analyzer import AnalysisReport, analyze_change


@click.command()
@click.argument("name")
@click.option("--path", "project_path", default=".", help="Project root directory.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def analyze(name: str, project_path: str, as_json: bool) -> None:
    """Analyze cross-artifact consistency for a change."""
    root = Path(project_path).resolve()
    change_dir = root / "openspec" / "changes" / name

    if not change_dir.exists():
        click.echo(f"Change not found: {name}")
        raise SystemExit(1)

    report = analyze_change(change_dir)

    if as_json:
        click.echo(json.dumps(asdict(report), indent=2))
    else:
        _print_report(report)

    if report.summary.get("critical", 0) > 0:
        raise SystemExit(1)


def _print_report(report: AnalysisReport) -> None:
    click.echo(f"## Analysis: {report.change_name}\n")

    if report.coverage:
        c = report.coverage
        req_pct = (c.requirements_with_tasks * 100 // c.total_requirements) if c.total_requirements else 0
        task_pct = (c.tasks_with_requirements * 100 // c.total_tasks) if c.total_tasks else 0

        click.echo("### Coverage")
        click.echo(f"  Requirements: {c.total_requirements} total, {c.requirements_with_tasks} with tasks ({req_pct}%)")
        click.echo(f"  Tasks: {c.total_tasks} total, {c.tasks_with_requirements} with requirements ({task_pct}%)")

        if c.uncovered_requirements:
            click.echo("\n  Uncovered requirements:")
            for r in c.uncovered_requirements:
                click.echo(f"    [!] {r}")

        if c.orphan_tasks:
            click.echo("\n  Orphan tasks:")
            for t in c.orphan_tasks:
                click.echo(f"    [!] {t}")
        click.echo()

    # Group issues by category
    consistency = [i for i in report.issues if i.category == "consistency"]
    ambiguity = [i for i in report.issues if i.category == "ambiguity"]
    fmt = [i for i in report.issues if i.category == "format"]

    if consistency:
        click.echo("### Consistency")
        for issue in consistency:
            icon = "!" if issue.severity in ("CRITICAL", "WARNING") else "i"
            click.echo(f"  [{icon}] {issue.message}")
        click.echo()

    if ambiguity:
        click.echo("### Ambiguity")
        for issue in ambiguity:
            icon = "!" if issue.severity == "CRITICAL" else "i"
            click.echo(f"  [{icon}] {issue.location}: {issue.message}")
        click.echo()

    if fmt:
        click.echo("### Format")
        for issue in fmt:
            click.echo(f"  [!] {issue.message}")
        click.echo()

    s = report.summary
    total = s.get("critical", 0) + s.get("warning", 0) + s.get("suggestion", 0)
    if total == 0:
        click.echo("No issues found.")
    else:
        click.echo(
            f"{s.get('critical', 0)} critical, {s.get('warning', 0)} warnings, {s.get('suggestion', 0)} suggestions"
        )
