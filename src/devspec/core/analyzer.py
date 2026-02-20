import re
from dataclasses import dataclass, field
from pathlib import Path

from devspec.core.delta_parser import parse_delta_spec

TASK_RE = re.compile(r"^- \[[ x]\] (.+)$", re.MULTILINE)
CAPABILITY_RE = re.compile(r"- `([^`]+)`")
NEEDS_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION[:\s].*?\]", re.IGNORECASE)
VAGUE_ADJECTIVES = frozenset(
    {
        "fast",
        "robust",
        "secure",
        "scalable",
        "intuitive",
        "efficient",
        "flexible",
        "reliable",
        "performant",
        "simple",
    }
)
VAGUE_RE = re.compile(r"\b(" + "|".join(VAGUE_ADJECTIVES) + r")\b", re.IGNORECASE)


@dataclass
class AnalysisIssue:
    severity: str  # "CRITICAL", "WARNING", "SUGGESTION"
    category: str  # "coverage", "consistency", "ambiguity", "orphan", "format"
    location: str  # artifact path
    message: str


@dataclass
class CoverageStats:
    total_requirements: int
    requirements_with_tasks: int
    total_tasks: int
    tasks_with_requirements: int
    uncovered_requirements: list[str]
    orphan_tasks: list[str]


@dataclass
class AnalysisReport:
    change_name: str
    issues: list[AnalysisIssue] = field(default_factory=list)
    coverage: CoverageStats | None = None
    summary: dict[str, int] = field(default_factory=dict)


_STEM_SUFFIXES = (
    # Longest first so compound suffixes match before shorter ones
    "ication",
    "icate",
    "ation",
    "ment",
    "ion",
    "ness",
    "able",
    "ible",
    "ing",
    "ity",
    "ous",
    "ive",
    "ful",
    "less",
    "ize",
    "ise",
    "ate",
)


