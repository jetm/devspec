import os
import re
from pathlib import Path

KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MARKER_FILE = ".devspec"


def get_data_root() -> Path:
    """Return the devspec data root directory, respecting $XDG_DATA_HOME."""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg) / "devspec"
    return Path.home() / ".local" / "share" / "devspec"


def resolve_project_name(start_path: Path) -> str:
    """Walk parent directories from start_path looking for .devspec marker file.

    Reads and strips its content, validates kebab-case.

    Raises:
        FileNotFoundError: If no .devspec marker is found in any parent directory.
        ValueError: If the marker file content is not valid kebab-case.
    """
    current = start_path.resolve()
    while True:
        marker = current / MARKER_FILE
        if marker.is_file():
            name = marker.read_text(encoding="utf-8").strip()
            if not name:
                raise ValueError(f"Empty .devspec marker file at {marker}")
            if not KEBAB_CASE_RE.match(name):
                raise ValueError(
                    f"Invalid project name in {marker}: {name!r}. Must be kebab-case (e.g., 'my-project')."
                )
            return name
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError("No .devspec marker file found in any parent directory.")


def resolve_project_data_dir(project: str | None = None) -> Path:
    """Resolve the project data directory.

    Resolution order:
    1. If --project override is provided, use it directly.
    2. Walk parent directories for .devspec marker file.
    3. Error if neither works.

    Returns the path: <data_root>/<project_name>/

    Raises:
        FileNotFoundError: If no project can be resolved or marker is invalid.
    """
    data_root = get_data_root()
    if project:
        if not KEBAB_CASE_RE.match(project):
            raise FileNotFoundError(f"Invalid project name: {project!r}. Must be kebab-case (e.g., 'my-project').")
        data_dir = data_root / project
        if not data_dir.is_dir():
            raise FileNotFoundError(f"Project not found: {project!r} (expected at {data_dir})")
        return data_dir

    try:
        name = resolve_project_name(Path.cwd())
    except ValueError as e:
        raise FileNotFoundError(str(e)) from e
    data_dir = data_root / name
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Project data directory not found: {data_dir}")
    return data_dir
