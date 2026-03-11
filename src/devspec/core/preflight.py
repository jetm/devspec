"""Pre-flight environment readiness checks."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PreflightCheck:
    name: str
    status: str  # "ok", "warn", "error"
    detail: str


@dataclass
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status != "error" for c in self.checks)

    @property
    def summary(self) -> dict[str, int]:
        ok = sum(1 for c in self.checks if c.status == "ok")
        warn = sum(1 for c in self.checks if c.status == "warn")
        error = sum(1 for c in self.checks if c.status == "error")
        return {"ok": ok, "warn": warn, "error": error}


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=10,
    )


def check_git_state() -> list[PreflightCheck]:
    """Check working tree cleanliness, stash entries, and leftover backup refs."""
    checks: list[PreflightCheck] = []

    # Check if we're in a git repo
    result = _run_git(["rev-parse", "--is-inside-work-tree"])
    if result.returncode != 0:
        return checks  # Not a git repo - skip silently

    # Working tree cleanliness
    result = _run_git(["status", "--porcelain"])
    if result.returncode == 0:
        dirty_files = [line for line in result.stdout.strip().splitlines() if line.strip()]
        if dirty_files:
            checks.append(
                PreflightCheck(
                    name="git-status",
                    status="warn",
                    detail=f"{len(dirty_files)} uncommitted change(s)",
                )
            )
        else:
            checks.append(
                PreflightCheck(
                    name="git-status",
                    status="ok",
                    detail="Working tree clean",
                )
            )

    # Stash entries
    result = _run_git(["stash", "list"])
    if result.returncode == 0:
        stash_entries = [line for line in result.stdout.strip().splitlines() if line.strip()]
        if stash_entries:
            checks.append(
                PreflightCheck(
                    name="git-stash",
                    status="warn",
                    detail=f"{len(stash_entries)} stash entry/entries",
                )
            )

    # Leftover backup refs
    result = _run_git(["for-each-ref", "--format=%(refname)", "refs/original/"])
    if result.returncode == 0 and result.stdout.strip():
        checks.append(
            PreflightCheck(
                name="git-backup-refs",
                status="warn",
                detail="Leftover refs/original/ from filter-branch",
            )
        )

    return checks


def check_data_store(data_dir: Path) -> list[PreflightCheck]:
    """Check global data dir existence, required subdirectories, writability."""
    checks: list[PreflightCheck] = []

    if not data_dir.exists():
        checks.append(
            PreflightCheck(
                name="data-store",
                status="error",
                detail=f"Data directory not found: {data_dir}",
            )
        )
        return checks

    if not data_dir.is_dir():
        checks.append(
            PreflightCheck(
                name="data-store",
                status="error",
                detail=f"Data path exists but is not a directory: {data_dir}",
            )
        )
        return checks

    # Check required subdirectories
    missing = []
    for subdir in ("specs", "changes"):
        if not (data_dir / subdir).is_dir():
            missing.append(subdir)

    if missing:
        checks.append(
            PreflightCheck(
                name="data-store",
                status="error",
                detail=f"Missing required subdirectories: {', '.join(missing)}",
            )
        )
        return checks

    # Check writability
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(dir=data_dir, delete=True):
            pass
        checks.append(
            PreflightCheck(
                name="data-store",
                status="ok",
                detail="Data store healthy",
            )
        )
    except OSError:
        checks.append(
            PreflightCheck(
                name="data-store",
                status="error",
                detail=f"Data directory not writable: {data_dir}",
            )
        )

    return checks


def check_change_integrity(data_dir: Path) -> list[PreflightCheck]:
    """Check that active changes have valid structure."""
    checks: list[PreflightCheck] = []
    changes_dir = data_dir / "changes"

    if not changes_dir.is_dir():
        return checks

    active_changes = [d for d in sorted(changes_dir.iterdir()) if d.is_dir() and d.name != "archive"]

    if not active_changes:
        return checks  # No active changes - skip silently

    broken = []
    for change_dir in active_changes:
        meta = change_dir / ".devspec.yaml"
        if not meta.is_file():
            broken.append(f"{change_dir.name}: missing .devspec.yaml")

    if broken:
        checks.append(
            PreflightCheck(
                name="change-integrity",
                status="error",
                detail="; ".join(broken),
            )
        )
    else:
        checks.append(
            PreflightCheck(
                name="change-integrity",
                status="ok",
                detail=f"{len(active_changes)} active change(s) valid",
            )
        )

    return checks


def check_tool_availability() -> list[PreflightCheck]:
    """Check that commonly needed tools are on PATH."""
    checks: list[PreflightCheck] = []
    tools = {
        "ruff": "Python linter",
        "shellcheck": "Shell script linter",
        "uv": "Python package manager",
        "claude": "Claude Code CLI",
    }

    missing = []
    for tool, description in tools.items():
        if not shutil.which(tool):
            missing.append(f"{tool} ({description})")

    if missing:
        checks.append(
            PreflightCheck(
                name="tool-availability",
                status="warn",
                detail=f"Missing: {', '.join(missing)}",
            )
        )
    else:
        checks.append(
            PreflightCheck(
                name="tool-availability",
                status="ok",
                detail="All tools available",
            )
        )

    return checks


def run_preflight(data_dir: Path) -> PreflightReport:
    """Orchestrate all checks and return a PreflightReport."""
    report = PreflightReport()
    report.checks.extend(check_git_state())
    report.checks.extend(check_data_store(data_dir))
    report.checks.extend(check_change_integrity(data_dir))
    report.checks.extend(check_tool_availability())
    return report
