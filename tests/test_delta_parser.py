from pathlib import Path

import pytest

from devspec.core.delta_parser import (
    extract_requirements_section,
    normalize_requirement_name,
    parse_delta_spec,
)

# --- normalize_requirement_name ---


class TestNormalizeRequirementName:
    def test_strips_whitespace(self):
        assert normalize_requirement_name("  foo  ") == "foo"

    def test_preserves_inner_spaces(self):
        assert normalize_requirement_name("  foo bar  ") == "foo bar"

    def test_empty_string(self):
        assert normalize_requirement_name("") == ""


# --- extract_requirements_section ---


class TestExtractRequirementsSection:
    def test_with_existing_section(self):
        content = """\
## Overview

Some overview text.

## Requirements

Preamble text here.

### Requirement: First thing
The system SHALL do first thing.

### Requirement: Second thing
The system SHALL do second thing.

## Other Section

Other content."""
        result = extract_requirements_section(content)
        assert result.header_line == "## Requirements"
        assert result.preamble == "\nPreamble text here."
        assert len(result.body_blocks) == 2
        assert result.body_blocks[0].name == "First thing"
        assert result.body_blocks[1].name == "Second thing"
        assert "Other content." in result.after

    def test_no_requirements_section(self):
        content = "Some content without requirements."
        result = extract_requirements_section(content)
        assert result.header_line == "## Requirements"
        assert result.preamble == ""
        assert result.body_blocks == []
        assert result.before == "Some content without requirements.\n\n"
        assert result.after == "\n"

    def test_empty_content(self):
        result = extract_requirements_section("")
        assert result.header_line == "## Requirements"
        assert result.before == ""
        assert result.preamble == ""
        assert result.body_blocks == []

    def test_requirements_at_end_of_file(self):
        content = """\
## Requirements

### Requirement: Only one
The system SHALL do something."""
        result = extract_requirements_section(content)
        assert result.header_line == "## Requirements"
        assert len(result.body_blocks) == 1
        assert result.body_blocks[0].name == "Only one"
        assert result.body_blocks[0].raw == "### Requirement: Only one\nThe system SHALL do something."

    def test_multiple_requirements_no_preamble(self):
        content = """\
## Requirements

### Requirement: Alpha
Alpha body.

### Requirement: Beta
Beta body.

### Requirement: Gamma
Gamma body."""
        result = extract_requirements_section(content)
        assert len(result.body_blocks) == 3
        assert [b.name for b in result.body_blocks] == ["Alpha", "Beta", "Gamma"]

    def test_before_section_preserved(self):
        content = """\
# Title

Intro paragraph.

## Requirements

### Requirement: Foo
Foo body."""
        result = extract_requirements_section(content)
        assert "# Title" in result.before
        assert "Intro paragraph." in result.before


# --- parse_delta_spec ---


class TestParseDeltaSpec:
    def test_added_only(self):
        content = """\
## ADDED Requirements

### Requirement: New feature
The system SHALL support the new feature.

#### Scenario: Basic usage
- **WHEN** a user activates the feature
- **THEN** it works"""
        result = parse_delta_spec(content)
        assert result.section_presence.added is True
        assert result.section_presence.modified is False
        assert result.section_presence.removed is False
        assert result.section_presence.renamed is False
        assert len(result.added) == 1
        assert result.added[0].name == "New feature"
        assert "#### Scenario: Basic usage" in result.added[0].raw

    def test_all_four_sections(self):
        content = """\
## ADDED Requirements

### Requirement: Brand new thing
Added body.

## MODIFIED Requirements

### Requirement: Existing thing
Modified body with changes.

## REMOVED Requirements

### Requirement: Old thing
### Requirement: Another old thing

## RENAMED Requirements

- FROM: `### Requirement: Old name`
- TO: `### Requirement: New name`"""
        result = parse_delta_spec(content)

        assert result.section_presence.added is True
        assert result.section_presence.modified is True
        assert result.section_presence.removed is True
        assert result.section_presence.renamed is True

        assert len(result.added) == 1
        assert result.added[0].name == "Brand new thing"

        assert len(result.modified) == 1
        assert result.modified[0].name == "Existing thing"

        assert result.removed == ["Old thing", "Another old thing"]

        assert len(result.renamed) == 1
        assert result.renamed[0].from_name == "Old name"
        assert result.renamed[0].to_name == "New name"

    def test_empty_content(self):
        result = parse_delta_spec("")
        assert result.added == []
        assert result.modified == []
        assert result.removed == []
        assert result.renamed == []
        assert result.section_presence.added is False

    def test_removed_bullet_list_format(self):
        content = """\
## REMOVED Requirements

- `### Requirement: First removed`
- `### Requirement: Second removed`
- `### Requirement: Third removed`"""
        result = parse_delta_spec(content)
        assert result.removed == ["First removed", "Second removed", "Third removed"]

    def test_removed_mixed_formats(self):
        content = """\
## REMOVED Requirements

### Requirement: Header format
- `### Requirement: Bullet format`"""
        result = parse_delta_spec(content)
        assert result.removed == ["Header format", "Bullet format"]

    def test_renamed_backtick_wrapped(self):
        content = """\
## RENAMED Requirements

- FROM: `### Requirement: Old A`
- TO: `### Requirement: New A`
- FROM: `### Requirement: Old B`
- TO: `### Requirement: New B`"""
        result = parse_delta_spec(content)
        assert len(result.renamed) == 2
        assert result.renamed[0].from_name == "Old A"
        assert result.renamed[0].to_name == "New A"
        assert result.renamed[1].from_name == "Old B"
        assert result.renamed[1].to_name == "New B"

    def test_renamed_without_backticks(self):
        content = """\
## RENAMED Requirements

FROM: ### Requirement: Plain old
TO: ### Requirement: Plain new"""
        result = parse_delta_spec(content)
        assert len(result.renamed) == 1
        assert result.renamed[0].from_name == "Plain old"
        assert result.renamed[0].to_name == "Plain new"

    def test_multiple_requirements_in_added(self):
        content = """\
## ADDED Requirements

### Requirement: First
First body line 1.
First body line 2.

### Requirement: Second
Second body.

### Requirement: Third
Third body."""
        result = parse_delta_spec(content)
        assert len(result.added) == 3
        assert result.added[0].name == "First"
        assert "First body line 1." in result.added[0].raw
        assert "First body line 2." in result.added[0].raw
        assert result.added[1].name == "Second"
        assert result.added[2].name == "Third"

    def test_case_insensitive_section_headers(self):
        content = """\
## Added Requirements

### Requirement: Case test
Body."""
        result = parse_delta_spec(content)
        assert result.section_presence.added is True
        assert len(result.added) == 1

    def test_crlf_line_endings(self):
        content = "## ADDED Requirements\r\n\r\n### Requirement: CRLF test\r\nBody with CRLF.\r\n"
        result = parse_delta_spec(content)
        assert len(result.added) == 1
        assert result.added[0].name == "CRLF test"


