import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.git import ensure_git_available, get_git_status, init_git_repo


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_git_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_git_init_creates_repository(workspace_root: Path):
    ensure_git_available()
    init_git_repo(workspace_root)

    assert (workspace_root / ".git").exists()


def test_git_status_classifies_raw_wiki_and_other_changes(workspace_root: Path):
    ensure_git_available()
    init_git_repo(workspace_root)
    (workspace_root / "raw").mkdir()
    (workspace_root / "wiki").mkdir()
    (workspace_root / "raw" / "note.md").write_text("raw\n", encoding="utf-8")
    (workspace_root / "scratch.txt").write_text("scratch\n", encoding="utf-8")

    status = get_git_status(workspace_root)

    assert status.raw_wiki_changes
    assert status.other_changes


def test_git_available_reports_clear_error(monkeypatch):
    import llm_wiki.git as git_module

    def fail_run(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(git_module.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError, match="Git is required"):
        ensure_git_available()
