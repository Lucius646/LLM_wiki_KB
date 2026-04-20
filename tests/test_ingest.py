import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.ingest import ingest_raw_file
from llm_wiki.workspace import init_workspace


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_ingest_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class FakeLlm:
    def infer_article(self, raw_text: str, candidates: list[object]) -> dict[str, object]:
        return {
            "article_slug": "attention-mechanism",
            "article_title": "Attention Mechanism",
            "is_new": False,
        }

    def compile_article(self, **kwargs: object) -> str:
        return (
            "# Attention Mechanism\n\n"
            "> Sources: Test Source, 2026-04-20\n"
            "> Raw: [attention-notes](../../raw/transformers/attention-notes.md)\n\n"
            "## Overview\n\n"
            "Attention routes token interactions.\n"
        )


def test_ingest_updates_existing_article_and_index(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "attention-notes.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# Attention Notes\n\nTransformers use attention.", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeLlm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is True
    assert result.article_path == "wiki/transformers/attention-mechanism.md"
    assert (tmp_path / result.article_path).exists()
    assert "Attention Mechanism" in (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")


def test_ingest_rejects_non_markdown(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "paper.pdf"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("not markdown", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeLlm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is False
    assert "only .md" in result.message.lower()
