from pathlib import Path
import shutil

import pytest

from llm_wiki.commands.init import run_init_command
from llm_wiki.repl import WikiRepl
from llm_wiki.workspace import detect_workspace, init_workspace


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / "_workspace_tmp"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_init_workspace_creates_expected_files(workspace_root: Path):
    result = init_workspace(workspace_root)
    assert (workspace_root / "raw").is_dir()
    assert (workspace_root / "wiki").is_dir()
    assert (workspace_root / "wiki" / "index.md").read_text(encoding="utf-8").startswith(
        "# Knowledge Base Index"
    )
    assert (workspace_root / "wiki" / "log.md").read_text(encoding="utf-8").startswith(
        "# Wiki Log"
    )
    assert result.created


def test_detect_workspace_requires_raw_and_wiki(workspace_root: Path):
    status = detect_workspace(workspace_root)
    assert status.initialized is False


def test_detect_workspace_reports_initialized_counts(workspace_root: Path):
    init_workspace(workspace_root)
    status = detect_workspace(workspace_root)
    assert status.initialized is True
    assert status.raw_file_count == 0
    assert status.wiki_page_count == 0


def test_init_command_uses_current_directory(workspace_root: Path, monkeypatch):
    monkeypatch.chdir(workspace_root)

    result = run_init_command()

    assert (workspace_root / "raw").is_dir()
    assert (workspace_root / "wiki").is_dir()
    assert result.created


def test_repl_status_reports_workspace_state(workspace_root: Path, monkeypatch, capsys):
    monkeypatch.chdir(workspace_root)
    run_init_command()
    inputs = iter(["status", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    WikiRepl().run()

    output = capsys.readouterr().out.lower()
    assert "initialized: yes" in output
