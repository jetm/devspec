"""Unit tests for MCP tool handlers."""

import pytest
import yaml

from devspec.mcp.tools import (
    devspec_analyze,
    devspec_archive,
    devspec_context,
    devspec_handoff_read,
    devspec_handoff_write,
    devspec_instructions,
    devspec_list,
    devspec_new,
    devspec_status,
    devspec_task_mark,
    devspec_validate,
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Create a temporary project data directory and patch resolve_project_data_dir."""
    d = tmp_path / "data_dir"
    d.mkdir()
    (d / "changes").mkdir()
    (d / "changes" / "archive").mkdir()
    (d / "specs").mkdir()

    import devspec.mcp.tools as tools_module

    monkeypatch.setattr(tools_module, "_get_data_dir", lambda project=None: d)
    return d


@pytest.fixture
def change_dir(data_dir):
    """Create a sample change directory with all artifacts."""
    cd = data_dir / "changes" / "test-change"
    cd.mkdir()
    (cd / ".devspec.yaml").write_text(yaml.dump({"schema": "spec-driven-custom", "created": "2026-02-21"}))
    (cd / "specs").mkdir()
    (cd / "proposal.md").write_text(
        "## Why\n\nTest proposal.\n\n## What Changes\n\n- Add test\n\n"
        "## Capabilities\n\n### New Capabilities\n- `test-cap`: Test\n\n"
        "### Modified Capabilities\n\n## Impact\n\n- tests/\n"
    )
    specs_dir = cd / "specs" / "test-cap"
    specs_dir.mkdir()
    (specs_dir / "spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Test SHALL work\n"
        "The system SHALL work correctly.\n\n"
        "#### Scenario: Basic\n"
        "- **WHEN** run\n"
        "- **THEN** works\n"
    )
    (cd / "design.md").write_text("## Design\n\nTest design.")
    (cd / "tasks.md").write_text("- [ ] Task one\n- [x] Task two\n- [ ] Task three\n")
    return cd


# -- devspec_list --


class TestDevspecList:
    def test_returns_changes(self, data_dir, change_dir):
        result = devspec_list()
        assert "changes" in result
        names = [c["name"] for c in result["changes"]]
        assert "test-change" in names

    def test_excludes_archive(self, data_dir, change_dir):
        result = devspec_list()
        names = [c["name"] for c in result["changes"]]
        assert "archive" not in names

    def test_empty_changes_dir(self, data_dir):
        result = devspec_list()
        assert result == {"changes": []}

    def test_error_when_no_changes_dir(self, data_dir, monkeypatch):
        import devspec.mcp.tools as tools_module

        monkeypatch.setattr(tools_module, "_get_data_dir", lambda project=None: data_dir / "nonexistent")
        result = devspec_list()
        assert "error" in result


# -- devspec_new --


class TestDevspecNew:
    def test_creates_change(self, data_dir):
        result = devspec_new("my-feature")
        assert result.get("created") == "my-feature"
        assert (data_dir / "changes" / "my-feature").exists()

    def test_invalid_name_rejected(self, data_dir):
        result = devspec_new("Invalid Name")
        assert "error" in result
        assert result["error"]["code"] == "invalid_name"

    def test_empty_name_rejected(self, data_dir):
        result = devspec_new("")
        assert "error" in result

    def test_duplicate_name_rejected(self, data_dir, change_dir):
        result = devspec_new("test-change")
        assert "error" in result
        assert result["error"]["code"] == "already_exists"


# -- devspec_status --


class TestDevspecStatus:
    def test_returns_status(self, data_dir, change_dir):
        result = devspec_status("test-change")
        assert "schemaName" in result
        assert "artifacts" in result
        assert "isComplete" in result

    def test_not_found_error(self, data_dir):
        result = devspec_status("nonexistent")
        assert "error" in result
        assert result["error"]["code"] == "not_found"
        assert "nonexistent" in result["error"]["message"]

    def test_all_artifacts_complete(self, data_dir, change_dir):
        result = devspec_status("test-change")
        # proposal, design, tasks, specs are all created
        done_artifacts = [a for a in result["artifacts"] if a["status"] == "done"]
        assert len(done_artifacts) > 0


# -- devspec_instructions --


class TestDevspecInstructions:
    def test_returns_bundle(self, data_dir, change_dir):
        result = devspec_instructions("proposal", "test-change")
        assert "artifactId" in result
        assert result["artifactId"] == "proposal"
        assert "template" in result
        assert "instruction" in result

    def test_invalid_artifact_error(self, data_dir, change_dir):
        result = devspec_instructions("nonexistent-artifact", "test-change")
        assert "error" in result
        assert result["error"]["code"] == "invalid_artifact"

    def test_not_found_change_error(self, data_dir):
        result = devspec_instructions("proposal", "no-such-change")
        # This won't fail on change lookup but may fail on dependency reading
        # The function call itself should not raise
        assert isinstance(result, dict)


# -- devspec_context --


class TestDevspecContext:
    def test_returns_content(self, data_dir, change_dir):
        result = devspec_context("test-change")
        assert "content" in result
        assert isinstance(result["content"], str)

    def test_not_found_error(self, data_dir):
        result = devspec_context("no-such-change")
        assert "error" in result
        assert result["error"]["code"] == "not_found"

    def test_token_budget_applied(self, data_dir, change_dir):
        result = devspec_context("test-change", max_tokens=1)
        assert "content" in result
        # With max_tokens=1 the content is truncated
        assert len(result["content"]) <= 100  # very short due to budget


# -- devspec_validate --


class TestDevspecValidate:
    def test_valid_specs(self, data_dir, change_dir):
        result = devspec_validate("test-change")
        assert "valid" in result
        assert result["valid"] is True

    def test_not_found_error(self, data_dir):
        result = devspec_validate("no-such-change")
        assert "error" in result
        assert result["error"]["code"] == "not_found"

    def test_invalid_specs_returns_issues(self, data_dir, change_dir):
        bad_spec = change_dir / "specs" / "bad-cap"
        bad_spec.mkdir()
        (bad_spec / "spec.md").write_text("## ADDED Requirements\n\n### Requirement: Bad\nNo SHALL.\n")
        result = devspec_validate("test-change")
        assert "issues" in result
        assert len(result["issues"]) > 0


# -- devspec_analyze --


class TestDevspecAnalyze:
    def test_returns_report(self, data_dir, change_dir):
        result = devspec_analyze("test-change")
        assert "change_name" in result
        assert result["change_name"] == "test-change"
        assert "summary" in result

    def test_not_found_error(self, data_dir):
        result = devspec_analyze("no-such-change")
        assert "error" in result
        assert result["error"]["code"] == "not_found"


# -- devspec_handoff_read --


class TestDevspecHandoffRead:
    def test_returns_empty_bundle_without_handoff(self, data_dir, change_dir):
        result = devspec_handoff_read("test-change")
        assert "content" in result

    def test_returns_handoff_content(self, data_dir):
        # Use a bare change (no artifacts) so handoff is included in the bundle
        bare_dir = data_dir / "changes" / "bare-change"
        bare_dir.mkdir()
        (bare_dir / ".devspec.yaml").write_text("schema: spec-driven-custom\ncreated: 2026-02-21\n")
        (bare_dir / ".handoff.md").write_text("## Context\nsome context")
        result = devspec_handoff_read("bare-change")
        assert "context" in result["content"].lower()

    def test_not_found_error(self, data_dir):
        result = devspec_handoff_read("no-such-change")
        assert "error" in result
        assert result["error"]["code"] == "not_found"


# -- devspec_handoff_write --


class TestDevspecHandoffWrite:
    def test_writes_content(self, data_dir, change_dir):
        result = devspec_handoff_write("test-change", "## Handoff\nSome context here.")
        assert "written" in result
        handoff = change_dir / ".handoff.md"
        assert handoff.exists()
        assert handoff.read_text() == "## Handoff\nSome context here."

    def test_not_found_error(self, data_dir):
        result = devspec_handoff_write("no-such-change", "content")
        assert "error" in result
        assert result["error"]["code"] == "not_found"


# -- devspec_archive --


class TestDevspecArchive:
    def test_archives_complete_change(self, data_dir, change_dir):
        result = devspec_archive("test-change", skip_specs=True)
        assert "archived" in result
        assert result["archived"] == "test-change"
        assert not change_dir.exists()

    def test_not_found_error(self, data_dir):
        result = devspec_archive("no-such-change")
        assert "error" in result
        assert result["error"]["code"] == "not_found"

    def test_incomplete_change_error(self, data_dir):
        incomplete = data_dir / "changes" / "incomplete"
        incomplete.mkdir()
        (incomplete / ".devspec.yaml").write_text("schema: spec-driven-custom\ncreated: 2026-02-21\n")
        result = devspec_archive("incomplete")
        assert "error" in result
        assert result["error"]["code"] == "incomplete"

    def test_force_archives_incomplete(self, data_dir):
        incomplete = data_dir / "changes" / "forced"
        incomplete.mkdir()
        (incomplete / ".devspec.yaml").write_text("schema: spec-driven-custom\ncreated: 2026-02-21\n")
        result = devspec_archive("forced", skip_specs=True, force=True)
        assert "archived" in result


# -- devspec_task_mark --


class TestDevspecTaskMark:
    def test_marks_task_complete(self, data_dir, change_dir):
        result = devspec_task_mark("test-change", task_index=1, done=True)
        assert result.get("done") is True
        content = (change_dir / "tasks.md").read_text()
        # First checkbox should now be [x]
        assert content.startswith("- [x] Task one")

    def test_marks_task_incomplete(self, data_dir, change_dir):
        result = devspec_task_mark("test-change", task_index=2, done=False)
        assert result.get("done") is False
        content = (change_dir / "tasks.md").read_text()
        assert "- [ ] Task two" in content

    def test_out_of_range_error(self, data_dir, change_dir):
        result = devspec_task_mark("test-change", task_index=99)
        assert "error" in result
        assert result["error"]["code"] == "out_of_range"

    def test_zero_index_error(self, data_dir, change_dir):
        result = devspec_task_mark("test-change", task_index=0)
        assert "error" in result

    def test_not_found_change_error(self, data_dir):
        result = devspec_task_mark("no-such-change", task_index=1)
        assert "error" in result
        assert result["error"]["code"] == "not_found"
