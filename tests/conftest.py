from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project data directory with devspec global store layout.

    Returns the data_dir path (equivalent to <data_root>/<project>/).
    """
    data_dir = tmp_path / "data_dir"
    data_dir.mkdir()
    (data_dir / "specs").mkdir()
    (data_dir / "changes").mkdir()
    (data_dir / "changes" / "archive").mkdir()
    return data_dir


@pytest.fixture
def sample_schema_yaml():
    """Return the spec-driven-custom schema as a string."""
    schema_file = Path(__file__).parent.parent / "src" / "devspec" / "data" / "schema.yaml"
    return schema_file.read_text()


@pytest.fixture
def sample_change(tmp_project):
    """Create a sample change directory with basic artifacts."""
    change_dir = tmp_project / "changes" / "test-change"
    change_dir.mkdir()
    (change_dir / ".devspec.yaml").write_text("schema: spec-driven-custom\ncreated: 2026-02-19\n")
    (change_dir / "proposal.md").write_text(
        "## Why\n\nTest motivation.\n\n## What Changes\n\n- Add test feature\n\n"
        "## Capabilities\n\n### New Capabilities\n- `test-cap`: Test capability\n\n"
        "### Modified Capabilities\n\n## Impact\n\n- tests/\n"
    )
    specs_dir = change_dir / "specs" / "test-cap"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Test feature support\n"
        "The system SHALL support test features.\n\n"
        "#### Scenario: Basic test\n"
        "- **WHEN** a test runs\n"
        "- **THEN** it passes\n"
    )
    return change_dir


@pytest.fixture
def real_archive_dir():
    """Path to real archived changes for integration testing."""
    archive = Path.home() / "repos" / "personal" / "claude.md" / "openspec" / "changes" / "archive"
    if not archive.exists():
        pytest.skip("Real archive not available")
    return archive