def _stem(word: str) -> str:
    """Crude suffix stripping to improve fuzzy matching (e.g., authenticate/authentication)."""
    for suffix in _STEM_SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            result = word[: -len(suffix)]
            # Un-double trailing consonant after -ing strip (logging→log, running→run)
            if suffix == "ing" and len(result) >= 3 and result[-1] == result[-2]:
                result = result[:-1]
            return result
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def _tokenize(text: str) -> set[str]:
    """Normalize text to a set of lowercase stemmed keywords."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _extract_requirements(change_dir: Path) -> list[tuple[str, str]]:
    """Extract (spec_name, requirement_name) pairs from all delta specs."""
    specs_dir = change_dir / "specs"
    if not specs_dir.is_dir():
        return []

    requirements: list[tuple[str, str]] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        spec_file = entry / "spec.md"
        if not spec_file.is_file():
            continue
        content = spec_file.read_text(encoding="utf-8")
        plan = parse_delta_spec(content)
        for block in plan.added + plan.modified:
            requirements.append((entry.name, block.name))
    return requirements


def _extract_tasks(change_dir: Path) -> list[str]:
    """Extract task descriptions from tasks.md."""
    tasks_file = change_dir / "tasks.md"
    if not tasks_file.is_file():
        return []
    return TASK_RE.findall(tasks_file.read_text(encoding="utf-8"))


def _extract_capabilities(change_dir: Path) -> tuple[list[str], list[str]]:
    """Extract (new_capabilities, modified_capabilities) from proposal.md."""
    proposal = change_dir / "proposal.md"
    if not proposal.is_file():
        return [], []

    content = proposal.read_text(encoding="utf-8")
    new_caps: list[str] = []
    mod_caps: list[str] = []

    in_new = False
    in_mod = False
    for line in content.split("\n"):
        if re.match(r"^###\s+New Capabilities", line):
            in_new, in_mod = True, False
            continue
        elif re.match(r"^###\s+Modified Capabilities", line):
            in_new, in_mod = False, True
            continue
        elif re.match(r"^##", line):
            in_new, in_mod = False, False
            continue

        m = CAPABILITY_RE.match(line.strip())
        if m:
            if in_new:
                new_caps.append(m.group(1))
            elif in_mod:
                mod_caps.append(m.group(1))

    return new_caps, mod_caps


def _extract_proposal_terms(change_dir: Path) -> set[str]:
    """Extract key terms from proposal (backtick-enclosed terms)."""
    proposal = change_dir / "proposal.md"
    if not proposal.is_file():
        return set()

    backtick_terms = set(re.findall(r"`([^`]+)`", proposal.read_text(encoding="utf-8")))

    # Filter out capability names — those are checked by _check_capability_alignment
    new_caps, mod_caps = _extract_capabilities(change_dir)
    backtick_terms -= set(new_caps + mod_caps)

    return backtick_terms


def _check_coverage(
    requirements: list[tuple[str, str]],
    tasks: list[str],
    issues: list[AnalysisIssue],
) -> CoverageStats:
    """Check requirement-task coverage using fuzzy matching."""
    req_tokens = [(spec, name, _tokenize(name)) for spec, name in requirements]
    task_tokens = [(desc, _tokenize(desc)) for desc in tasks]

    matched_reqs: set[int] = set()
    matched_tasks: set[int] = set()

    for ri, (spec, name, rtoks) in enumerate(req_tokens):
        for ti, (desc, ttoks) in enumerate(task_tokens):
            if _jaccard(rtoks, ttoks) >= 0.2:
                matched_reqs.add(ri)
                matched_tasks.add(ti)

    uncovered: list[str] = []
    for ri, (spec, name, _) in enumerate(req_tokens):
        if ri not in matched_reqs:
            uncovered.append(f"specs/{spec}: {name!r}")
            issues.append(
                AnalysisIssue(
                    severity="WARNING",
                    category="coverage",
                    location=f"specs/{spec}",
                    message=f"Requirement {name!r} — no matching task",
                )
            )

    orphan: list[str] = []
    for ti, (desc, _) in enumerate(task_tokens):
        if ti not in matched_tasks:
            orphan.append(f"tasks.md: {desc!r}")
            issues.append(
                AnalysisIssue(
                    severity="SUGGESTION",
                    category="orphan",
                    location="tasks.md",
                    message=f"Task {desc!r} — no matching requirement",
                )
            )

    return CoverageStats(
        total_requirements=len(requirements),
        requirements_with_tasks=len(matched_reqs),
        total_tasks=len(tasks),
        tasks_with_requirements=len(matched_tasks),
        uncovered_requirements=uncovered,
        orphan_tasks=orphan,
    )


def _check_capability_alignment(
    change_dir: Path,
    issues: list[AnalysisIssue],
) -> None:
    """Check that declared capabilities match spec directories."""
    new_caps, mod_caps = _extract_capabilities(change_dir)
    specs_dir = change_dir / "specs"
    existing_specs = {d.name for d in specs_dir.iterdir() if d.is_dir()} if specs_dir.is_dir() else set()

    all_declared = set(new_caps + mod_caps)

    for cap in sorted(all_declared - existing_specs):
        issues.append(
            AnalysisIssue(
                severity="CRITICAL",
                category="consistency",
                location="proposal.md",
                message=f"Declares capability `{cap}` but no specs/{cap}/ exists",
            )
        )

    for spec in sorted(existing_specs - all_declared):
        issues.append(
            AnalysisIssue(
                severity="WARNING",
                category="consistency",
                location=f"specs/{spec}",
                message=f"Spec directory exists but `{spec}` not declared in proposal capabilities",
            )
        )


def _check_ambiguity(
    change_dir: Path,
    issues: list[AnalysisIssue],
) -> None:
    """Scan for unresolved NEEDS CLARIFICATION markers and vague adjectives."""
    for md_file in sorted(change_dir.rglob("*.md")):
        rel = md_file.relative_to(change_dir)
        content = md_file.read_text(encoding="utf-8")

        for m in NEEDS_CLARIFICATION_RE.finditer(content):
            issues.append(
                AnalysisIssue(
                    severity="CRITICAL",
                    category="ambiguity",
                    location=str(rel),
                    message=f"Unresolved marker: {m.group(0)}",
                )
            )

        for m in VAGUE_RE.finditer(content):
            # Get line context
            start = content.rfind("\n", 0, m.start()) + 1
            end = content.find("\n", m.end())
            if end == -1:
                end = len(content)
            line = content[start:end].strip()
            issues.append(
                AnalysisIssue(
                    severity="SUGGESTION",
                    category="ambiguity",
                    location=str(rel),
                    message=f"Vague term {m.group(0)!r} — needs quantification: {line!r}",
                )
            )


def _check_terminology(
    change_dir: Path,
    issues: list[AnalysisIssue],
) -> None:
    """Check that key terms from proposal appear in downstream artifacts."""
    terms = _extract_proposal_terms(change_dir)
    if not terms:
        return

    # Collect text from all non-proposal artifacts
    downstream_text = ""
    for md_file in sorted(change_dir.rglob("*.md")):
        if md_file.name == "proposal.md":
            continue
        downstream_text += md_file.read_text(encoding="utf-8") + "\n"

    if not downstream_text.strip():
        return

    downstream_lower = downstream_text.lower()
    for term in sorted(terms):
        # Skip short/generic terms and capability names (covered by alignment check)
        if len(term) < 4 or term.startswith("<"):
            continue
        if term.lower() not in downstream_lower:
            issues.append(
                AnalysisIssue(
                    severity="SUGGESTION",
                    category="consistency",
                    location="proposal.md",
                    message=f"Term `{term}` appears in proposal but not in downstream artifacts",
                )
            )


def _check_task_format(
    change_dir: Path,
    issues: list[AnalysisIssue],
) -> None:
    """Verify tasks use checkbox format."""
    tasks_file = change_dir / "tasks.md"
    if not tasks_file.is_file():
        return

    content = tasks_file.read_text(encoding="utf-8")
    for i, line in enumerate(content.split("\n"), 1):
        # Only flag top-level list items (no leading whitespace) that lack checkbox format.
        # Indented sub-bullets (e.g., "  - detail") are descriptions, not tasks.
        if re.match(r"^- (?!\[[ x]\] )\S", line):
            issues.append(
                AnalysisIssue(
                    severity="WARNING",
                    category="format",
                    location=f"tasks.md:{i}",
                    message=f"Task without checkbox format: {line.strip()!r}",
                )
            )


def analyze_change(change_dir: Path) -> AnalysisReport:
    """Run all analysis passes on a change directory."""
    change_name = change_dir.name
    issues: list[AnalysisIssue] = []

    if not change_dir.is_dir():
        issues.append(
            AnalysisIssue(
                severity="CRITICAL",
                category="consistency",
                location=str(change_dir),
                message="Change directory does not exist",
            )
        )
        return AnalysisReport(
            change_name=change_name,
            issues=issues,
            summary={"critical": 1, "warning": 0, "suggestion": 0},
        )

    requirements = _extract_requirements(change_dir)
    tasks = _extract_tasks(change_dir)

    # 1. Coverage gaps
    coverage = _check_coverage(requirements, tasks, issues) if requirements or tasks else None

    # 2. Capability alignment
    if (change_dir / "proposal.md").is_file():
        _check_capability_alignment(change_dir, issues)

    # 3. Ambiguity detection
    _check_ambiguity(change_dir, issues)

    # 4. Terminology drift
    _check_terminology(change_dir, issues)

    # 5. Task format
    _check_task_format(change_dir, issues)

    summary = {
        "critical": sum(1 for i in issues if i.severity == "CRITICAL"),
        "warning": sum(1 for i in issues if i.severity == "WARNING"),
        "suggestion": sum(1 for i in issues if i.severity == "SUGGESTION"),
    }

    return AnalysisReport(
        change_name=change_name,
        issues=issues,
        coverage=coverage,
        summary=summary,
    )
