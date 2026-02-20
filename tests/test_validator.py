from pathlib import Path

from devspec.core.validator import (
    _contains_shall_or_must,
    _count_scenarios,
    _extract_requirement_text,
    validate_change_delta_specs,
    validate_spec_content,
)

# --- Helper ---


def _make_change_dir(tmp_path: Path, specs: dict[str, str]) -> Path:
    """Create a change directory with specs/{name}/spec.md for each entry."""
    change_dir = tmp_path / "change"
    change_dir.mkdir()
    specs_dir = change_dir / "specs"
    specs_dir.mkdir()
    for name, content in specs.items():
        spec_dir = specs_dir / name
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text(content)
    return change_dir


VALID_DELTA_SPEC = """\
## ADDED Requirements

### Requirement: Widget support
The system SHALL support widgets.

#### Scenario: Basic widget
- **WHEN** a widget is created
- **THEN** it exists
"""

VALID_MODIFIED_SPEC = """\
## MODIFIED Requirements

### Requirement: Widget support
The system SHALL support enhanced widgets.

#### Scenario: Enhanced widget
- **WHEN** a widget is enhanced
- **THEN** it is better
"""

VALID_REMOVED_SPEC = """\
## REMOVED Requirements

### Requirement: Old feature
"""

VALID_RENAMED_SPEC = """\
## RENAMED Requirements

- FROM: `### Requirement: Old name`
- TO: `### Requirement: New name`
"""


# --- Internal helper tests ---


class TestExtractRequirementText:
    def test_extracts_first_line(self):
        raw = "### Requirement: Foo\nThe system SHALL do X.\n\n#### Scenario: test\n"
        assert _extract_requirement_text(raw) == "The system SHALL do X."

    def test_skips_metadata(self):
        raw = "### Requirement: Foo\n**Status**: active\nThe system MUST do Y.\n"
        assert _extract_requirement_text(raw) == "The system MUST do Y."

    def test_returns_none_for_empty(self):
        raw = "### Requirement: Foo\n\n#### Scenario: test\n"
        assert _extract_requirement_text(raw) is None


class TestContainsShallOrMust:
    def test_shall(self):
        assert _contains_shall_or_must("The system SHALL do X.")

    def test_must(self):
        assert _contains_shall_or_must("The system MUST do X.")

    def test_neither(self):
        assert not _contains_shall_or_must("The system should do X.")

    def test_lowercase_no_match(self):
        assert not _contains_shall_or_must("The system shall do X.")


class TestCountScenarios:
    def test_counts_scenarios(self):
        raw = "### Requirement: Foo\nText\n#### Scenario: A\nStuff\n#### Scenario: B\nMore\n"
        assert _count_scenarios(raw) == 2

    def test_zero_scenarios(self):
        raw = "### Requirement: Foo\nText only\n"
        assert _count_scenarios(raw) == 0


# --- validate_change_delta_specs ---


class TestValidateChangeDeltaSpecs:
    def test_valid_delta_spec_passes(self, tmp_path):
        change_dir = _make_change_dir(tmp_path, {"my-cap": VALID_DELTA_SPEC})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is True
        assert report.summary["errors"] == 0

    def test_missing_shall_or_must_fails(self, tmp_path):
        bad_spec = """\
## ADDED Requirements

### Requirement: Widget support
The system supports widgets.

#### Scenario: Basic widget
- **WHEN** a widget is created
- **THEN** it exists
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("SHALL or MUST" in i.message for i in report.issues)

    def test_missing_scenario_fails(self, tmp_path):
        bad_spec = """\
## ADDED Requirements

### Requirement: Widget support
The system SHALL support widgets.
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("scenario" in i.message for i in report.issues)

    def test_duplicate_removed_fails(self, tmp_path):
        bad_spec = """\
## REMOVED Requirements

### Requirement: Old feature
### Requirement: Old feature
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("Duplicate removal" in i.message for i in report.issues)

    def test_cross_section_modified_removed_conflict(self, tmp_path):
        bad_spec = """\
## MODIFIED Requirements

### Requirement: Widget support
The system SHALL support enhanced widgets.

#### Scenario: Enhanced widget
- **WHEN** a widget is enhanced
- **THEN** it is better

## REMOVED Requirements

### Requirement: Widget support
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("MODIFIED and REMOVED" in i.message for i in report.issues)

    def test_cross_section_added_removed_conflict(self, tmp_path):
        bad_spec = """\
## ADDED Requirements

### Requirement: Widget support
The system SHALL support widgets.

#### Scenario: Basic widget
- **WHEN** a widget is created
- **THEN** it exists

## REMOVED Requirements

### Requirement: Widget support
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("ADDED and REMOVED" in i.message for i in report.issues)

    def test_empty_delta_spec_fails(self, tmp_path):
        empty_spec = "## Overview\n\nJust some text with no delta sections.\n"
        change_dir = _make_change_dir(tmp_path, {"my-cap": empty_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("No deltas found" in i.message for i in report.issues)

    def test_section_header_with_no_entries(self, tmp_path):
        bad_spec = """\
