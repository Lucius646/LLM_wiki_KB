import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.raw_input import build_raw_input


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_raw_input_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_build_raw_input_accepts_file_at_raw_root(workspace_root: Path):
    raw = workspace_root / "raw" / "paper.txt"
    raw.parent.mkdir()
    raw.write_text("hello", encoding="utf-8")

    result = build_raw_input(workspace_root, raw)

    assert result.ok is True
    assert result.relative_path == "raw/paper.txt"
    assert result.mime_type == "text/plain"
    assert result.kind == "text"
    assert result.text == "hello"


def test_build_raw_input_accepts_pdf_file(workspace_root: Path):
    raw = workspace_root / "raw" / "paper.pdf"
    raw.parent.mkdir()
    raw.write_bytes(b"%PDF-1.4 test")

    result = build_raw_input(workspace_root, raw)

    assert result.ok is True
    assert result.kind == "file"
    assert result.mime_type == "application/pdf"


def test_build_raw_input_accepts_image_file(workspace_root: Path):
    raw = workspace_root / "raw" / "shot.png"
    raw.parent.mkdir()
    raw.write_bytes(b"png")

    result = build_raw_input(workspace_root, raw)

    assert result.ok is True
    assert result.kind == "image"
    assert result.mime_type == "image/png"


def test_build_raw_input_rejects_file_outside_raw(workspace_root: Path):
    outside = workspace_root / "paper.txt"
    outside.write_text("hello", encoding="utf-8")

    result = build_raw_input(workspace_root, outside)

    assert result.ok is False
    assert "under raw/" in result.message.lower()


def test_build_raw_input_rejects_unsupported_type(workspace_root: Path):
    raw = workspace_root / "raw" / "archive.zip"
    raw.parent.mkdir()
    raw.write_bytes(b"zip")

    result = build_raw_input(workspace_root, raw)

    assert result.ok is False
    assert "unsupported raw file type" in result.message.lower()
