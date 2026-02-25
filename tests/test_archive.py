import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from devspec.core.archive import archive_change
from devspec.core.instructions import generate_instructions

# -- archive_change tests --


def _make_complete_change(change_dir: Path) -> None:
    """Populate a change directory with all required artifacts."""
    (change_dir / "proposal.md").write_text("proposal content")
    (change_dir / "design.md").write_text("design content")
    (change_dir / "tasks.md").write_text("tasks content")
    specs = change_dir / "specs" / "cap"
    specs.mkdir(parents=True)
    (specs / "spec.md").write_text("spec content")


def test_archive_moves_to_dated_directory(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    _make_complete_change(change_dir)

    with patch("devspec.core.archive.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 1, 15)
        result = archive_change(tmp_project, "my-change", skip_specs=True)

    expected = tmp_project / "changes" / "archive" / "2026-01-15-my-change"
    assert result.archive_path == expected
    assert expected.exists()
    assert not change_dir.exists()
    assert (expected / "proposal.md").exists()


def test_archive_fails_if_change_missing(tmp_project: Path):
    with pytest.raises(FileNotFoundError, match="Change not found"):
        archive_change(tmp_project, "nonexistent", skip_specs=True)


def test_archive_appends_suffix_on_collision(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    _make_complete_change(change_dir)

    # Pre-create archive target to trigger collision
    target = tmp_project / "changes" / "archive" / "2026-01-15-my-change"
    target.mkdir(parents=True)

    with patch("devspec.core.archive.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 1, 15)
        result = archive_change(tmp_project, "my-change", skip_specs=True)

    expected = tmp_project / "changes" / "archive" / "2026-01-15-my-change-2"
    assert result.archive_path == expected
    assert expected.exists()


def test_archive_increments_suffix_on_multiple_collisions(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    _make_complete_change(change_dir)

    # Pre-create two archive targets
    archive_dir = tmp_project / "changes" / "archive"
    (archive_dir / "2026-01-15-my-change").mkdir(parents=True)
    (archive_dir / "2026-01-15-my-change-2").mkdir(parents=True)

    with patch("devspec.core.archive.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 1, 15)
        result = archive_change(tmp_project, "my-change", skip_specs=True)

    expected = tmp_project / "changes" / "archive" / "2026-01-15-my-change-3"
    assert result.archive_path == expected
    assert expected.exists()


def test_archive_skip_specs(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    _make_complete_change(change_dir)

    result = archive_change(tmp_project, "my-change", skip_specs=True)
    assert result.specs_synced is False
    assert result.archive_path.exists()


def test_archive_force_allows_incomplete(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    # Only create proposal -- incomplete
    (change_dir / "proposal.md").write_text("proposal content")

    result = archive_change(tmp_project, "my-change", skip_specs=True, force=True)
    assert result.archive_path.exists()


def test_archive_fails_incomplete_without_force(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    # Only create proposal -- incomplete
    (change_dir / "proposal.md").write_text("proposal content")

    with pytest.raises(ValueError, match="Incomplete artifacts"):
        archive_change(tmp_project, "my-change", skip_specs=True)


# -- generate_instructions tests --


def test_generate_instructions_basic(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)

    bundle = generate_instructions(tmp_project, "proposal", "my-change")
    assert bundle.artifact_id == "proposal"
    assert bundle.template != ""
    assert bundle.instruction != ""
    assert bundle.output_path == "proposal.md"
    assert bundle.dependencies == {}


def test_generate_instructions_reads_dependencies(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("My proposal content")

    bundle = generate_instructions(tmp_project, "design", "my-change")
    assert "proposal" in bundle.dependencies
    assert bundle.dependencies["proposal"] == "My proposal content"


def test_generate_instructions_unknown_artifact(tmp_project: Path):
    with pytest.raises(ValueError, match="Unknown artifact"):
        generate_instructions(tmp_project, "nonexistent", "my-change")


def test_generate_instructions_glob_output_path(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("proposal")

    bundle = generate_instructions(tmp_project, "specs", "my-change")
    assert bundle.output_path == "specs/"


def test_generate_instructions_reads_glob_dependencies(tmp_project: Path):
    change_dir = tmp_project / "changes" / "my-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("proposal")
    specs_dir = change_dir / "specs" / "auth"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("auth spec")
    specs_dir2 = change_dir / "specs" / "core"
    specs_dir2.mkdir(parents=True)
    (specs_dir2 / "spec.md").write_text("core spec")
    (change_dir / "design.md").write_text("design")

    bundle = generate_instructions(tmp_project, "tasks", "my-change")
    # tasks requires specs and design
    assert "design" in bundle.dependencies
    assert bundle.dependencies["design"] == "design"
    assert "specs" in bundle.dependencies
    # Glob deps are joined with ---
    assert "auth spec" in bundle.dependencies["specs"]
    assert "core spec" in bundle.dependencies["specs"]
