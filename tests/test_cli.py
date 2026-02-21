import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from devspec.cli import cli


def _setup_project(tmp_path: Path, project_name: str = "test-proj") -> tuple[Path, Path]:
    """Create a project with global store layout. Returns (data_home, data_dir)."""
    data_home = tmp_path / "data"
    data_dir = data_home / "devspec" / project_name
    data_dir.mkdir(parents=True)
    (data_dir / "specs").mkdir()
    (data_dir / "changes").mkdir()
    (data_dir / "changes" / "archive").mkdir()
    (data_dir / "learnings").mkdir()
    (data_dir / "config.yaml").write_text(yaml.dump({"schema": "spec-driven-custom"}))
    return data_home, data_dir


def _setup_change(tmp_path: Path, name: str = "test-change") -> tuple[Path, Path]:
    """Create a project with a change that has all artifacts. Returns (data_home, data_dir)."""
    data_home, data_dir = _setup_project(tmp_path)
    change_dir = data_dir / "changes" / name
    change_dir.mkdir()
    (change_dir / ".devspec.yaml").write_text(yaml.dump({"schema": "spec-driven-custom", "created": "2026-02-19"}))
    (change_dir / "proposal.md").write_text("## Why\n\nTest.\n")
    (change_dir / "design.md").write_text("## Context\n\nTest.\n")
    (change_dir / "tasks.md").write_text("## 1. Setup\n\n- [x] 1.1 Done\n")
    specs_dir = change_dir / "specs" / "test-cap"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Test\n"
        "The system SHALL test.\n\n"
        "#### Scenario: Basic\n"
        "- **WHEN** test\n"
        "- **THEN** pass\n"
    )
    return data_home, data_dir


class TestAnalyze:
    def test_analyze_text(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "test-change", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "Analysis: test-change" in result.output

    def test_analyze_json(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "test-change", "--json", "--project", "test-proj"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["change_name"] == "test-change"
        assert "issues" in data
        assert "summary" in data

    def test_analyze_missing_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "nonexistent", "--project", "test-proj"])
        assert result.exit_code != 0


class TestVersion:
    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Spec-driven development workflow engine" in result.output


class TestNew:
    def test_creates_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "my-change", "--project", "test-proj"])
        assert result.exit_code == 0
        assert (data_dir / "changes" / "my-change").is_dir()
        assert (data_dir / "changes" / "my-change" / ".devspec.yaml").exists()

    def test_fails_if_exists(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        (data_dir / "changes" / "my-change").mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "my-change", "--project", "test-proj"])
        assert result.exit_code != 0

    def test_rejects_name_with_spaces(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "has spaces", "--project", "test-proj"])
        assert result.exit_code != 0
        assert "kebab-case" in result.output

    def test_rejects_uppercase_name(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "UPPERCASE", "--project", "test-proj"])
        assert result.exit_code != 0
        assert "kebab-case" in result.output

    def test_rejects_empty_name(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "", "--project", "test-proj"])
        assert result.exit_code != 0
        assert "empty" in result.output.lower()

    def test_accepts_numeric_segments(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "add-v2-support", "--project", "test-proj"])
        assert result.exit_code == 0


class TestStatus:
    def test_status_json(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--change", "test-change", "--json", "--project", "test-proj"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["schemaName"] == "spec-driven-custom"
        assert isinstance(data["artifacts"], list)

    def test_status_text(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--change", "test-change", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "test-change" in result.output

    def test_status_missing_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--change", "nonexistent", "--project", "test-proj"])
        assert result.exit_code != 0


class TestList:
    def test_list_json(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json", "--project", "test-proj"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "test-change"
        assert data[0]["status"] == "complete"

    def test_list_planned_status(self, tmp_path, monkeypatch):
        """All artifacts present but tasks.md has unchecked items -> planned."""
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        change_dir = data_dir / "changes" / "test-change"
        (change_dir / "tasks.md").write_text("## 1. Setup\n\n- [x] 1.1 Done\n- [ ] 1.2 Not done\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json", "--project", "test-proj"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["status"] == "planned"

    def test_list_incomplete_status(self, tmp_path, monkeypatch):
        """Missing artifacts -> incomplete."""
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        change_dir = data_dir / "changes" / "partial-change"
        change_dir.mkdir()
        (change_dir / "proposal.md").write_text("## Why\n\nTest.\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json", "--project", "test-proj"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["status"] == "incomplete"

    def test_list_empty(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "No active changes" in result.output


class TestInstructions:
    def test_instructions_json(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(
            cli, ["instructions", "proposal", "--change", "test-change", "--json", "--project", "test-proj"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["artifactId"] == "proposal"
        assert "template" in data
        assert "instruction" in data

    def test_instructions_unknown_artifact(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(
            cli, ["instructions", "nonexistent", "--change", "test-change", "--project", "test-proj"]
        )
        assert result.exit_code != 0


class TestValidate:
    def test_validate_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "test-change", "--project", "test-proj"])
        assert result.exit_code == 0

    def test_validate_all_specs(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        # Create a main spec
        spec_dir = data_dir / "specs" / "test-cap"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "# test-cap Specification\n\n## Purpose\nTest capability for validation.\n\n## Requirements\n\n"
            "### Requirement: Test feature\n"
            "The system SHALL support testing.\n\n"
            "#### Scenario: Basic test\n"
            "- **WHEN** test runs\n"
            "- **THEN** it passes\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_change_exits_nonzero_on_errors(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        change_dir = data_dir / "changes" / "bad-change"
        change_dir.mkdir()
        specs_dir = change_dir / "specs" / "bad-cap"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            "## ADDED Requirements\n\n"
            "### Requirement: Missing normative language\n"
            "This requirement has no SHALL or MUST.\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "bad-change", "--project", "test-proj"])
        assert result.exit_code != 0

    def test_validate_main_specs_exits_nonzero_on_errors(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        spec_dir = data_dir / "specs" / "bad-cap"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "# bad-cap Specification\n\n## Requirements\n\n"
            "### Requirement: No normative language\n"
            "This requirement has no SHALL or MUST.\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--project", "test-proj"])
        assert result.exit_code != 0


class TestArchive:
    def test_archive_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["archive", "test-change", "--skip-specs", "--yes", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "Archived" in result.output
        # Change should be moved to archive
        assert not (data_dir / "changes" / "test-change").exists()
        archive_entries = list((data_dir / "changes" / "archive").iterdir())
        assert len(archive_entries) == 1

    def test_archive_missing_change(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["archive", "nonexistent", "--project", "test-proj"])
        assert result.exit_code != 0


class TestContext:
    def test_context_output(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["context", "test-change", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "proposal.md" in result.output

    def test_context_missing(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_project(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        result = runner.invoke(cli, ["context", "nonexistent", "--project", "test-proj"])
        assert result.exit_code != 0


class TestHandoff:
    def test_write_and_read(self, tmp_path, monkeypatch):
        data_home, data_dir = _setup_change(tmp_path)
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        runner = CliRunner()
        # Write
        result = runner.invoke(
            cli,
            ["handoff", "write", "test-change", "--project", "test-proj"],
            input="## Problem\nTest problem\n",
        )
        assert result.exit_code == 0
        assert "Handoff written" in result.output

        # Read
        result = runner.invoke(cli, ["handoff", "read", "test-change", "--project", "test-proj"])
        assert result.exit_code == 0
        assert "Test problem" in result.output
