import pytest

from devspec.core.handoff import (
    HANDOFF_FILE,
    build_context,
    read_handoff,
    read_handoff_bundle,
    write_handoff,
)


@pytest.fixture
def change_dir(tmp_path):
    """Create a bare change directory in global store layout."""
    d = tmp_path / "data_dir" / "changes" / "my-change"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def data_dir(change_dir):
    """Return the data_dir (parent of changes dir)."""
    return change_dir.parent.parent


class TestWriteHandoff:
    def test_creates_file(self, change_dir):
        path = write_handoff(change_dir, "hello")
        assert path == change_dir / HANDOFF_FILE
        assert path.exists()

    def test_writes_content(self, change_dir):
        write_handoff(change_dir, "## Problem\nSomething broke")
        assert (change_dir / HANDOFF_FILE).read_text() == "## Problem\nSomething broke"


class TestReadHandoff:
    def test_returns_content(self, change_dir):
        (change_dir / HANDOFF_FILE).write_text("context data")
        assert read_handoff(change_dir) == "context data"

    def test_returns_none_when_missing(self, change_dir):
        assert read_handoff(change_dir) is None


class TestReadHandoffBundle:
    def test_includes_handoff(self, change_dir):
        write_handoff(change_dir, "handoff text")
        bundle = read_handoff_bundle(change_dir)
        assert "# Handoff" in bundle
        assert "handoff text" in bundle

    def test_includes_artifacts(self, change_dir):
        (change_dir / "proposal.md").write_text("proposal content")
        (change_dir / "design.md").write_text("design content")
        bundle = read_handoff_bundle(change_dir)
        assert "# proposal.md" in bundle
        assert "proposal content" in bundle
        assert "# design.md" in bundle
        assert "design content" in bundle

    def test_missing_artifacts_graceful(self, change_dir):
        """No artifacts at all produces empty string."""
        assert read_handoff_bundle(change_dir) == ""

    def test_skips_empty_artifacts(self, change_dir):
        (change_dir / "proposal.md").write_text("")
        (change_dir / "tasks.md").write_text("   ")
        # Empty/whitespace-only files are stripped then skipped
        assert read_handoff_bundle(change_dir) == ""

    def test_includes_delta_specs(self, change_dir):
        spec_dir = change_dir / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("auth spec content")
        bundle = read_handoff_bundle(change_dir)
        assert "# specs/auth/spec.md" in bundle
        assert "auth spec content" in bundle

    def test_delta_specs_sorted(self, change_dir):
        for name in ["zebra", "alpha"]:
            d = change_dir / "specs" / name
            d.mkdir(parents=True)
            (d / "spec.md").write_text(f"{name} spec")
        bundle = read_handoff_bundle(change_dir)
        assert bundle.index("alpha") < bundle.index("zebra")

    def test_full_bundle(self, change_dir):
        write_handoff(change_dir, "handoff text")
        (change_dir / "proposal.md").write_text("proposal")
        spec_dir = change_dir / "specs" / "feat"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("feat spec")
        bundle = read_handoff_bundle(change_dir)
        # Handoff excluded because artifacts exist
        assert "# Handoff" not in bundle
        assert "# proposal.md" in bundle
        assert "# specs/feat/spec.md" in bundle
        # Sections separated by ---
        assert "---" in bundle

    def test_handoff_excluded_when_artifacts_exist(self, change_dir):
        write_handoff(change_dir, "handoff text")
        (change_dir / "proposal.md").write_text("proposal content")
        bundle = read_handoff_bundle(change_dir)
        assert "# Handoff" not in bundle
        assert "handoff text" not in bundle
        assert "# proposal.md" in bundle
        assert "proposal content" in bundle

    def test_handoff_excluded_with_partial_artifacts(self, change_dir):
        write_handoff(change_dir, "handoff text")
        (change_dir / "proposal.md").write_text("proposal only")
        bundle = read_handoff_bundle(change_dir)
        assert "# Handoff" not in bundle
        assert "handoff text" not in bundle
        assert "proposal only" in bundle

    def test_handoff_excluded_when_only_specs_exist(self, change_dir):
        write_handoff(change_dir, "handoff text")
        spec_dir = change_dir / "specs" / "auth"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("auth spec content")
        bundle = read_handoff_bundle(change_dir)
        assert "# Handoff" not in bundle
        assert "handoff text" not in bundle
        assert "# specs/auth/spec.md" in bundle
        assert "auth spec content" in bundle

    def test_handoff_included_when_no_artifacts(self, change_dir):
        write_handoff(change_dir, "explore summary here")
        bundle = read_handoff_bundle(change_dir)
        assert "# Handoff" in bundle
        assert "explore summary here" in bundle


class TestBuildContext:
    def test_valid_change(self, data_dir):
        change_dir = data_dir / "changes" / "my-change"
        write_handoff(change_dir, "handoff data")
        result = build_context(data_dir, "my-change")
        assert "handoff data" in result

    def test_nonexistent_change_raises(self, data_dir):
        with pytest.raises(FileNotFoundError, match="no-such-change"):
            build_context(data_dir, "no-such-change")

    def test_token_truncation(self, data_dir):
        change_dir = data_dir / "changes" / "my-change"
        write_handoff(change_dir, "x" * 10000)
        result = build_context(data_dir, "my-change", max_tokens=100)
        # 100 tokens * 4 chars = 400 chars max before truncation marker
        assert "[... truncated to fit token budget ...]" in result
        # Content before marker should be roughly 400 chars
        truncated_content = result.split("\n\n[... truncated")[0]
        assert len(truncated_content) <= 500  # some overhead from headers

    def test_no_truncation_within_budget(self, data_dir):
        change_dir = data_dir / "changes" / "my-change"
        write_handoff(change_dir, "short")
        result = build_context(data_dir, "my-change", max_tokens=10000)
        assert "[... truncated" not in result

    def test_no_config(self, data_dir):
        """build_context works fine without config.yaml."""
        change_dir = data_dir / "changes" / "my-change"
        write_handoff(change_dir, "data")
        result = build_context(data_dir, "my-change")
        assert "data" in result
