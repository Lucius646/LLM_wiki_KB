import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.workspace import init_workspace
from llm_wiki.wiki.article import ArticleDocument, load_article, save_article
from llm_wiki.wiki.index import read_index_entries, upsert_index_entry
from llm_wiki.wiki.log import append_log_entry
from llm_wiki.wiki.search import search_index


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_wiki_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_upsert_index_entry_creates_topic_section(tmp_path: Path):
    init_workspace(tmp_path)
    upsert_index_entry(
        tmp_path / "wiki" / "index.md",
        topic="transformers",
        article_title="Attention Mechanism",
        article_path="transformers/attention-mechanism.md",
        summary="How attention routes token interactions.",
        updated="2026-04-20",
    )
    content = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "## transformers" in content
    assert "[Attention Mechanism](transformers/attention-mechanism.md)" in content


def test_append_log_entry_adds_operation_block(tmp_path: Path):
    init_workspace(tmp_path)
    append_log_entry(
        tmp_path / "wiki" / "log.md",
        "2026-04-20",
        "ingest",
        "Attention Mechanism",
        ["Updated: Self-Attention"],
    )
    content = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "## [2026-04-20] ingest | Attention Mechanism" in content


def test_read_index_entries_parses_upserted_rows(tmp_path: Path):
    init_workspace(tmp_path)
    index_path = tmp_path / "wiki" / "index.md"
    upsert_index_entry(
        index_path,
        topic="transformers",
        article_title="Attention Mechanism",
        article_path="transformers/attention-mechanism.md",
        summary="How attention routes token interactions.",
        updated="2026-04-20",
    )

    entries = read_index_entries(index_path)

    assert len(entries) == 1
    assert entries[0].topic == "transformers"
    assert entries[0].title == "Attention Mechanism"
    assert entries[0].path == "transformers/attention-mechanism.md"


def test_article_document_round_trip(tmp_path: Path):
    init_workspace(tmp_path)
    article_path = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    document = ArticleDocument(
        title="Attention Mechanism",
        sources_line="Test Source, 2026-04-20",
        raw_line="[attention-notes](../../raw/transformers/attention-notes.md)",
        body="## Overview\n\nAttention routes token interactions.\n",
    )

    save_article(article_path, document)
    loaded = load_article(article_path)

    assert loaded.title == "Attention Mechanism"
    assert "Attention routes token interactions." in loaded.body
    assert "attention-notes" in loaded.raw_line


def test_search_index_matches_title_and_summary(tmp_path: Path):
    init_workspace(tmp_path)
    index_path = tmp_path / "wiki" / "index.md"
    upsert_index_entry(
        index_path,
        topic="transformers",
        article_title="Attention Mechanism",
        article_path="transformers/attention-mechanism.md",
        summary="How attention routes token interactions.",
        updated="2026-04-20",
    )
    upsert_index_entry(
        index_path,
        topic="state-space-models",
        article_title="Mamba",
        article_path="state-space-models/mamba.md",
        summary="Selective state space model.",
        updated="2026-04-20",
    )

    results = search_index(index_path, "token attention")

    assert results
    assert results[0].path == "transformers/attention-mechanism.md"