## ADDED Requirements

Some preamble text but no ### Requirement: headers.
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": bad_spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("section header present but no requirement entries" in i.message for i in report.issues)

    def test_no_specs_directory(self, tmp_path):
        change_dir = tmp_path / "change"
        change_dir.mkdir()
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("No specs/ directory" in i.message for i in report.issues)

    def test_missing_spec_md(self, tmp_path):
        change_dir = tmp_path / "change"
        change_dir.mkdir()
        specs_dir = change_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "my-cap").mkdir()
        # No spec.md inside
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("Missing spec.md" in i.message for i in report.issues)

    def test_multiple_specs_all_valid(self, tmp_path):
        change_dir = _make_change_dir(
            tmp_path,
            {
                "cap-one": VALID_DELTA_SPEC,
                "cap-two": VALID_MODIFIED_SPEC,
            },
        )
        report = validate_change_delta_specs(change_dir)
        assert report.valid is True

    def test_renamed_interplay_modified_old_name(self, tmp_path):
        """MODIFIED referencing old name when RENAMED exists should warn."""
        spec = """\
## MODIFIED Requirements

### Requirement: Old name
The system SHALL do something new.

#### Scenario: Test
- **WHEN** something happens
- **THEN** it works

## RENAMED Requirements

- FROM: `### Requirement: Old name`
- TO: `### Requirement: New name`
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": spec})
        report = validate_change_delta_specs(change_dir)
        # Should have a warning about old name in MODIFIED
        warnings = [i for i in report.issues if i.level == "WARNING"]
        assert any("old name" in i.message for i in warnings)

    def test_renamed_to_collides_with_added(self, tmp_path):
        """RENAMED TO name that conflicts with an ADDED requirement should error."""
        spec = """\
## ADDED Requirements

### Requirement: New name
The system SHALL support the new name.

#### Scenario: Test
- **WHEN** something happens
- **THEN** it works

## RENAMED Requirements

- FROM: `### Requirement: Old name`
- TO: `### Requirement: New name`
"""
        change_dir = _make_change_dir(tmp_path, {"my-cap": spec})
        report = validate_change_delta_specs(change_dir)
        assert report.valid is False
        assert any("conflicts with ADDED" in i.message for i in report.issues)


# --- validate_spec_content ---


class TestValidateSpecContent:
    def test_valid_content_passes(self):
        content = """\
## Requirements

### Requirement: Widget support
The system SHALL support widgets.

#### Scenario: Basic widget
- **WHEN** a widget is created
- **THEN** it exists
"""
        report = validate_spec_content("test-spec", content)
        assert report.valid is True
        assert report.summary["errors"] == 0

    def test_missing_requirements_section(self):
        content = "## Overview\n\nSome text.\n"
        report = validate_spec_content("test-spec", content)
        assert report.valid is False
        assert any("Missing '## Requirements'" in i.message for i in report.issues)

    def test_missing_shall_or_must(self):
        content = """\
## Requirements

### Requirement: Widget support
The system supports widgets.

#### Scenario: Basic widget
- **WHEN** a widget is created
- **THEN** it exists
"""
        report = validate_spec_content("test-spec", content)
        assert report.valid is False
        assert any("SHALL or MUST" in i.message for i in report.issues)

    def test_missing_scenarios(self):
        content = """\
## Requirements

### Requirement: Widget support
The system SHALL support widgets.
"""
        report = validate_spec_content("test-spec", content)
        assert report.valid is False
        assert any("scenario" in i.message for i in report.issues)

    def test_multiple_requirements_mixed_validity(self):
        content = """\
## Requirements

### Requirement: Good one
The system SHALL work well.

#### Scenario: Test
- **WHEN** it runs
- **THEN** it passes

### Requirement: Bad one
This one has no keyword.

#### Scenario: Test
- **WHEN** it runs
- **THEN** it fails
"""
        report = validate_spec_content("test-spec", content)
        assert report.valid is False
        assert report.summary["errors"] == 1
        assert any("Bad one" in i.message for i in report.issues)


# --- Real archive integration test ---


class TestRealArchive:
    def test_real_delta_spec_passes(self, real_archive_dir):
        """Validate a real archived spec.md passes validation."""
        # Find first available change directory with specs
        found = False
        for change_dir in sorted(real_archive_dir.iterdir()):
            if not change_dir.is_dir():
                continue
            specs_dir = change_dir / "specs"
            if not specs_dir.is_dir():
                continue
            # Check there's at least one spec
            spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir() and (d / "spec.md").exists()]
            if not spec_dirs:
                continue

            report = validate_change_delta_specs(change_dir)
            assert report.valid is True, f"Real spec at {change_dir} failed validation: " + "; ".join(
                f"[{i.level}] {i.path}: {i.message}" for i in report.issues
            )
            found = True
            break

        assert found, "No valid real spec found in archive"
