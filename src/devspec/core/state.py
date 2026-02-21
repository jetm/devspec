import re
from pathlib import Path

from devspec.core.schema import Schema

TASK_CHECKBOX_RE = re.compile(r"^- \[([ x])\] ", re.MULTILINE)


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


def detect_task_progress(change_dir: Path, tracks: str) -> tuple[int, int]:
    """Count (done, total) task checkboxes in the tracked file."""
    tasks_file = change_dir / tracks
    if not tasks_file.is_file():
        return (0, 0)
    content = tasks_file.read_text(encoding="utf-8")
    matches = TASK_CHECKBOX_RE.findall(content)
    total = len(matches)
    done = sum(1 for m in matches if m == "x")
    return (done, total)
