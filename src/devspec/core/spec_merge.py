import re
from dataclasses import dataclass, field
from pathlib import Path

from devspec.core.delta_parser import (
    RequirementBlock,
    extract_requirements_section,
    normalize_requirement_name,
    parse_delta_spec,
)


@dataclass
class SpecUpdate:
    source: Path
    target: Path
    exists: bool


@dataclass
class MergeCounts:
    added: int = 0
    modified: int = 0
    removed: int = 0
    renamed: int = 0


@dataclass
class ApplyResult:
    change_name: str
    capabilities: list[dict[str, MergeCounts]] = field(default_factory=list)
    totals: MergeCounts = field(default_factory=MergeCounts)
    no_changes: bool = False


def find_spec_updates(change_dir: Path, main_specs_dir: Path) -> list[SpecUpdate]:
    """Discover delta spec files under change_dir/specs/ and pair them with main spec targets."""
    updates: list[SpecUpdate] = []
    change_specs_dir = change_dir / "specs"
    if not change_specs_dir.is_dir():
        return updates

    for entry in sorted(change_specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        spec_file = entry / "spec.md"
        target_file = main_specs_dir / entry.name / "spec.md"
        if spec_file.is_file():
            updates.append(SpecUpdate(source=spec_file, target=target_file, exists=target_file.is_file()))

    return updates


def build_spec_skeleton(spec_name: str, change_name: str) -> str:
    """Create a minimal spec file for a new capability."""
    return (
        f"# {spec_name} Specification\n\n"
        f"## Purpose\nTBD - created by archiving change {change_name}.\n\n"
        f"## Requirements\n"
    )


def build_updated_spec(update: SpecUpdate, change_name: str) -> tuple[str, MergeCounts]:
    """Apply a delta spec to an existing (or new) main spec, returning the rebuilt content and counts."""
    change_content = update.source.read_text()
    plan = parse_delta_spec(change_content)
    spec_name = update.target.parent.name

    # --- Pre-validate duplicates within sections ---
    added_names: set[str] = set()
    for add in plan.added:
        name = normalize_requirement_name(add.name)
        if name in added_names:
            raise ValueError(f'duplicate in ADDED for "{add.name}"')
        added_names.add(name)

    modified_names: set[str] = set()
    for mod in plan.modified:
        name = normalize_requirement_name(mod.name)
        if name in modified_names:
            raise ValueError(f'duplicate in MODIFIED for "{mod.name}"')
        modified_names.add(name)

    removed_names_set: set[str] = set()
    for rem in plan.removed:
        name = normalize_requirement_name(rem)
        if name in removed_names_set:
            raise ValueError(f'duplicate in REMOVED for "{rem}"')
        removed_names_set.add(name)

    renamed_from_set: set[str] = set()
    renamed_to_set: set[str] = set()
    for r in plan.renamed:
        from_norm = normalize_requirement_name(r.from_name)
        to_norm = normalize_requirement_name(r.to_name)
        if from_norm in renamed_from_set:
            raise ValueError("duplicate FROM in RENAMED")
        if to_norm in renamed_to_set:
            raise ValueError("duplicate TO in RENAMED")
        renamed_from_set.add(from_norm)
        renamed_to_set.add(to_norm)

    # --- Cross-section conflicts ---
    conflicts: list[dict[str, str]] = []
    for n in modified_names:
        if n in removed_names_set:
            conflicts.append({"name": n, "a": "MODIFIED", "b": "REMOVED"})
        if n in added_names:
            conflicts.append({"name": n, "a": "MODIFIED", "b": "ADDED"})
    for n in added_names:
        if n in removed_names_set:
            conflicts.append({"name": n, "a": "ADDED", "b": "REMOVED"})

    # Renamed interplay
    for r in plan.renamed:
        if normalize_requirement_name(r.from_name) in modified_names:
            raise ValueError(f'MODIFIED must reference NEW header "{r.to_name}"')
        if normalize_requirement_name(r.to_name) in added_names:
            raise ValueError(f'RENAMED TO collides with ADDED for "{r.to_name}"')

    if conflicts:
        c = conflicts[0]
        raise ValueError(f'requirement in both {c["a"]} and {c["b"]} for "{c["name"]}"')

    has_any_delta = len(plan.added) + len(plan.modified) + len(plan.removed) + len(plan.renamed) > 0
    if not has_any_delta:
        raise ValueError("no operations found")

    # --- Load or create target ---
    is_new_spec = False
    if update.exists:
        target_content = update.target.read_text()
    else:
        if plan.modified or plan.renamed:
            raise ValueError("target does not exist; only ADDED allowed for new specs")
        is_new_spec = True
        target_content = build_spec_skeleton(spec_name, change_name)

    # --- Build name->block map ---
    parts = extract_requirements_section(target_content)
    name_to_block: dict[str, RequirementBlock] = {}
    for block in parts.body_blocks:
        name_to_block[normalize_requirement_name(block.name)] = block

    # --- Apply: RENAMED -> REMOVED -> MODIFIED -> ADDED ---
    for r in plan.renamed:
        from_key = normalize_requirement_name(r.from_name)
        to_key = normalize_requirement_name(r.to_name)
        if from_key not in name_to_block:
            raise ValueError(f'RENAMED source not found: "{r.from_name}"')
        if to_key in name_to_block:
            raise ValueError(f'RENAMED target already exists: "{r.to_name}"')
        block = name_to_block[from_key]
        raw_lines = block.raw.split("\n")
        raw_lines[0] = f"### Requirement: {to_key}"
        del name_to_block[from_key]
        name_to_block[to_key] = RequirementBlock(header_line=raw_lines[0], name=to_key, raw="\n".join(raw_lines))

    for rem in plan.removed:
        key = normalize_requirement_name(rem)
        if key not in name_to_block:
            if not is_new_spec:
                raise ValueError(f'REMOVED not found: "{rem}"')
            continue
        del name_to_block[key]

    for mod in plan.modified:
        key = normalize_requirement_name(mod.name)
        if key not in name_to_block:
            raise ValueError(f'MODIFIED not found: "{mod.name}"')
        name_to_block[key] = mod

    for add in plan.added:
        key = normalize_requirement_name(add.name)
        if key in name_to_block:
            raise ValueError(f'ADDED already exists: "{add.name}"')
        name_to_block[key] = add

    # --- Recompose preserving original order ---
    kept_order: list[RequirementBlock] = []
    seen: set[str] = set()
    for block in parts.body_blocks:
        key = normalize_requirement_name(block.name)
        replacement = name_to_block.get(key)
        if replacement:
            kept_order.append(replacement)
            seen.add(key)
    for key, block in name_to_block.items():
        if key not in seen:
            kept_order.append(block)

    # Build requirements body
    preamble_stripped = parts.preamble.strip() if parts.preamble else ""
    req_parts: list[str] = []
    if preamble_stripped:
        req_parts.append(preamble_stripped)
    req_parts.extend(b.raw for b in kept_order)
    req_body = "\n\n".join(req_parts).rstrip()

    # Reassemble full document
    before = parts.before.rstrip()
    pieces: list[str] = []
    if before:
        pieces.append(before)
    pieces.append(parts.header_line)
    pieces.append(req_body)
    pieces.append(parts.after)
    rebuilt = "\n".join(pieces)

    # Collapse 3+ newlines to 2

    rebuilt = re.sub(r"\n{3,}", "\n\n", rebuilt)

    counts = MergeCounts(
        added=len(plan.added),
        modified=len(plan.modified),
        removed=len(plan.removed),
        renamed=len(plan.renamed),
    )
    return rebuilt, counts


def apply_specs(
    data_dir: Path,
    change_name: str,
    *,
    dry_run: bool = False,
    skip_validation: bool = False,
) -> ApplyResult:
    """Find and apply all delta specs for a change, writing results unless dry_run."""
    change_dir = data_dir / "changes" / change_name
    main_specs_dir = data_dir / "specs"

    if not change_dir.is_dir():
        raise FileNotFoundError(f"Change directory not found: {change_dir}")

    updates = find_spec_updates(change_dir, main_specs_dir)
    if not updates:
        return ApplyResult(change_name=change_name, no_changes=True)

    # Build all updates first (validation pass)
    results: list[tuple[SpecUpdate, str, MergeCounts]] = []
    for update in updates:
        rebuilt, counts = build_updated_spec(update, change_name)
        results.append((update, rebuilt, counts))

    # Write if not dry run
    if not dry_run:
        for update, rebuilt, _counts in results:
            update.target.parent.mkdir(parents=True, exist_ok=True)
            update.target.write_text(rebuilt)

    # Build result
    capabilities: list[dict[str, MergeCounts]] = []
    totals = MergeCounts()
    for update, _rebuilt, counts in results:
        cap_name = update.target.parent.name
        capabilities.append({cap_name: counts})
        totals.added += counts.added
        totals.modified += counts.modified
        totals.removed += counts.removed
        totals.renamed += counts.renamed

    return ApplyResult(
        change_name=change_name,
        capabilities=capabilities,
        totals=totals,
    )
