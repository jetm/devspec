from pathlib import Path

from devspec.core.schema import Schema


def detect_completed(schema: Schema, change_dir: Path) -> set[str]:
    """Detect which artifacts are completed by checking file existence in change_dir."""
    completed: set[str] = set()
    for artifact in schema.artifacts:
        pattern = artifact.generates
        if "*" in pattern:
            if list(change_dir.glob(pattern)):
                completed.add(artifact.id)
        else:
            if (change_dir / pattern).exists():
                completed.add(artifact.id)
    return completed
