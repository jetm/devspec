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


def mark_task(change_dir: Path, tracks: str, task_index: int, done: bool = True) -> Path:
    """Mark a task checkbox as complete or incomplete by 1-based index.

    Args:
        change_dir: Path to the change directory.
        tracks: Relative path to the tasks file (e.g., "tasks.md").
        task_index: 1-based index of the task checkbox to toggle.
        done: True to mark complete ([x]), False to mark incomplete ([ ]).

    Returns:
        Path to the modified tasks file.

    Raises:
        FileNotFoundError: If the tasks file does not exist.
        IndexError: If task_index is out of range.
    """
    tasks_file = change_dir / tracks
    if not tasks_file.exists():
        raise FileNotFoundError(f"Tasks file not found: {tracks}")

    content = tasks_file.read_text(encoding="utf-8")
    checkbox_re = re.compile(r"^(- \[)[ x](\] )", re.MULTILINE)
    matches = list(checkbox_re.finditer(content))

    if task_index < 1 or task_index > len(matches):
        raise IndexError(f"Task index {task_index} out of range (1-{len(matches)})")

    match = matches[task_index - 1]
    mark = "x" if done else " "
    new_content = content[: match.start()] + match.group(1) + mark + match.group(2) + content[match.end() :]
    tasks_file.write_text(new_content, encoding="utf-8")

    return tasks_file
