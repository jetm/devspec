from pathlib import Path

from devspec.core.analyzer import (
    AnalysisReport,
    _jaccard,
    _stem,
    _tokenize,
    analyze_change,
)

# --- Helpers ---


def _make_change(tmp_path: Path, *, proposal: str = "", specs: dict[str, str] | None = None, tasks: str = "") -> Path:
    """Create a change directory with optional artifacts."""
    change_dir = tmp_path / "test-change"
    change_dir.mkdir()

    if proposal:
        (change_dir / "proposal.md").write_text(proposal)

    if specs:
        specs_dir = change_dir / "specs"
        specs_dir.mkdir()
        for name, content in specs.items():
            cap_dir = specs_dir / name
            cap_dir.mkdir()
            (cap_dir / "spec.md").write_text(content)

    if tasks:
        (change_dir / "tasks.md").write_text(tasks)

    return change_dir


SAMPLE_PROPOSAL = """\
## Why

Add user authentication.

## What Changes

- Add OAuth2 login flow
- Add session management

## Capabilities

### New Capabilities
- `user-auth`: User authentication via OAuth2
- `session-mgmt`: Session token management

### Modified Capabilities

## Impact

- src/auth/
"""

SAMPLE_SPEC_AUTH = """\
## ADDED Requirements

### Requirement: User can authenticate
The system SHALL authenticate users via OAuth2.

#### Scenario: Successful login
- **WHEN** user provides valid credentials
- **THEN** system issues a session token
"""

SAMPLE_SPEC_SESSION = """\
## ADDED Requirements

### Requirement: Session token management
The system SHALL manage session tokens with expiry.

#### Scenario: Token expiry
- **WHEN** session token expires
- **THEN** user must re-authenticate
"""

SAMPLE_TASKS = """\
## 1. Setup

- [ ] 1.1 Add OAuth2 dependency
- [ ] 1.2 Configure auth provider

## 2. Authentication

- [ ] 2.1 Implement user authentication flow
- [ ] 2.2 Add session token management
- [ ] 2.3 Add logging middleware
"""


# --- Unit tests for helpers ---


class TestStem:
    def test_ication_suffix(self):
        assert _stem("authentication") == "authent"

    def test_icate_suffix(self):
        assert _stem("authenticate") == "authent"

    def test_ion_suffix(self):
        assert _stem("detection") == "detect"

    def test_ing_undoubles_consonant(self):
        assert _stem("logging") == "log"
        assert _stem("running") == "run"

    def test_ing_no_undouble_when_different(self):
        assert _stem("reading") == "read"

    def test_short_word_unchanged(self):
        assert _stem("can") == "can"

    def test_no_suffix(self):
        assert _stem("user") == "user"


class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("User can authenticate")
        assert "user" in tokens
        assert "authent" in tokens  # stemmed

    def test_filters_short(self):
        assert _tokenize("a to be") == set()

    def test_includes_digits(self):
        tokens = _tokenize("OAuth2 Login")
        assert "oauth2" in tokens
        assert "login" in tokens

    def test_stemming_matches_variants(self):
        # "authenticate" and "authentication" should produce the same stem
        t1 = _tokenize("authenticate")
        t2 = _tokenize("authentication")
        assert t1 & t2  # non-empty intersection


