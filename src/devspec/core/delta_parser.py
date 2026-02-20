import re
from dataclasses import dataclass

REQUIREMENT_HEADER_RE = re.compile(r"^###\s*Requirement:\s*(.+)\s*$")


@dataclass
class RequirementBlock:
    header_line: str
    name: str
    raw: str


@dataclass
class RenamedPair:
    from_name: str
    to_name: str


@dataclass
class SectionPresence:
    added: bool
    modified: bool
    removed: bool
    renamed: bool


@dataclass
class DeltaPlan:
    added: list[RequirementBlock]
    modified: list[RequirementBlock]
    removed: list[str]
    renamed: list[RenamedPair]
    section_presence: SectionPresence


@dataclass
class RequirementsSectionParts:
    before: str
    header_line: str
    preamble: str
    body_blocks: list[RequirementBlock]
    after: str


def _normalize_line_endings(content: str) -> str:
    return content.replace("\r\n", "\n")


def normalize_requirement_name(name: str) -> str:
    return name.strip()


def extract_requirements_section(content: str) -> RequirementsSectionParts:
    normalized = _normalize_line_endings(content)
    lines = normalized.split("\n")

    req_header_index = -1
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Requirements\s*$", line, re.IGNORECASE):
            req_header_index = i
            break

    if req_header_index == -1:
        before = content.rstrip()
        return RequirementsSectionParts(
            before=before + "\n\n" if before else "",
            header_line="## Requirements",
            preamble="",
            body_blocks=[],
            after="\n",
        )

    end_index = len(lines)
    for i in range(req_header_index + 1, len(lines)):
        if re.match(r"^##\s+", lines[i]):
            end_index = i
            break

    before = "\n".join(lines[:req_header_index])
    header_line = lines[req_header_index]
    section_body_lines = lines[req_header_index + 1 : end_index]

    # Extract preamble (lines before first requirement header)
    cursor = 0
    preamble_lines: list[str] = []
    while cursor < len(section_body_lines) and not re.match(r"^###\s+Requirement:", section_body_lines[cursor]):
        preamble_lines.append(section_body_lines[cursor])
        cursor += 1

    # Extract requirement blocks
    blocks: list[RequirementBlock] = []
    while cursor < len(section_body_lines):
        header_candidate = section_body_lines[cursor]
        m = REQUIREMENT_HEADER_RE.match(header_candidate)
        if not m:
            cursor += 1
            continue

        name = normalize_requirement_name(m.group(1))
        cursor += 1
        body_lines = [header_candidate]
        while (
            cursor < len(section_body_lines)
            and not re.match(r"^###\s+Requirement:", section_body_lines[cursor])
            and not re.match(r"^##\s+", section_body_lines[cursor])
        ):
            body_lines.append(section_body_lines[cursor])
            cursor += 1

        raw = "\n".join(body_lines).rstrip()
        blocks.append(RequirementBlock(header_line=header_candidate, name=name, raw=raw))

    after = "\n".join(lines[end_index:])
    preamble = "\n".join(preamble_lines).rstrip()

    return RequirementsSectionParts(
        before=before + "\n" if before.rstrip() else before,
        header_line=header_line,
        preamble=preamble,
        body_blocks=blocks,
        after=after if after.startswith("\n") else "\n" + after,
    )


def parse_delta_spec(content: str) -> DeltaPlan:
    normalized = _normalize_line_endings(content)
    sections = _split_top_level_sections(normalized)

    added_lookup = _get_section_case_insensitive(sections, "ADDED Requirements")
    modified_lookup = _get_section_case_insensitive(sections, "MODIFIED Requirements")
    removed_lookup = _get_section_case_insensitive(sections, "REMOVED Requirements")
    renamed_lookup = _get_section_case_insensitive(sections, "RENAMED Requirements")

    return DeltaPlan(
        added=_parse_requirement_blocks_from_section(added_lookup[0]),
        modified=_parse_requirement_blocks_from_section(modified_lookup[0]),
        removed=_parse_removed_names(removed_lookup[0]),
        renamed=_parse_renamed_pairs(renamed_lookup[0]),
        section_presence=SectionPresence(
            added=added_lookup[1],
            modified=modified_lookup[1],
            removed=removed_lookup[1],
            renamed=renamed_lookup[1],
        ),
    )


def _split_top_level_sections(content: str) -> dict[str, str]:
    lines = content.split("\n")
    indices: list[tuple[str, int]] = []

    for i, line in enumerate(lines):
        m = re.match(r"^(##)\s+(.+)$", line)
        if m:
            indices.append((m.group(2).strip(), i))

    result: dict[str, str] = {}
    for i, (title, start) in enumerate(indices):
        next_start = indices[i + 1][1] if i + 1 < len(indices) else len(lines)
        result[title] = "\n".join(lines[start + 1 : next_start])

    return result


def _get_section_case_insensitive(sections: dict[str, str], desired: str) -> tuple[str, bool]:
    target = desired.lower()
    for title, body in sections.items():
        if title.lower() == target:
            return (body, True)
    return ("", False)


def _parse_requirement_blocks_from_section(section_body: str) -> list[RequirementBlock]:
    if not section_body:
        return []

    lines = _normalize_line_endings(section_body).split("\n")
    blocks: list[RequirementBlock] = []
    i = 0

    while i < len(lines):
        # Skip until we find a requirement header
        while i < len(lines) and not re.match(r"^###\s+Requirement:", lines[i]):
            i += 1
        if i >= len(lines):
            break

        header_line = lines[i]
        m = REQUIREMENT_HEADER_RE.match(header_line)
        if not m:
            i += 1
            continue

        name = normalize_requirement_name(m.group(1))
        buf = [header_line]
        i += 1
        while i < len(lines) and not re.match(r"^###\s+Requirement:", lines[i]) and not re.match(r"^##\s+", lines[i]):
            buf.append(lines[i])
            i += 1

        blocks.append(RequirementBlock(header_line=header_line, name=name, raw="\n".join(buf).rstrip()))

    return blocks


def _parse_removed_names(section_body: str) -> list[str]:
    if not section_body:
        return []

    names: list[str] = []
    lines = _normalize_line_endings(section_body).split("\n")

    for line in lines:
        m = REQUIREMENT_HEADER_RE.match(line)
        if m:
            names.append(normalize_requirement_name(m.group(1)))
            continue
        bullet = re.match(r"^\s*-\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
        if bullet:
            names.append(normalize_requirement_name(bullet.group(1)))

    return names


def _parse_renamed_pairs(section_body: str) -> list[RenamedPair]:
    if not section_body:
        return []

    pairs: list[RenamedPair] = []
    lines = _normalize_line_endings(section_body).split("\n")
    current_from: str | None = None

    for line in lines:
        from_match = re.match(r"^\s*-?\s*FROM:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
        to_match = re.match(r"^\s*-?\s*TO:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", line)
        if from_match:
            current_from = normalize_requirement_name(from_match.group(1))
        elif to_match:
            to_name = normalize_requirement_name(to_match.group(1))
            if current_from and to_name:
                pairs.append(RenamedPair(from_name=current_from, to_name=to_name))
                current_from = None

    return pairs
