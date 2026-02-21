from pathlib import Path

from devspec.core.schema import load_schema
from devspec.core.state import detect_completed, detect_task_progress


def test_empty_dir(tmp_path: Path):
    schema = load_schema()
    assert detect_completed(schema, tmp_path) == set()


def test_proposal_only(tmp_path: Path):
    (tmp_path / "proposal.md").write_text("content")
    schema = load_schema()
    completed = detect_completed(schema, tmp_path)
    assert completed == {"proposal"}


def test_all_artifacts(tmp_path: Path):
    (tmp_path / "proposal.md").write_text("content")
    (tmp_path / "design.md").write_text("content")
    (tmp_path / "tasks.md").write_text("content")
    # specs uses glob pattern specs/**/*.md
    specs_dir = tmp_path / "specs" / "auth"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("content")
    schema = load_schema()
    completed = detect_completed(schema, tmp_path)
    assert completed == {"proposal", "specs", "design", "tasks"}


def test_glob_pattern_no_match(tmp_path: Path):
    # Create specs dir but no .md files
    (tmp_path / "specs").mkdir()
    schema = load_schema()
    completed = detect_completed(schema, tmp_path)
    assert "specs" not in completed


def test_glob_pattern_nested(tmp_path: Path):
    # specs/**/*.md should match deeply nested files
    nested = tmp_path / "specs" / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "spec.md").write_text("content")
    schema = load_schema()
    completed = detect_completed(schema, tmp_path)
    assert "specs" in completed


class TestDetectTaskProgress:
    def test_no_tasks_file(self, tmp_path: Path):
        assert detect_task_progress(tmp_path, "tasks.md") == (0, 0)

    def test_all_checked(self, tmp_path: Path):
        (tmp_path / "tasks.md").write_text("## 1. Setup\n\n- [x] 1.1 Done\n- [x] 1.2 Also done\n")
        assert detect_task_progress(tmp_path, "tasks.md") == (2, 2)

    def test_mixed_checkboxes(self, tmp_path: Path):
        (tmp_path / "tasks.md").write_text("## 1. Setup\n\n- [x] 1.1 Done\n- [ ] 1.2 Not done\n- [x] 1.3 Done\n")
        assert detect_task_progress(tmp_path, "tasks.md") == (2, 3)

    def test_no_checkboxes(self, tmp_path: Path):
        (tmp_path / "tasks.md").write_text("## 1. Setup\n\nJust some text.\n")
        assert detect_task_progress(tmp_path, "tasks.md") == (0, 0)
