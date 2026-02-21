"""Core logic for creating devspec changes."""

from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from devspec.core.resolve import KEBAB_CASE_RE
from devspec.core.schema import load_schema


def create_change(changes_dir: Path, name: str) -> tuple[Path, str]:
    """Create a new change directory with metadata and specs subdirectory.

    Args:
        changes_dir: Path to the changes/ directory.
        name: Kebab-case change name.

    Returns:
        Tuple of (change_dir, schema_name).

    Raises:
        FileNotFoundError: If changes_dir does not exist.
        ValueError: If name is invalid or change already exists.
    """
    if not changes_dir.exists():
        raise FileNotFoundError("No changes/ directory. Run devspec init first.")

    if not name or not name.strip():
        raise ValueError("Change name must not be empty.")

    if not KEBAB_CASE_RE.match(name):
        raise ValueError(f"Invalid change name: {name!r}. Use kebab-case (e.g., 'add-feature').")

    change_dir = changes_dir / name
    if change_dir.exists():
        raise ValueError(f"Change already exists: {name}")

    schema = load_schema()
    change_dir.mkdir()

    meta = {"schema": schema.name, "created": datetime.date.today().isoformat()}
    (change_dir / ".devspec.yaml").write_text(yaml.dump(meta, default_flow_style=False))
    (change_dir / "specs").mkdir()

    return change_dir, schema.name
