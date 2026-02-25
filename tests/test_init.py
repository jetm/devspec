from click.testing import CliRunner

from devspec.cli import cli


class TestInit:
    def test_creates_global_dir_structure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--name", "my-project"])
        assert result.exit_code == 0

        data_dir = tmp_path / "data" / "devspec" / "my-project"
        assert data_dir.is_dir()
        assert (data_dir / "specs").is_dir()
        assert (data_dir / "changes").is_dir()
        assert (data_dir / "changes" / "archive").is_dir()
        assert (data_dir / "learnings").is_dir()

    def test_creates_marker_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--name", "blog"])
        assert result.exit_code == 0

        marker = tmp_path / ".devspec"
        assert marker.is_file()
        assert marker.read_text().strip() == "blog"

    def test_errors_on_existing_marker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".devspec").write_text("existing")
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--name", "blog"])
        assert result.exit_code != 0
        assert ".devspec marker already exists" in result.output

    def test_name_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--name", "custom-name"])
        assert result.exit_code == 0

        marker = tmp_path / ".devspec"
        assert marker.read_text().strip() == "custom-name"
        assert (tmp_path / "data" / "devspec" / "custom-name").is_dir()

    def test_default_name_from_basename(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "my-blog"
        project_dir.mkdir()
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        marker = project_dir / ".devspec"
        assert marker.read_text().strip() == "my-blog"

    def test_rejects_invalid_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--name", "UPPER CASE"])
        assert result.exit_code != 0
        assert "kebab-case" in result.output
