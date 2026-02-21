from pathlib import Path

from click.testing import CliRunner

from devspec.cli import cli


def _setup_old_layout(data_home: Path, project_name: str = "blog") -> Path:
    """Create an old-style openspec/ global directory."""
    old_root = data_home / "openspec" / project_name
    old_root.mkdir(parents=True)
    (old_root / "specs").mkdir()
    changes = old_root / "changes"
    changes.mkdir()
    (changes / "archive").mkdir()
    # Create a change with old metadata
    change = changes / "add-feature"
    change.mkdir()
    (change / ".openspec.yaml").write_text("schema: spec-driven-custom\n")
    (change / "proposal.md").write_text("## Why\nTest.\n")
    return old_root


class TestMigrate:
    def test_global_rename(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        _setup_old_layout(data_home)

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0
        assert "Renamed:" in result.output

        assert not (data_home / "openspec").exists()
        assert (data_home / "devspec" / "blog").is_dir()
        assert (data_home / "devspec" / "blog" / "specs").is_dir()

    def test_metadata_rename(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        _setup_old_layout(data_home)

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0

        change = data_home / "devspec" / "blog" / "changes" / "add-feature"
        assert not (change / ".openspec.yaml").exists()
        assert (change / ".devspec.yaml").exists()
        assert "Renamed 1 .openspec.yaml" in result.output

    def test_repo_cleanup(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        _setup_old_layout(data_home)

        # Create a repo with openspec/ directory
        repo = tmp_path / "repo"
        repo.mkdir()
        openspec = repo / "openspec"
        openspec.mkdir()
        (openspec / "config.yaml").write_text("schema: spec-driven-custom\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate", "--repo", str(repo)])
        assert result.exit_code == 0
        assert not openspec.exists()
        assert "Removed:" in result.output

    def test_error_target_exists(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        _setup_old_layout(data_home)
        # Pre-create target
        (data_home / "devspec").mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code != 0
        assert "Target already exists" in result.output

    def test_nothing_to_migrate(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0
        assert "Nothing to migrate" in result.output

    def test_metadata_rename_in_archive(self, tmp_path, monkeypatch):
        data_home = tmp_path / "data"
        data_home.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
        old_root = _setup_old_layout(data_home)
        # Add archived change with old metadata
        archived = old_root / "changes" / "archive" / "2026-01-01-old-change"
        archived.mkdir(parents=True)
        (archived / ".openspec.yaml").write_text("schema: spec-driven-custom\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0

        migrated = data_home / "devspec" / "blog" / "changes" / "archive" / "2026-01-01-old-change"
        assert not (migrated / ".openspec.yaml").exists()
        assert (migrated / ".devspec.yaml").exists()
        assert "Renamed 2 .openspec.yaml" in result.output
