from pathlib import Path

import pytest

from devspec.core.resolve import get_data_root, resolve_project_data_dir, resolve_project_name


class TestGetDataRoot:
    def test_respects_xdg_data_home(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
        assert get_data_root() == Path("/custom/data/devspec")

    def test_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        assert get_data_root() == Path.home() / ".local" / "share" / "devspec"

    def test_empty_xdg_data_home_uses_default(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "")
        assert get_data_root() == Path.home() / ".local" / "share" / "devspec"

    def test_whitespace_xdg_data_home_uses_default(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "   ")
        assert get_data_root() == Path.home() / ".local" / "share" / "devspec"


class TestResolveProjectName:
    def test_finds_marker_in_current_dir(self, tmp_path):
        (tmp_path / ".devspec").write_text("my-project\n")
        assert resolve_project_name(tmp_path) == "my-project"

    def test_strips_whitespace_and_newlines(self, tmp_path):
        (tmp_path / ".devspec").write_text("  blog  \n")
        assert resolve_project_name(tmp_path) == "blog"

    def test_walks_parent_directories(self, tmp_path):
        (tmp_path / ".devspec").write_text("blog")
        subdir = tmp_path / "src" / "components"
        subdir.mkdir(parents=True)
        assert resolve_project_name(subdir) == "blog"

    def test_raises_when_no_marker_found(self, tmp_path):
        subdir = tmp_path / "empty"
        subdir.mkdir()
        with pytest.raises(FileNotFoundError, match="No .devspec marker file found"):
            resolve_project_name(subdir)

    def test_raises_on_empty_marker(self, tmp_path):
        (tmp_path / ".devspec").write_text("")
        with pytest.raises(ValueError, match="Empty .devspec marker"):
            resolve_project_name(tmp_path)

    def test_raises_on_invalid_kebab_case(self, tmp_path):
        (tmp_path / ".devspec").write_text("My Project")
        with pytest.raises(ValueError, match="Must be kebab-case"):
            resolve_project_name(tmp_path)

    def test_raises_on_uppercase(self, tmp_path):
        (tmp_path / ".devspec").write_text("MyProject")
        with pytest.raises(ValueError, match="Must be kebab-case"):
            resolve_project_name(tmp_path)


class TestResolveProjectDataDir:
    def test_project_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        project_dir = tmp_path / "devspec" / "blog"
        project_dir.mkdir(parents=True)
        assert resolve_project_data_dir("blog") == project_dir

    def test_project_override_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        with pytest.raises(FileNotFoundError, match="Project not found"):
            resolve_project_data_dir("nonexistent")

    def test_marker_resolution(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        project_dir = tmp_path / "devspec" / "blog"
        project_dir.mkdir(parents=True)
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".devspec").write_text("blog")
        monkeypatch.chdir(repo)
        assert resolve_project_data_dir() == project_dir

    def test_marker_resolution_data_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".devspec").write_text("blog")
        monkeypatch.chdir(repo)
        with pytest.raises(FileNotFoundError, match="Project data directory not found"):
            resolve_project_data_dir()

    def test_no_project_no_marker(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            resolve_project_data_dir()

    def test_project_override_rejects_path_traversal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        with pytest.raises(FileNotFoundError, match="Invalid project name"):
            resolve_project_data_dir("../../../tmp")

    def test_project_override_rejects_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        with pytest.raises(FileNotFoundError, match="Invalid project name"):
            resolve_project_data_dir("/etc")

    def test_project_override_rejects_uppercase(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        with pytest.raises(FileNotFoundError, match="Invalid project name"):
            resolve_project_data_dir("MyProject")

    def test_invalid_marker_raises_file_not_found(self, tmp_path, monkeypatch):
        """ValueError from invalid marker content is wrapped as FileNotFoundError."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        (tmp_path / "devspec").mkdir()
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".devspec").write_text("INVALID NAME")
        monkeypatch.chdir(repo)
        with pytest.raises(FileNotFoundError, match="Must be kebab-case"):
            resolve_project_data_dir()