class TestJaccard:
    def test_identical(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial(self):
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0


# --- Coverage gaps ---


class TestCoverageGaps:
    def test_matched_requirements(self, tmp_path):
        change = _make_change(
            tmp_path,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            tasks="- [ ] Implement user authentication flow\n",
        )
        report = analyze_change(change)
        assert report.coverage is not None
        assert report.coverage.requirements_with_tasks == 1
        assert report.coverage.uncovered_requirements == []

    def test_uncovered_requirement(self, tmp_path):
        change = _make_change(
            tmp_path,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            tasks="- [ ] Add logging middleware\n",
        )
        report = analyze_change(change)
        assert report.coverage is not None
        assert report.coverage.requirements_with_tasks == 0
        assert len(report.coverage.uncovered_requirements) == 1
        coverage_issues = [i for i in report.issues if i.category == "coverage"]
        assert len(coverage_issues) == 1

    def test_orphan_task(self, tmp_path):
        change = _make_change(
            tmp_path,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            tasks="- [ ] Implement user authentication flow\n- [ ] Add unrelated logging\n",
        )
        report = analyze_change(change)
        assert report.coverage is not None
        assert len(report.coverage.orphan_tasks) == 1
        orphan_issues = [i for i in report.issues if i.category == "orphan"]
        assert len(orphan_issues) == 1

    def test_no_artifacts(self, tmp_path):
        change = _make_change(tmp_path)
        report = analyze_change(change)
        assert report.coverage is None


# --- Capability alignment ---


class TestCapabilityAlignment:
    def test_aligned(self, tmp_path):
        change = _make_change(
            tmp_path,
            proposal=SAMPLE_PROPOSAL,
            specs={"user-auth": SAMPLE_SPEC_AUTH, "session-mgmt": SAMPLE_SPEC_SESSION},
        )
        report = analyze_change(change)
        consistency = [i for i in report.issues if i.category == "consistency" and "capability" in i.message.lower()]
        assert len(consistency) == 0

    def test_declared_but_missing_spec(self, tmp_path):
        change = _make_change(
            tmp_path,
            proposal=SAMPLE_PROPOSAL,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            # session-mgmt is declared but has no spec dir
        )
        report = analyze_change(change)
        consistency = [i for i in report.issues if i.severity == "CRITICAL" and i.category == "consistency"]
        assert any("session-mgmt" in i.message for i in consistency)

    def test_undeclared_spec(self, tmp_path):
        extra_proposal = SAMPLE_PROPOSAL.replace("- `session-mgmt`: Session token management\n", "")
        change = _make_change(
            tmp_path,
            proposal=extra_proposal,
            specs={"user-auth": SAMPLE_SPEC_AUTH, "session-mgmt": SAMPLE_SPEC_SESSION},
        )
        report = analyze_change(change)
        warnings = [i for i in report.issues if i.severity == "WARNING" and "not declared" in i.message]
        assert any("session-mgmt" in i.message for i in warnings)


# --- Ambiguity detection ---


class TestAmbiguityDetection:
    def test_needs_clarification_marker(self, tmp_path):
        change = _make_change(tmp_path)
        (change / "design.md").write_text("## Context\n\n[NEEDS CLARIFICATION: What auth provider?]\n")
        report = analyze_change(change)
        ambiguity = [i for i in report.issues if i.category == "ambiguity" and i.severity == "CRITICAL"]
        assert len(ambiguity) == 1
        assert "NEEDS CLARIFICATION" in ambiguity[0].message

    def test_vague_adjective(self, tmp_path):
        spec = """\
## ADDED Requirements

### Requirement: Fast response
The system SHALL provide fast response times.

#### Scenario: Quick response
- **WHEN** user makes a request
- **THEN** response is fast
"""
        change = _make_change(tmp_path, specs={"perf": spec})
        report = analyze_change(change)
        vague = [i for i in report.issues if i.category == "ambiguity" and i.severity == "SUGGESTION"]
        assert len(vague) > 0
        assert any("fast" in i.message.lower() for i in vague)

    def test_no_false_positives_on_clean(self, tmp_path):
        change = _make_change(
            tmp_path,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
        )
        report = analyze_change(change)
        ambiguity = [i for i in report.issues if i.category == "ambiguity" and i.severity == "CRITICAL"]
        assert len(ambiguity) == 0


# --- Terminology drift ---


class TestTerminologyDrift:
    def test_term_missing_downstream(self, tmp_path):
        # Proposal has `session-tokens` in backticks (not a capability name),
        # and downstream artifacts don't mention it
        proposal = """\
## Why

Add auth.

## What Changes

- Add `OAuth2` login flow
- Add `session-tokens` handling

## Capabilities

### New Capabilities
- `user-auth`: Auth capability

### Modified Capabilities

## Impact

- src/auth/
"""
        change = _make_change(
            tmp_path,
            proposal=proposal,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            tasks="- [ ] Implement login\n",
        )
        report = analyze_change(change)
        term_issues = [i for i in report.issues if i.category == "consistency" and "Term" in i.message]
        # session-tokens is in proposal backticks but not in downstream artifacts
        assert any("session-tokens" in i.message for i in term_issues)
        # OAuth2 appears in spec, so it should NOT be flagged
        assert not any("OAuth2" in i.message for i in term_issues)

    def test_capability_names_not_double_reported(self, tmp_path):
        """Capability names should be checked by alignment, not terminology."""
        change = _make_change(
            tmp_path,
            proposal=SAMPLE_PROPOSAL,
            specs={"user-auth": SAMPLE_SPEC_AUTH},
            # session-mgmt declared in proposal but no spec dir — alignment catches this
            tasks="- [ ] Implement auth\n",
        )
        report = analyze_change(change)
        term_issues = [i for i in report.issues if i.category == "consistency" and "Term" in i.message]
        # session-mgmt should NOT appear in terminology issues (it's a capability name)
        assert not any("session-mgmt" in i.message for i in term_issues)

    def test_short_terms_ignored(self, tmp_path):
        proposal = "## Why\n\nTest.\n\n## What Changes\n\n- Use `db`\n\n## Capabilities\n\n### New Capabilities\n\n### Modified Capabilities\n\n## Impact\n\n- none\n"
        change = _make_change(tmp_path, proposal=proposal)
        (change / "tasks.md").write_text("- [ ] Do something\n")
        report = analyze_change(change)
        term_issues = [i for i in report.issues if i.category == "consistency" and "Term" in i.message]
        assert not any("`db`" in i.message for i in term_issues)


# --- Task format ---


class TestTaskFormat:
    def test_valid_checkboxes(self, tmp_path):
        change = _make_change(tmp_path, tasks="- [ ] Task one\n- [x] Task two\n")
        report = analyze_change(change)
        fmt = [i for i in report.issues if i.category == "format"]
        assert len(fmt) == 0

    def test_missing_checkbox(self, tmp_path):
        change = _make_change(tmp_path, tasks="- [ ] Task one\n- Task without checkbox\n")
        report = analyze_change(change)
        fmt = [i for i in report.issues if i.category == "format"]
        assert len(fmt) == 1
        assert "checkbox" in fmt[0].message.lower()

    def test_headings_not_flagged(self, tmp_path):
        change = _make_change(tmp_path, tasks="## 1. Setup\n\n- [ ] Task one\n")
        report = analyze_change(change)
        fmt = [i for i in report.issues if i.category == "format"]
        assert len(fmt) == 0

    def test_indented_sub_items_not_flagged(self, tmp_path):
        tasks = "- [ ] Implement auth\n  - Use OAuth2 library\n  - Handle token refresh\n"
        change = _make_change(tmp_path, tasks=tasks)
        report = analyze_change(change)
        fmt = [i for i in report.issues if i.category == "format"]
        assert len(fmt) == 0


# --- Full integration ---


class TestFullAnalysis:
    def test_full_change(self, tmp_path):
        change = _make_change(
            tmp_path,
            proposal=SAMPLE_PROPOSAL,
            specs={"user-auth": SAMPLE_SPEC_AUTH, "session-mgmt": SAMPLE_SPEC_SESSION},
            tasks=SAMPLE_TASKS,
        )
        report = analyze_change(change)
        assert isinstance(report, AnalysisReport)
        assert report.change_name == "test-change"
        assert report.coverage is not None
        assert report.summary is not None
        # Should have some issues (orphan task for logging, terminology)
        assert len(report.issues) > 0

    def test_nonexistent_change(self, tmp_path):
        report = analyze_change(tmp_path / "nonexistent")
        assert len(report.issues) == 1
        assert report.issues[0].severity == "CRITICAL"
        assert report.summary == {"critical": 1, "warning": 0, "suggestion": 0}

    def test_sample_change_fixture(self, sample_change):
        """Test against the conftest sample_change fixture."""
        report = analyze_change(sample_change)
        assert isinstance(report, AnalysisReport)
        assert report.change_name == "test-change"
