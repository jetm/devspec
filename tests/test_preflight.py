from pathlib import Path
from unittest.mock import patch

import pytest

from devspec.core.preflight import (
    PreflightReport,
    check_change_integrity,
    check_data_store,
    check_git_state,
    check_tool_availability,
    run_preflight,
)

# --- PreflightReport ---


@pytest.mark.unit
class TestPreflightReport:
    def test_passed_when_all_ok(self):
        report = PreflightReport()
        report.checks = [
            type("C", (), {"name": "a", "status": "ok", "detail": ""})(),
            type("C", (), {"name": "b", "status": "warn", "detail": ""})(),
        ]
        assert report.passed is True

    def test_failed_when_error(self):
        report = PreflightReport()
        report.checks = [
            type("C", (), {"name": "a", "status": "ok", "detail": ""})(),
            type("C", (), {"name": "b", "status": "error", "detail": ""})(),
        ]
        assert report.passed is False

    def test_summary_counts(self):
        report = PreflightReport()
        report.checks = [
            type("C", (), {"name": "a", "status": "ok", "detail": ""})(),
            type("C", (), {"name": "b", "status": "warn", "detail": ""})(),
            type("C", (), {"name": "c", "status": "error", "detail": ""})(),
            type("C", (), {"name": "d", "status": "ok", "detail": ""})(),
        ]
        assert report.summary == {"ok": 2, "warn": 1, "error": 1}

    def test_empty_report_passes(self):
        report = PreflightReport()
        assert report.passed is True
        assert report.summary == {"ok": 0, "warn": 0, "error": 0}


# --- check_git_state ---


@pytest.mark.unit
class TestCheckGitState:
    def test_not_a_git_repo(self):
        with patch("devspec.core.preflight._run_git") as mock_git:
            mock_git.return_value = type("R", (), {"returncode": 128, "stdout": "", "stderr": ""})()
            checks = check_git_state()
            assert checks == []

    def test_clean_tree(self):
        def fake_git(args, cwd=None):
            if args[0] == "rev-parse":
                return type("R", (), {"returncode": 0, "stdout": "true\n", "stderr": ""})()
            if args[0] == "status":
                return type("R", (), {"returncode": 0, "stdout": "\n", "stderr": ""})()
            if args[0] == "stash":
                return type("R", (), {"returncode": 0, "stdout": "\n", "stderr": ""})()
            if args[0] == "for-each-ref":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        with patch("devspec.core.preflight._run_git", side_effect=fake_git):
            checks = check_git_state()
            assert len(checks) == 1
            assert checks[0].name == "git-status"
            assert checks[0].status == "ok"

    def test_dirty_tree(self):
        def fake_git(args, cwd=None):
            if args[0] == "rev-parse":
                return type("R", (), {"returncode": 0, "stdout": "true\n", "stderr": ""})()
            if args[0] == "status":
                return type("R", (), {"returncode": 0, "stdout": " M foo.py\n M bar.py\n", "stderr": ""})()
            if args[0] == "stash":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[0] == "for-each-ref":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        with patch("devspec.core.preflight._run_git", side_effect=fake_git):
            checks = check_git_state()
            assert any(c.name == "git-status" and c.status == "warn" and "2" in c.detail for c in checks)

    def test_stash_entries(self):
        def fake_git(args, cwd=None):
            if args[0] == "rev-parse":
                return type("R", (), {"returncode": 0, "stdout": "true\n", "stderr": ""})()
            if args[0] == "status":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[0] == "stash":
                return type("R", (), {"returncode": 0, "stdout": "stash@{0}: WIP\n", "stderr": ""})()
            if args[0] == "for-each-ref":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        with patch("devspec.core.preflight._run_git", side_effect=fake_git):
            checks = check_git_state()
            assert any(c.name == "git-stash" and c.status == "warn" for c in checks)

    def test_leftover_backup_refs(self):
        def fake_git(args, cwd=None):
            if args[0] == "rev-parse":
                return type("R", (), {"returncode": 0, "stdout": "true\n", "stderr": ""})()
            if args[0] == "status":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[0] == "stash":
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if args[0] == "for-each-ref":
                return type("R", (), {"returncode": 0, "stdout": "refs/original/refs/heads/main\n", "stderr": ""})()
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()

        with patch("devspec.core.preflight._run_git", side_effect=fake_git):
            checks = check_git_state()
            assert any(c.name == "git-backup-refs" and c.status == "warn" for c in checks)


