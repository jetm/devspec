"""Unit tests for MCP resource handlers."""

import pytest

from devspec.mcp.resources import (
    get_artifact,
    get_delta_spec,
    get_main_spec,
    get_schema,
    list_changes,
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Create a temporary project data directory and patch _data_dir."""
    d = tmp_path / "data_dir"
    d.mkdir()
    (d / "changes").mkdir()
    (d / "changes" / "archive").mkdir()
    (d / "specs").mkdir()

    import devspec.mcp.resources as resources_module

    monkeypatch.setattr(resources_module, "_data_dir", lambda project=None: d)
    return d


@pytest.fixture
def change_dir(data_dir):
    """Create a sample change directory with artifacts."""
    cd = data_dir / "changes" / "test-change"
    cd.mkdir()
    (cd / "specs").mkdir()
    (cd / "proposal.md").write_text("# Proposal\n\nTest proposal content.")
    (cd / "design.md").write_text("# Design\n\nTest design content.")
    (cd / "tasks.md").write_text("- [ ] Task one\n- [x] Task two\n")
    specs_dir = cd / "specs" / "test-cap"
    specs_dir.mkdir()
    (specs_dir / "spec.md").write_text("## ADDED Requirements\n\n### Req: Test SHALL work\n")
    return cd


# -- list_changes --


class TestListChanges:
    def test_lists_active_changes(self, data_dir, change_dir):
        result = list_changes()
        assert "test-change" in result

    def test_excludes_archive_entry(self, data_dir, change_dir):
        result = list_changes()
        assert "archive" not in result

    def test_empty_returns_message(self, data_dir):
        result = list_changes()
        assert "No active changes" in result

    def test_multiple_changes_listed(self, data_dir):
        (data_dir / "changes" / "change-a").mkdir()
        (data_dir / "changes" / "change-b").mkdir()
        result = list_changes()
        assert "change-a" in result
        assert "change-b" in result


# -- get_artifact --


class TestGetArtifact:
    def test_reads_proposal(self, data_dir, change_dir):
        result = get_artifact("test-change", "proposal.md")
        assert "Test proposal content" in result

    def test_reads_tasks(self, data_dir, change_dir):
        result = get_artifact("test-change", "tasks.md")
        assert "Task one" in result

    def test_not_found_change(self, data_dir):
        result = get_artifact("no-such-change", "proposal.md")
        assert result.startswith("Error:")
        assert "not found" in result.lower()

    def test_not_found_artifact(self, data_dir, change_dir):
        result = get_artifact("test-change", "nonexistent.md")
        assert result.startswith("Error:")
        assert "not found" in result.lower()

    def test_reads_artifact_by_id(self, data_dir, change_dir):
        result = get_artifact("test-change", "proposal")
        assert "Test proposal content" in result

    def test_reads_specs_directory(self, data_dir, change_dir):
        result = get_artifact("test-change", "specs")
        assert "ADDED Requirements" in result
        assert "test-cap" in result

    def test_empty_directory_returns_error(self, data_dir, change_dir):
        (change_dir / "empty-dir").mkdir()
        result = get_artifact("test-change", "empty-dir")
        assert result.startswith("Error:")
        assert "no markdown files" in result.lower()


# -- get_delta_spec --


class TestGetDeltaSpec:
    def test_reads_existing_spec(self, data_dir, change_dir):
        result = get_delta_spec("test-change", "test-cap")
        assert "ADDED Requirements" in result

    def test_not_found_change(self, data_dir):
        result = get_delta_spec("no-such-change", "test-cap")
        assert result.startswith("Error:")

    def test_not_found_capability(self, data_dir, change_dir):
        result = get_delta_spec("test-change", "nonexistent-cap")
        assert result.startswith("Error:")
        assert "not found" in result.lower()


# -- get_main_spec --


class TestGetMainSpec:
    def test_reads_main_spec(self, data_dir):
        spec_dir = data_dir / "specs" / "my-capability"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Main Spec\n\nContent here.")
        result = get_main_spec("my-capability")
        assert "Content here" in result

    def test_not_found(self, data_dir):
        result = get_main_spec("no-such-capability")
        assert result.startswith("Error:")
        assert "not found" in result.lower()


# -- get_schema --


class TestGetSchema:
    def test_returns_schema_content(self, data_dir):
        result = get_schema()
        # Schema YAML should contain key fields
        assert "spec-driven-custom" in result or "name:" in result

    def test_returns_string(self, data_dir):
        result = get_schema()
        assert isinstance(result, str)
        assert len(result) > 0