# --- Real archive integration tests ---


class TestRealArchiveSpecs:
    """Tests using real delta spec files from the openspec archive."""

    ARCHIVE_DIR = Path.home() / "repos" / "personal" / "claude.md" / "openspec" / "changes" / "archive"

    @pytest.fixture(autouse=True)
    def _check_archive(self):
        if not self.ARCHIVE_DIR.exists():
            pytest.skip("Real archive not available")

    def test_real_added_only_spec(self):
        """Parse the claude-code-hooks spec (ADDED only)."""
        spec_file = self.ARCHIVE_DIR / "2026-02-15-extract-rules-to-hooks" / "specs" / "claude-code-hooks" / "spec.md"
        if not spec_file.exists():
            pytest.skip(f"Spec file not found: {spec_file}")

        content = spec_file.read_text()
        result = parse_delta_spec(content)

        assert result.section_presence.added is True
        assert result.section_presence.modified is False
        assert result.section_presence.removed is False
        assert len(result.added) >= 7
        names = [b.name for b in result.added]
        assert "Chezmoi PostToolUse hook" in names
        assert "All hooks are non-blocking" in names

    def test_real_modified_spec(self):
        """Parse the rule-composition spec (MODIFIED only)."""
        spec_file = self.ARCHIVE_DIR / "2026-02-15-extract-rules-to-hooks" / "specs" / "rule-composition" / "spec.md"
        if not spec_file.exists():
            pytest.skip(f"Spec file not found: {spec_file}")

        content = spec_file.read_text()
        result = parse_delta_spec(content)

        assert result.section_presence.modified is True
        assert len(result.modified) >= 1
        names = [b.name for b in result.modified]
        assert "Initial rule files" in names

    def test_real_removed_spec(self):
        """Parse the gitlab-mcp-server spec (REMOVED only)."""
        spec_file = self.ARCHIVE_DIR / "2026-02-17-add-gitlab-rules" / "specs" / "gitlab-mcp-server" / "spec.md"
        if not spec_file.exists():
            pytest.skip(f"Spec file not found: {spec_file}")

        content = spec_file.read_text()
        result = parse_delta_spec(content)

        assert result.section_presence.removed is True
        assert len(result.removed) == 3
        assert "GitLab MCP server configuration exists in ~/.claude.json" in result.removed
        assert "GITLAB_TOKEN authentication" in result.removed

    def test_real_renamed_spec(self):
        """Parse the rename spec (RENAMED only)."""
        spec_file = self.ARCHIVE_DIR / "2026-02-18-rename-tooling-to-devtool" / "specs" / "rename" / "spec.md"
        if not spec_file.exists():
            pytest.skip(f"Spec file not found: {spec_file}")

        content = spec_file.read_text()
        result = parse_delta_spec(content)

        assert result.section_presence.renamed is True
        # This spec uses a non-standard format (no FROM:/TO: prefix),
        # so renamed parsing via FROM/TO regex may not match.
        # The important thing is the section was detected.
