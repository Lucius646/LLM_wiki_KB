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


class FakeRawLlm:
    def __init__(self):
        self.plan_raw_inputs = []
        self.compile_raw_inputs = []

    def plan_ingest(self, **kwargs: object) -> dict[str, object]:
        raw_input = kwargs.get("raw_input")
        self.plan_raw_inputs.append(raw_input)
        return {
            "summary": "Raw source compiles into a durable wiki concept.",
            "changes": [
                {
                    "action": "create",
                    "topic": "concepts",
                    "slug": "raw-source",
                    "title": "Raw Source",
                    "reason": "Captures the source evidence.",
                }
            ],
            "warnings": [],
        }

    def compile_page_change(self, **kwargs: object) -> str:
        raw_input = kwargs.get("raw_input")
        self.compile_raw_inputs.append(raw_input)
        return (
            "# Raw Source\n\n"
            f"> Sources: {kwargs['reason']}\n"
            f"> Raw: [source](../../{raw_input.relative_path})\n\n"
            "## Overview\n\n"
            "Compiled from raw evidence.\n"
        )

    def generate_commit_message(self, **kwargs: object) -> str:
        return "ingest: compile raw source"


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
    assert "- Planned:" in log_text
    assert "- Updated:" in log_text
    assert "- Created:" in log_text
    assert "- Warnings:" in log_text
    assert "- Commit:" in log_text
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


def test_ingest_rejects_file_outside_raw(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "note.txt"
    raw_path.write_text("not under raw", encoding="utf-8")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeV2Llm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is False
    assert "under raw/" in result.message.lower()


def test_ingest_accepts_txt_at_raw_root(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "note.txt"
    raw_path.write_text("Transformers use attention.", encoding="utf-8")
    llm = FakeRawLlm()

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=llm,
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is True
    assert result.article_path == "wiki/concepts/raw-source.md"
    assert llm.plan_raw_inputs[0].kind == "text"
    assert llm.plan_raw_inputs[0].relative_path == "raw/note.txt"
    assert llm.compile_raw_inputs[0].text == "Transformers use attention."


def test_ingest_accepts_pdf_at_raw_root(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "paper.pdf"
    raw_path.write_bytes(b"%PDF-1.4")
    llm = FakeRawLlm()

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=llm,
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is True
    assert result.article_path == "wiki/concepts/raw-source.md"
    assert llm.plan_raw_inputs[0].kind == "file"
    assert llm.plan_raw_inputs[0].relative_path == "raw/paper.pdf"
    assert llm.compile_raw_inputs[0].mime_type == "application/pdf"


def test_ingest_rejects_unsupported_raw_type(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "archive.zip"
    raw_path.write_bytes(b"zip")

    result = ingest_raw_file(
        tmp_path,
        raw_path,
        llm=FakeRawLlm(),
        article_override=None,
        confirm_new=lambda _: True,
    )

    assert result.ok is False
    assert "unsupported raw file type" in result.message.lower()
