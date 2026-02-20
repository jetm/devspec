from pathlib import Path

import pytest

from devspec.core.spec_merge import (
    ApplyResult,
    MergeCounts,
    SpecUpdate,
    apply_specs,
    build_spec_skeleton,
    build_updated_spec,
    find_spec_updates,
)

# --- Helpers ---


def _make_delta_spec(
    *,
    added: list[tuple[str, str]] | None = None,
    modified: list[tuple[str, str]] | None = None,
    removed: list[str] | None = None,
    renamed: list[tuple[str, str]] | None = None,
) -> str:
    """Build a delta spec markdown string from components."""
    sections: list[str] = []
    if added:
        lines = ["## ADDED Requirements", ""]
        for name, body in added:
            lines.append(f"### Requirement: {name}")
            lines.append(body)
            lines.append("")
        sections.append("\n".join(lines))
    if modified:
        lines = ["## MODIFIED Requirements", ""]
        for name, body in modified:
            lines.append(f"### Requirement: {name}")
            lines.append(body)
            lines.append("")
        sections.append("\n".join(lines))
    if removed:
        lines = ["## REMOVED Requirements", ""]
        for name in removed:
            lines.append(f"### Requirement: {name}")
            lines.append("")
        sections.append("\n".join(lines))
    if renamed:
        lines = ["## RENAMED Requirements", ""]
        for from_name, to_name in renamed:
            lines.append(f"FROM: `### Requirement: {from_name}`")
            lines.append(f"TO: `### Requirement: {to_name}`")
            lines.append("")
        sections.append("\n".join(lines))
    return "\n".join(sections)


def _make_main_spec(name: str, requirements: list[tuple[str, str]]) -> str:
    """Build a main spec markdown string."""
    lines = [f"# {name} Specification", "", "## Purpose", "Test spec.", "", "## Requirements", ""]
    for req_name, body in requirements:
        lines.append(f"### Requirement: {req_name}")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def _write_update(tmp_path: Path, delta_content: str, main_content: str | None = None) -> SpecUpdate:
    """Set up a SpecUpdate with files on disk."""
    cap_name = "test-cap"
    source_dir = tmp_path / "change" / "specs" / cap_name
    source_dir.mkdir(parents=True)
    source = source_dir / "spec.md"
    source.write_text(delta_content)

    target_dir = tmp_path / "main" / cap_name
    target_dir.mkdir(parents=True)
    target = target_dir / "spec.md"
    exists = False
    if main_content is not None:
        target.write_text(main_content)
        exists = True

    return SpecUpdate(source=source, target=target, exists=exists)


# --- find_spec_updates ---


class TestFindSpecUpdates:
    def test_discovers_delta_specs(self, tmp_path: Path):
        change_dir = tmp_path / "change"
        main_dir = tmp_path / "main"
        main_dir.mkdir()

        # Create two delta specs
        for name in ["cap-a", "cap-b"]:
            spec_dir = change_dir / "specs" / name
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text("## ADDED Requirements\n")

        # Create existing main spec for cap-a only
        (main_dir / "cap-a").mkdir()
        (main_dir / "cap-a" / "spec.md").write_text("existing")

        updates = find_spec_updates(change_dir, main_dir)

        assert len(updates) == 2
        names = {u.source.parent.name for u in updates}
        assert names == {"cap-a", "cap-b"}

        cap_a = next(u for u in updates if u.source.parent.name == "cap-a")
        cap_b = next(u for u in updates if u.source.parent.name == "cap-b")
        assert cap_a.exists is True
        assert cap_b.exists is False

    def test_no_specs_dir(self, tmp_path: Path):
        change_dir = tmp_path / "change"
        change_dir.mkdir()
        main_dir = tmp_path / "main"
        main_dir.mkdir()

        updates = find_spec_updates(change_dir, main_dir)
        assert updates == []

    def test_ignores_files_in_specs_dir(self, tmp_path: Path):
        change_dir = tmp_path / "change"
        specs_dir = change_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "README.md").write_text("ignore me")

        main_dir = tmp_path / "main"
        main_dir.mkdir()

        updates = find_spec_updates(change_dir, main_dir)
        assert updates == []


# --- build_spec_skeleton ---


class TestBuildSpecSkeleton:
    def test_generates_skeleton(self):
        result = build_spec_skeleton("my-feature", "test-change")
        assert "# my-feature Specification" in result
        assert "created by archiving change test-change" in result
        assert "## Requirements" in result


# --- build_updated_spec: ADDED only (new spec) ---


