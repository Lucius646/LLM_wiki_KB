import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.lint import lint_workspace
from llm_wiki.wiki.index import upsert_index_entry
from llm_wiki.workspace import init_workspace


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_lint_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_lint_reports_missing_index_entry(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Attention Mechanism\n", encoding="utf-8")

    result = lint_workspace(tmp_path)

    assert result.ok is False
    assert any("missing from index" in issue.lower() for issue in result.issues)


def test_lint_reports_broken_raw_reference(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "# Attention Mechanism\n\n> Sources: Test, 2026-04-20\n> Raw: [missing](../../raw/transformers/missing.md)\n",
        encoding="utf-8",
    )

    result = lint_workspace(tmp_path)

    assert any("raw reference" in issue.lower() for issue in result.issues)


def test_lint_reports_broken_wiki_link(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "# Attention Mechanism\n\n> Sources: Test, 2026-04-20\n> Raw: [raw](../../raw/transformers/source.md)\n\n"
        "## See Also\n\n[Missing](missing-page.md)\n",
        encoding="utf-8",
    )
    raw = tmp_path / "raw" / "transformers" / "source.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("# Source\n", encoding="utf-8")

    result = lint_workspace(tmp_path)

    assert any("wiki link" in issue.lower() for issue in result.issues)


def test_lint_reports_missing_article_metadata(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Attention Mechanism\n\nBody.\n", encoding="utf-8")
    upsert_index_entry(
        tmp_path / "wiki" / "index.md",
        topic="transformers",
        article_title="Attention Mechanism",
        article_path="transformers/attention-mechanism.md",
        summary="Body.",
        updated="2026-04-26",
    )

    result = lint_workspace(tmp_path)

    assert any("missing sources" in issue.lower() for issue in result.issues)
    assert any("missing raw" in issue.lower() for issue in result.issues)


def test_lint_reports_broken_log_source_reference(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "wiki" / "log.md").write_text(
        "# Wiki Log\n\n## [2026-04-26] ingest | raw/transformers/missing.md\n\n"
        "- Updated:\n  - wiki/transformers/missing.md\n",
        encoding="utf-8",
    )

    result = lint_workspace(tmp_path)

    assert any("log references missing raw source" in issue.lower() for issue in result.issues)
    assert any("log references missing wiki page" in issue.lower() for issue in result.issues)


def test_lint_reports_orphan_pages(tmp_path: Path):
    init_workspace(tmp_path)
    raw = tmp_path / "raw" / "transformers" / "source.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("# Source\n", encoding="utf-8")
    linked = tmp_path / "wiki" / "transformers" / "linked.md"
    orphan = tmp_path / "wiki" / "transformers" / "orphan.md"
    linked.parent.mkdir(parents=True)
    linked.write_text(
        "# Linked\n\n> Sources: Test\n> Raw: [source](../../raw/transformers/source.md)\n\n"
        "[Orphan](orphan.md)\n",
        encoding="utf-8",
    )
    orphan.write_text(
        "# Orphan\n\n> Sources: Test\n> Raw: [source](../../raw/transformers/source.md)\n\nBody.\n",
        encoding="utf-8",
    )
    upsert_index_entry(tmp_path / "wiki" / "index.md", "transformers", "Linked", "transformers/linked.md", "Linked.", "2026-04-26")
    upsert_index_entry(tmp_path / "wiki" / "index.md", "transformers", "Orphan", "transformers/orphan.md", "Orphan.", "2026-04-26")

    result = lint_workspace(tmp_path)

    assert any("orphan" in issue.lower() for issue in result.issues)


def test_lint_reports_duplicate_title_candidates(tmp_path: Path):
    init_workspace(tmp_path)
    raw = tmp_path / "raw" / "source.md"
    raw.write_text("# Source\n", encoding="utf-8")
    first = tmp_path / "wiki" / "a" / "duplicate.md"
    second = tmp_path / "wiki" / "b" / "duplicate.md"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("# Duplicate\n\n> Sources: Test\n> Raw: [source](../../raw/source.md)\n", encoding="utf-8")
    second.write_text("# Duplicate\n\n> Sources: Test\n> Raw: [source](../../raw/source.md)\n", encoding="utf-8")

    result = lint_workspace(tmp_path)

    assert any("duplicate" in issue.lower() for issue in result.issues)
