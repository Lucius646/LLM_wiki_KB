import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.ingest import ingest_raw_file
from llm_wiki.git import run_git
from llm_wiki.workspace import init_workspace


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_ingest_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class FakeV2Llm:
    def plan_ingest(self, **kwargs: object) -> dict[str, object]:
        return {
            "summary": "Self-attention source updates attention and creates self-attention.",
            "changes": [
                {
                    "action": "update",
                    "topic": "transformers",
                    "slug": "attention-mechanism",
                    "title": "Attention Mechanism",
                    "reason": "Adds motivation for attention.",
                },
                {
                    "action": "create",
                    "topic": "transformers",
                    "slug": "self-attention",
                    "title": "Self-Attention",
                    "reason": "Introduces a distinct concept.",
                },
            ],
            "warnings": [],
        }

    def compile_page_change(self, **kwargs: object) -> str:
        return (
            f"# {kwargs['title']}\n\n"
            "> Sources: Test Source, 2026-04-20\n"
            "> Raw: [attention-notes](../../raw/transformers/attention-notes.md)\n\n"
            "## Overview\n\n"
            f"{kwargs['reason']}\n"
        )

    def generate_commit_message(self, **kwargs: object) -> str:
        return "ingest: compile self-attention source"


def test_ingest_updates_multiple_pages_index_log_and_git(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "attention-notes.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# Attention Notes\n\nTransformers use attention.", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeV2Llm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is True
    assert result.article_path == "wiki/transformers/attention-mechanism.md"
    assert set(result.article_paths) == {
        "wiki/transformers/attention-mechanism.md",
        "wiki/transformers/self-attention.md",
    }
    assert (tmp_path / "wiki" / "transformers" / "attention-mechanism.md").exists()
    assert (tmp_path / "wiki" / "transformers" / "self-attention.md").exists()

    index_text = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "Attention Mechanism" in index_text
    assert "Self-Attention" in index_text

    log_text = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "Self-attention source updates attention" in log_text
    assert "raw/transformers/attention-notes.md" in log_text
    assert "wiki/transformers/attention-mechanism.md" in log_text
    assert "wiki/transformers/self-attention.md" in log_text

    git_log = run_git(tmp_path, ["log", "--format=%B", "-2"]).stdout
    assert "LLM-Wiki-Action: ingest" in git_log
    assert "LLM-Wiki-Source: raw/transformers/attention-notes.md" in git_log
    assert "LLM-Wiki-Action: checkpoint" in git_log


def test_ingest_blocks_when_non_wiki_files_are_dirty(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "attention-notes.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# Attention Notes\n\nTransformers use attention.", encoding="utf-8")
    (tmp_path / "scratch.txt").write_text("local scratch\n", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeV2Llm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is False
    assert "outside raw/ and wiki/" in result.message.lower()


def test_ingest_rejects_non_markdown(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "paper.pdf"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("not markdown", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeV2Llm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is False
    assert "only .md" in result.message.lower()
