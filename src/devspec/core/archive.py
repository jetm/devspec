import datetime
import shutil
from dataclasses import dataclass
from pathlib import Path

from devspec.core.schema import load_schema
from devspec.core.state import detect_completed


@dataclass
class ArchiveResult:
    change_name: str
    archive_path: Path
    specs_synced: bool


def archive_change(
    project_root: Path,
    change_name: str,
    *,
    skip_specs: bool = False,
    force: bool = False,
) -> ArchiveResult:
    """Archive a completed change.

    Pipeline:
    1. Verify change exists
    2. Check artifact completion status (warn if incomplete, fail unless force)
    3. Optionally sync specs
    4. Create archive directory if needed
    5. Generate target name: YYYY-MM-DD-<change-name>
    6. Check target doesn't already exist
    7. Move change directory to archive
    """
    changes_dir = project_root / "openspec" / "changes"
    change_dir = changes_dir / change_name

    if not change_dir.exists():
        raise FileNotFoundError(f"Change not found: {change_name}")

    # Check completion status
    schema = load_schema()
    completed = detect_completed(schema, change_dir)
    all_ids = {a.id for a in schema.artifacts}
    if completed != all_ids and not force:
        missing = all_ids - completed
        raise ValueError(f"Incomplete artifacts: {', '.join(sorted(missing))}. Use force=True to archive anyway.")

    # Optionally sync specs
    specs_synced = False
    if not skip_specs:
        try:
            from devspec.core.spec_merge import apply_specs  # type: ignore[import-not-found]

            apply_specs(project_root, change_name)
            specs_synced = True
        except Exception:
            pass

    # Create archive directory
    archive_dir = changes_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Generate target name
    date_prefix = datetime.date.today().isoformat()
    target_name = f"{date_prefix}-{change_name}"
    target_path = archive_dir / target_name

    if target_path.exists():
        raise FileExistsError(f"Archive target already exists: {target_path}")

    shutil.move(str(change_dir), str(target_path))

    return ArchiveResult(
        change_name=change_name,
        archive_path=target_path,
        specs_synced=specs_synced,
    )
