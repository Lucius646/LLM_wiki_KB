import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.lint import lint_workspace
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
