import re
from dataclasses import dataclass, field
from pathlib import Path

from devspec.core.delta_parser import (
    DeltaPlan,
    RequirementBlock,
    extract_requirements_section,
    normalize_requirement_name,
    parse_delta_spec,
)


@dataclass
class ValidationIssue:
    level: str  # "ERROR", "WARNING", "INFO"
    path: str
    message: str


@dataclass
class ValidationReport:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


def _extract_requirement_text(block_raw: str) -> str | None:
    """Extract the first substantial text line from a requirement block, skipping header and metadata."""
    lines = block_raw.split("\n")
    for i in range(1, len(lines)):
        if re.match(r"^####\s+", lines[i]):
            break
        trimmed = lines[i].strip()
        if not trimmed:
            continue
        if re.match(r"^\*\*[^*]+\*\*:", trimmed):
            continue
        return trimmed
    return None


def _contains_shall_or_must(text: str) -> bool:
    return bool(re.search(r"\b(SHALL|MUST)\b", text))


def _count_scenarios(block_raw: str) -> int:
    return len(re.findall(r"^####\s+", block_raw, re.MULTILINE))


def _create_report(issues: list[ValidationIssue], strict: bool = False) -> ValidationReport:
    errors = sum(1 for i in issues if i.level == "ERROR")
    warnings = sum(1 for i in issues if i.level == "WARNING")
    info = sum(1 for i in issues if i.level == "INFO")
    valid = (errors == 0 and warnings == 0) if strict else errors == 0
    return ValidationReport(
        valid=valid,
        issues=issues,
        summary={"errors": errors, "warnings": warnings, "info": info},
    )


def _validate_requirement_blocks(
    spec_name: str,
    section: str,
    blocks: list[RequirementBlock],
    issues: list[ValidationIssue],
) -> int:
    """Validate requirement blocks for SHALL/MUST and scenarios. Returns count."""
    for block in blocks:
        text = _extract_requirement_text(block.raw)
        if text is None or not _contains_shall_or_must(text):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/{section}/{block.name}",
                    message=f"Requirement '{block.name}' must contain SHALL or MUST in its description.",
                )
            )
        if _count_scenarios(block.raw) < 1:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/{section}/{block.name}",
                    message=f"Requirement '{block.name}' must have at least one scenario (#### heading).",
                )
            )
    return len(blocks)


def _validate_plan(spec_name: str, plan: DeltaPlan, issues: list[ValidationIssue]) -> int:
    """Validate a parsed DeltaPlan. Returns total delta count."""
    sp = plan.section_presence
    total = 0

    # Check section presence vs actual entries
    for section_name, present, entries in [
        ("ADDED", sp.added, plan.added),
        ("MODIFIED", sp.modified, plan.modified),
        ("REMOVED", sp.removed, plan.removed),
        ("RENAMED", sp.renamed, plan.renamed),
    ]:
        if present and not entries:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/{section_name}",
                    message=f"{section_name} Requirements section header present but no requirement entries found.",
                )
            )

    # Validate ADDED and MODIFIED blocks (same rules)
    total += _validate_requirement_blocks(spec_name, "ADDED", plan.added, issues)
    total += _validate_requirement_blocks(spec_name, "MODIFIED", plan.modified, issues)

    # Validate REMOVED: check duplicates
    removed_set: set[str] = set()
    for name in plan.removed:
        total += 1
        normalized = normalize_requirement_name(name)
        if normalized in removed_set:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/REMOVED",
                    message=f"Duplicate removal of requirement '{normalized}'.",
                )
            )
        removed_set.add(normalized)

    # Validate RENAMED: check duplicate FROM/TO
    renamed_froms: set[str] = set()
    renamed_tos: set[str] = set()
    for pair in plan.renamed:
        total += 1
        if pair.from_name in renamed_froms:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/RENAMED",
                    message=f"Duplicate FROM in rename: '{pair.from_name}'.",
                )
            )
        renamed_froms.add(pair.from_name)
        if pair.to_name in renamed_tos:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/RENAMED",
                    message=f"Duplicate TO in rename: '{pair.to_name}'.",
                )
            )
        renamed_tos.add(pair.to_name)

    # Cross-section conflicts
    added_names = {normalize_requirement_name(b.name) for b in plan.added}
    modified_names = {normalize_requirement_name(b.name) for b in plan.modified}

    for label_a, set_a, label_b, set_b in [
        ("MODIFIED", modified_names, "REMOVED", removed_set),
        ("MODIFIED", modified_names, "ADDED", added_names),
        ("ADDED", added_names, "REMOVED", removed_set),
    ]:
        overlap = set_a & set_b
        if overlap:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=spec_name,
                    message=f"Requirements in both {label_a} and {label_b}: {', '.join(sorted(overlap))}.",
                )
            )

    # RENAMED interplay
    for pair in plan.renamed:
        if pair.from_name in modified_names:
            issues.append(
                ValidationIssue(
                    level="WARNING",
                    path=f"{spec_name}/RENAMED",
                    message=f"MODIFIED references old name '{pair.from_name}' — should use new name '{pair.to_name}'.",
                )
            )
        if pair.to_name in added_names:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/RENAMED",
                    message=f"RENAMED TO '{pair.to_name}' conflicts with ADDED requirement of the same name.",
                )
            )

    return total


def validate_change_delta_specs(change_dir: Path) -> ValidationReport:
    """Validate all delta spec files under a change directory."""
    issues: list[ValidationIssue] = []
    specs_dir = change_dir / "specs"

    if not specs_dir.is_dir():
        issues.append(ValidationIssue(level="ERROR", path=str(change_dir), message="No specs/ directory found."))
        return _create_report(issues)

    total_deltas = 0
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        spec_file = entry / "spec.md"
        if not spec_file.is_file():
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=str(entry),
                    message=f"Missing spec.md in specs/{entry.name}/.",
                )
            )
            continue

        content = spec_file.read_text(encoding="utf-8")
        plan = parse_delta_spec(content)
        total_deltas += _validate_plan(entry.name, plan, issues)

    if total_deltas == 0:
        issues.append(ValidationIssue(level="ERROR", path=str(specs_dir), message="No deltas found in any spec file."))

    return _create_report(issues)


def validate_spec_content(spec_name: str, content: str) -> ValidationReport:
    """Validate a main spec file's content (checks structure, SHALL/MUST, scenarios)."""
    issues: list[ValidationIssue] = []

    # Check section exists before parsing (extract_requirements_section creates a synthetic
    # header as fallback, so we can't rely on its header_line being empty)
    if not re.search(r"^##\s+Requirements\s*$", content, re.MULTILINE | re.IGNORECASE):
        issues.append(ValidationIssue(level="ERROR", path=spec_name, message="Missing '## Requirements' section."))
        return _create_report(issues)

    parts = extract_requirements_section(content)

    for block in parts.body_blocks:
        text = _extract_requirement_text(block.raw)
        if text is None or not _contains_shall_or_must(text):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/{block.name}",
                    message=f"Requirement '{block.name}' must contain SHALL or MUST in its description.",
                )
            )
        if _count_scenarios(block.raw) < 1:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    path=f"{spec_name}/{block.name}",
                    message=f"Requirement '{block.name}' must have at least one scenario (#### heading).",
                )
            )

    return _create_report(issues)
