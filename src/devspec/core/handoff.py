from pathlib import Path

HANDOFF_FILE = ".handoff.md"


def write_handoff(change_dir: Path, content: str) -> Path:
    """Write handoff content to .handoff.md in the change directory.

    Content can be either raw markdown or structured with ## sections.
    """
    path = change_dir / HANDOFF_FILE
    path.write_text(content)
    return path


def read_handoff(change_dir: Path) -> str | None:
    """Read handoff content from .handoff.md. Returns None if not found."""
    path = change_dir / HANDOFF_FILE
    if not path.exists():
        return None
    return path.read_text()


def read_handoff_bundle(change_dir: Path) -> str:
    """Read handoff + all existing artifacts into a single context bundle.

    Returns a markdown document with:
    - Handoff content (only when no artifact files exist yet)
    - All artifact files found in the change directory
    """
    parts = []

    # Check if any artifacts exist
    artifact_files = ["proposal.md", "design.md", "tasks.md"]
    artifacts_exist = any((change_dir / name).exists() for name in artifact_files)

    # Also check for any specs/*/spec.md files
    if not artifacts_exist:
        specs_dir = change_dir / "specs"
        if specs_dir.is_dir():
            artifacts_exist = any(
                (spec_dir / "spec.md").exists() for spec_dir in specs_dir.iterdir() if spec_dir.is_dir()
            )

    # Handoff - only include when no artifacts exist yet
    if not artifacts_exist:
        handoff = read_handoff(change_dir)
        if handoff:
            parts.append("# Handoff\n\n" + handoff)

    # Artifacts - check for standard files
    for name in artifact_files:
        path = change_dir / name
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(f"# {name}\n\n{content}")

    # Delta specs
    specs_dir = change_dir / "specs"
    if specs_dir.is_dir():
        for spec_dir in sorted(specs_dir.iterdir()):
            if spec_dir.is_dir():
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    content = spec_file.read_text().strip()
                    if content:
                        parts.append(f"# specs/{spec_dir.name}/spec.md\n\n{content}")

    return "\n\n---\n\n".join(parts) if parts else ""


def build_context(data_dir: Path, change_name: str, max_tokens: int | None = None) -> str:
    """Build a token-budgeted context dump for subagent injection.

    Includes: handoff + artifacts.
    If max_tokens is set, truncates to approximate token budget (4 chars per token estimate).
    """
    change_dir = data_dir / "changes" / change_name
    if not change_dir.is_dir():
        raise FileNotFoundError(f"Change '{change_name}' not found at {change_dir}")

    parts = []

    # Bundle all artifacts
    bundle = read_handoff_bundle(change_dir)
    if bundle:
        parts.append(bundle)

    result = "\n\n---\n\n".join(parts) if parts else ""

    # Token budget truncation
    if max_tokens and len(result) > max_tokens * 4:
        result = result[: max_tokens * 4] + "\n\n[... truncated to fit token budget ...]"

    return result
