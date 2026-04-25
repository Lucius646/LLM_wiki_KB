import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.undo import undo_last_ingest
from llm_wiki.git import commit_paths, run_git
from llm_wiki.workspace import init_workspace


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_undo_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_undo_reverts_latest_llm_wiki_ingest_commit(workspace_root: Path):
    init_workspace(workspace_root)
    article = workspace_root / "wiki" / "transformers" / "self-attention.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Self-Attention\n", encoding="utf-8")
    commit_paths(
        workspace_root,
        [workspace_root / "wiki"],
        "ingest: compile self-attention\n\n"
        "LLM-Wiki-Action: ingest\n"
        "LLM-Wiki-Source: raw/transformers/source.md",
    )

    result = undo_last_ingest(workspace_root)

    assert result.ok is True
    assert "reverted" in result.message.lower()
    assert not article.exists()
    log = run_git(workspace_root, ["log", "--format=%B", "-1"]).stdout
    assert "LLM-Wiki-Action: undo" in log


def test_undo_reports_when_no_ingest_commit_exists(workspace_root: Path):
    init_workspace(workspace_root)

    result = undo_last_ingest(workspace_root)

    assert result.ok is False
    assert "no llm-wiki ingest commit" in result.message.lower()


def test_undo_blocks_dirty_workspace(workspace_root: Path):
    init_workspace(workspace_root)
    article = workspace_root / "wiki" / "transformers" / "self-attention.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Self-Attention\n", encoding="utf-8")
    commit_paths(
        workspace_root,
        [workspace_root / "wiki"],
        "ingest: compile self-attention\n\n"
        "LLM-Wiki-Action: ingest\n"
        "LLM-Wiki-Source: raw/transformers/source.md",
    )
    (workspace_root / "wiki" / "dirty.md").write_text("# Dirty\n", encoding="utf-8")

    result = undo_last_ingest(workspace_root)

    assert result.ok is False
    assert "uncommitted changes" in result.message.lower()