class TestBuildUpdatedSpecAdded:
    def test_added_to_new_spec(self, tmp_path: Path):
        delta = _make_delta_spec(added=[("Feature A", "The system SHALL do A.")])
        update = _write_update(tmp_path, delta)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts.added == 1
        assert counts.modified == 0
        assert "### Requirement: Feature A" in rebuilt
        assert "The system SHALL do A." in rebuilt
        assert "## Requirements" in rebuilt

    def test_multiple_added_to_new_spec(self, tmp_path: Path):
        delta = _make_delta_spec(
            added=[
                ("Feature A", "The system SHALL do A."),
                ("Feature B", "The system SHALL do B."),
            ]
        )
        update = _write_update(tmp_path, delta)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts.added == 2
        assert "### Requirement: Feature A" in rebuilt
        assert "### Requirement: Feature B" in rebuilt


# --- build_updated_spec: MODIFIED ---


class TestBuildUpdatedSpecModified:
    def test_modified_existing_requirement(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Old body.")])
        delta = _make_delta_spec(modified=[("Feature A", "New body.")])
        update = _write_update(tmp_path, delta, main)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts.modified == 1
        assert "New body." in rebuilt
        assert "Old body." not in rebuilt

    def test_modified_not_found(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = _make_delta_spec(modified=[("Nonexistent", "New body.")])
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="MODIFIED not found"):
            build_updated_spec(update, "test-change")


# --- build_updated_spec: REMOVED ---


class TestBuildUpdatedSpecRemoved:
    def test_removed_existing_requirement(self, tmp_path: Path):
        main = _make_main_spec(
            "test-cap",
            [("Feature A", "Body A."), ("Feature B", "Body B.")],
        )
        delta = _make_delta_spec(removed=["Feature A"])
        update = _write_update(tmp_path, delta, main)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts.removed == 1
        assert "### Requirement: Feature A" not in rebuilt
        assert "### Requirement: Feature B" in rebuilt

    def test_removed_not_found(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = _make_delta_spec(removed=["Nonexistent"])
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="REMOVED not found"):
            build_updated_spec(update, "test-change")


# --- build_updated_spec: RENAMED ---


class TestBuildUpdatedSpecRenamed:
    def test_renamed_requirement(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Old Name", "Body content.")])
        delta = _make_delta_spec(renamed=[("Old Name", "New Name")])
        update = _write_update(tmp_path, delta, main)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts.renamed == 1
        assert "### Requirement: New Name" in rebuilt
        assert "### Requirement: Old Name" not in rebuilt
        assert "Body content." in rebuilt

    def test_renamed_source_not_found(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = _make_delta_spec(renamed=[("Nonexistent", "New Name")])
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="RENAMED source not found"):
            build_updated_spec(update, "test-change")

    def test_renamed_target_already_exists(self, tmp_path: Path):
        main = _make_main_spec(
            "test-cap",
            [("Feature A", "Body A."), ("Feature B", "Body B.")],
        )
        delta = _make_delta_spec(renamed=[("Feature A", "Feature B")])
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="RENAMED target already exists"):
            build_updated_spec(update, "test-change")


# --- build_updated_spec: all 4 operations combined ---


class TestBuildUpdatedSpecCombined:
    def test_all_operations(self, tmp_path: Path):
        main = _make_main_spec(
            "test-cap",
            [
                ("Keep This", "Unchanged."),
                ("Rename Me", "Rename body."),
                ("Remove Me", "Remove body."),
                ("Modify Me", "Old modify body."),
            ],
        )
        delta = _make_delta_spec(
            added=[("Brand New", "Added body.")],
            modified=[("Modify Me", "New modify body.")],
            removed=["Remove Me"],
            renamed=[("Rename Me", "Renamed Thing")],
        )
        update = _write_update(tmp_path, delta, main)

        rebuilt, counts = build_updated_spec(update, "test-change")

        assert counts == MergeCounts(added=1, modified=1, removed=1, renamed=1)
        assert "### Requirement: Keep This" in rebuilt
        assert "### Requirement: Renamed Thing" in rebuilt
        assert "### Requirement: Remove Me" not in rebuilt
        assert "New modify body." in rebuilt
        assert "Old modify body." not in rebuilt
        assert "### Requirement: Brand New" in rebuilt

        # Verify ordering: original-order blocks first, then renamed/added appended
        # "Rename Me" was renamed so its original slot is gone; it appears after kept blocks
        keep_pos = rebuilt.index("Keep This")
        modify_pos = rebuilt.index("Modify Me")
        renamed_pos = rebuilt.index("Renamed Thing")
        new_pos = rebuilt.index("Brand New")
        assert keep_pos < modify_pos < renamed_pos < new_pos


# --- Cross-section conflict detection ---


class TestCrossSectionConflicts:
    def test_modified_and_removed(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = _make_delta_spec(
            modified=[("Feature A", "New body.")],
            removed=["Feature A"],
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="requirement in both MODIFIED and REMOVED"):
            build_updated_spec(update, "test-change")

    def test_added_and_removed(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Existing", "Body.")])
        delta = _make_delta_spec(
            added=[("Feature A", "New body.")],
            removed=["Feature A"],
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="requirement in both ADDED and REMOVED"):
            build_updated_spec(update, "test-change")

    def test_modified_and_added(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = _make_delta_spec(
            added=[("Feature A", "Added body.")],
            modified=[("Feature A", "Modified body.")],
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="requirement in both MODIFIED and ADDED"):
            build_updated_spec(update, "test-change")


# --- Duplicate detection within sections ---


class TestDuplicateDetection:
    def test_duplicate_in_added(self, tmp_path: Path):
        delta = "## ADDED Requirements\n\n### Requirement: Feature A\nBody 1.\n\n### Requirement: Feature A\nBody 2.\n"
        update = _write_update(tmp_path, delta)

        with pytest.raises(ValueError, match="duplicate in ADDED"):
            build_updated_spec(update, "test-change")

    def test_duplicate_in_modified(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = (
            "## MODIFIED Requirements\n\n### Requirement: Feature A\nBody 1.\n\n### Requirement: Feature A\nBody 2.\n"
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="duplicate in MODIFIED"):
            build_updated_spec(update, "test-change")

    def test_duplicate_in_removed(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = "## REMOVED Requirements\n\n### Requirement: Feature A\n\n### Requirement: Feature A\n"
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="duplicate in REMOVED"):
            build_updated_spec(update, "test-change")

    def test_duplicate_from_in_renamed(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Feature A", "Body.")])
        delta = (
            "## RENAMED Requirements\n\n"
            "FROM: `### Requirement: Feature A`\n"
            "TO: `### Requirement: Feature B`\n\n"
            "FROM: `### Requirement: Feature A`\n"
            "TO: `### Requirement: Feature C`\n"
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="duplicate FROM in RENAMED"):
            build_updated_spec(update, "test-change")

    def test_duplicate_to_in_renamed(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("A", "Body A."), ("B", "Body B.")])
        delta = (
            "## RENAMED Requirements\n\n"
            "FROM: `### Requirement: A`\n"
            "TO: `### Requirement: C`\n\n"
            "FROM: `### Requirement: B`\n"
            "TO: `### Requirement: C`\n"
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match="duplicate TO in RENAMED"):
            build_updated_spec(update, "test-change")


# --- RENAMED interplay ---


class TestRenamedInterplay:
    def test_modified_must_reference_new_name(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Old Name", "Body.")])
        delta = _make_delta_spec(
            renamed=[("Old Name", "New Name")],
            modified=[("Old Name", "Updated body.")],
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match='MODIFIED must reference NEW header "New Name"'):
            build_updated_spec(update, "test-change")

    def test_renamed_to_collides_with_added(self, tmp_path: Path):
        main = _make_main_spec("test-cap", [("Old Name", "Body.")])
        delta = _make_delta_spec(
            renamed=[("Old Name", "New Name")],
            added=[("New Name", "Added body.")],
        )
        update = _write_update(tmp_path, delta, main)

        with pytest.raises(ValueError, match='RENAMED TO collides with ADDED for "New Name"'):
            build_updated_spec(update, "test-change")


# --- New spec with MODIFIED/RENAMED ---


class TestNewSpecRestrictions:
    def test_new_spec_with_modified_raises(self, tmp_path: Path):
        delta = _make_delta_spec(modified=[("Feature A", "Body.")])
        update = _write_update(tmp_path, delta)

        with pytest.raises(ValueError, match="target does not exist; only ADDED allowed"):
            build_updated_spec(update, "test-change")

    def test_new_spec_with_renamed_raises(self, tmp_path: Path):
        delta = _make_delta_spec(renamed=[("Old", "New")])
        update = _write_update(tmp_path, delta)

        with pytest.raises(ValueError, match="target does not exist; only ADDED allowed"):
            build_updated_spec(update, "test-change")


# --- No operations ---


class TestNoOperations:
    def test_empty_delta_raises(self, tmp_path: Path):
        delta = "## Some Section\n\nNo operations here.\n"
        update = _write_update(tmp_path, delta)

        with pytest.raises(ValueError, match="no operations found"):
            build_updated_spec(update, "test-change")


# --- apply_specs ---


class TestApplySpecs:
    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a project with openspec structure and a delta spec."""
        project = tmp_path / "project"
        change_dir = project / "openspec" / "changes" / "test-change" / "specs" / "my-cap"
        change_dir.mkdir(parents=True)
        (change_dir / "spec.md").write_text(_make_delta_spec(added=[("Feature X", "The system SHALL do X.")]))
        (project / "openspec" / "specs").mkdir(parents=True)
        return project

    def test_dry_run_does_not_write(self, tmp_path: Path):
        project = self._setup_project(tmp_path)

        result = apply_specs(project, "test-change", dry_run=True)

        assert isinstance(result, ApplyResult)
        assert result.change_name == "test-change"
        assert result.totals.added == 1
        assert not result.no_changes
        # Target should NOT exist
        target = project / "openspec" / "specs" / "my-cap" / "spec.md"
        assert not target.exists()

    def test_writes_files(self, tmp_path: Path):
        project = self._setup_project(tmp_path)

        result = apply_specs(project, "test-change")

        assert result.totals.added == 1
        target = project / "openspec" / "specs" / "my-cap" / "spec.md"
        assert target.is_file()
        content = target.read_text()
        assert "### Requirement: Feature X" in content

    def test_no_specs_returns_no_changes(self, tmp_path: Path):
        project = tmp_path / "project"
        change_dir = project / "openspec" / "changes" / "empty-change"
        change_dir.mkdir(parents=True)

        result = apply_specs(project, "empty-change")

        assert result.no_changes is True

    def test_change_not_found_raises(self, tmp_path: Path):
        project = tmp_path / "project"
        (project / "openspec" / "changes").mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            apply_specs(project, "nonexistent")

    def test_modifies_existing_spec(self, tmp_path: Path):
        project = tmp_path / "project"
        main_cap = project / "openspec" / "specs" / "my-cap"
        main_cap.mkdir(parents=True)
        (main_cap / "spec.md").write_text(_make_main_spec("my-cap", [("Feature A", "Old body.")]))

        change_dir = project / "openspec" / "changes" / "mod-change" / "specs" / "my-cap"
        change_dir.mkdir(parents=True)
        (change_dir / "spec.md").write_text(_make_delta_spec(modified=[("Feature A", "New body.")]))

        result = apply_specs(project, "mod-change")

        assert result.totals.modified == 1
        content = (main_cap / "spec.md").read_text()
        assert "New body." in content
        assert "Old body." not in content


# --- Real archive integration test ---


class TestRealArchiveFixtures:
    def test_with_real_archived_change(self, real_archive_dir: Path, tmp_path: Path):
        """Test using real delta spec content from the archive against a synthetic main spec.

        We read the real delta from the systemd-daemon-reload-hook change
        (which MODIFIES 'Chezmoi PostToolUse hook') and construct a main spec
        with a ## Requirements header containing that requirement.
        """
        change_dir = real_archive_dir / "2026-02-16-systemd-daemon-reload-hook"
        if not change_dir.is_dir():
            pytest.skip("Expected change not available")

        delta_source = change_dir / "specs" / "claude-code-hooks" / "spec.md"
        if not delta_source.is_file():
            pytest.skip("Delta spec file not available")

        # Read the real delta content
        delta_content = delta_source.read_text()

        # Build a synthetic main spec with the requirement that will be modified
        main_content = (
            "# claude-code-hooks Specification\n\n"
            "## Purpose\nHook framework for Claude Code.\n\n"
            "## Requirements\n\n"
            "### Requirement: Chezmoi PostToolUse hook\n"
            "Old content that will be replaced by the delta.\n\n"
            "### Requirement: Another hook\n"
            "This requirement should survive the merge.\n"
        )

        # Write files to tmp_path and build SpecUpdate
        cap_dir = tmp_path / "change" / "specs" / "claude-code-hooks"
        cap_dir.mkdir(parents=True)
        (cap_dir / "spec.md").write_text(delta_content)

        target_dir = tmp_path / "main" / "claude-code-hooks"
        target_dir.mkdir(parents=True)
        (target_dir / "spec.md").write_text(main_content)

        update = SpecUpdate(
            source=cap_dir / "spec.md",
            target=target_dir / "spec.md",
            exists=True,
        )
        rebuilt, counts = build_updated_spec(update, "2026-02-16-systemd-daemon-reload-hook")

        # The delta modifies "Chezmoi PostToolUse hook"
        assert counts.modified == 1
        assert "### Requirement: Chezmoi PostToolUse hook" in rebuilt
        # The unmodified requirement should still be present
        assert "### Requirement: Another hook" in rebuilt
        # Old content should be replaced
        assert "Old content that will be replaced" not in rebuilt
        # New content from delta should be present
        assert "systemd" in rebuilt.lower() or "daemon-reload" in rebuilt.lower()
