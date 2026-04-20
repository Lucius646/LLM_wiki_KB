import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.commands.query import answer_query
from llm_wiki.workspace import init_workspace


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_query_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class FakeQueryLlm:
    def answer_query(self, **kwargs: object) -> str:
        return (
            "Attention helps models relate tokens across positions.\n\n"
            "Sources:\n- wiki/transformers/attention-mechanism.md"
        )


def test_query_reads_wiki_and_returns_console_answer(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Attention Mechanism\n\n## Overview\n\nAttention relates tokens.\n", encoding="utf-8")
    (tmp_path / "wiki" / "index.md").write_text(
        "# Knowledge Base Index\n\n## transformers\n\nTransformer concepts.\n\n"
        "| Article | Summary | Updated |\n"
        "|---------|---------|---------|\n"
        "| [Attention Mechanism](transformers/attention-mechanism.md) | Attention relates tokens. | 2026-04-20 |\n",
        encoding="utf-8",
    )

    result = answer_query(tmp_path, "what does attention do", llm=FakeQueryLlm())

    assert result.ok is True
    assert "relate tokens" in result.answer.lower()
    assert "wiki/transformers/attention-mechanism.md" in result.answer


def test_query_returns_failure_when_no_relevant_wiki_content_exists(tmp_path: Path):
    init_workspace(tmp_path)

    result = answer_query(tmp_path, "what does attention do", llm=FakeQueryLlm())

    assert result.ok is False
    assert "no relevant wiki content found" in result.answer.lower()