# --- check_data_store ---


@pytest.mark.unit
class TestCheckDataStore:
    def test_healthy_store(self, tmp_project: Path):
        checks = check_data_store(tmp_project)
        assert len(checks) == 1
        assert checks[0].status == "ok"

    def test_missing_dir(self, tmp_path: Path):
        checks = check_data_store(tmp_path / "nonexistent")
        assert len(checks) == 1
        assert checks[0].status == "error"
        assert "not found" in checks[0].detail

    def test_not_a_directory(self, tmp_path: Path):
        f = tmp_path / "file"
        f.write_text("x")
        checks = check_data_store(f)
        assert len(checks) == 1
        assert checks[0].status == "error"
        assert "not a directory" in checks[0].detail

    def test_missing_subdirectories(self, tmp_path: Path):
        data_dir = tmp_path / "store"
        data_dir.mkdir()
        checks = check_data_store(data_dir)
        assert len(checks) == 1
        assert checks[0].status == "error"
        assert "Missing required" in checks[0].detail


# --- check_change_integrity ---


@pytest.mark.unit
class TestCheckChangeIntegrity:
    def test_valid_change(self, tmp_project: Path):
        change_dir = tmp_project / "changes" / "my-change"
        change_dir.mkdir()
        (change_dir / ".devspec.yaml").write_text("schema: spec-driven-custom\n")
        checks = check_change_integrity(tmp_project)
        assert len(checks) == 1
        assert checks[0].status == "ok"
        assert "1 active" in checks[0].detail

    def test_missing_metadata(self, tmp_project: Path):
        change_dir = tmp_project / "changes" / "broken"
        change_dir.mkdir()
        checks = check_change_integrity(tmp_project)
        assert len(checks) == 1
        assert checks[0].status == "error"
        assert "missing .devspec.yaml" in checks[0].detail

    def test_no_active_changes(self, tmp_project: Path):
        checks = check_change_integrity(tmp_project)
        assert checks == []

    def test_skips_archive(self, tmp_project: Path):
        # archive dir already exists from tmp_project, just verify it's ignored
        checks = check_change_integrity(tmp_project)
        assert checks == []


# --- check_tool_availability ---


@pytest.mark.unit
class TestCheckToolAvailability:
    def test_all_present(self):
        with patch("devspec.core.preflight.shutil.which", return_value="/usr/bin/x"):
            checks = check_tool_availability()
            assert len(checks) == 1
            assert checks[0].status == "ok"

    def test_some_missing(self):
        def fake_which(name):
            return "/usr/bin/x" if name in ("ruff", "uv") else None

        with patch("devspec.core.preflight.shutil.which", side_effect=fake_which):
            checks = check_tool_availability()
            assert len(checks) == 1
            assert checks[0].status == "warn"
            assert "Missing" in checks[0].detail


# --- run_preflight ---


@pytest.mark.unit
class TestRunPreflight:
    def test_orchestrates_all_checks(self, tmp_project: Path):
        with patch("devspec.core.preflight._run_git") as mock_git:
            mock_git.return_value = type("R", (), {"returncode": 128, "stdout": "", "stderr": ""})()
            report = run_preflight(tmp_project)
            assert report.passed is True
            check_names = [c.name for c in report.checks]
            assert "data-store" in check_names
            assert "tool-availability" in check_names
