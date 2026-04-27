import json
import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.ledger import (
    discover_supported_raw_files,
    empty_ledger,
    pending_raw_files,
    read_ledger,
    sha256_file,
    write_ledger,
)


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_ledger_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_write_ledger_writes_stable_json(workspace_root: Path):
    path = workspace_root / "wiki" / "ingest-ledger.json"
    write_ledger(path, empty_ledger())

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "sources": {},
        "failures": {},
    }


def test_read_ledger_rejects_invalid_json(workspace_root: Path):
    path = workspace_root / "wiki" / "ingest-ledger.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Invalid ingest ledger JSON"):
        read_ledger(path)


def test_sha256_file_changes_when_content_changes(workspace_root: Path):
    raw = workspace_root / "raw" / "note.txt"
    raw.parent.mkdir()
    raw.write_text("one", encoding="utf-8")
    first = sha256_file(raw)

    raw.write_text("two", encoding="utf-8")

    assert sha256_file(raw) != first


def test_discover_supported_raw_files_ignores_unsupported(workspace_root: Path):
    raw_dir = workspace_root / "raw"
    raw_dir.mkdir()
    (raw_dir / "a.txt").write_text("a", encoding="utf-8")
    (raw_dir / "b.pdf").write_bytes(b"%PDF")
    (raw_dir / "c.zip").write_bytes(b"zip")

    result = [
        path.relative_to(workspace_root).as_posix()
        for path in discover_supported_raw_files(workspace_root)
    ]

    assert result == ["raw/a.txt", "raw/b.pdf"]


def test_pending_raw_files_returns_new_and_changed_files(workspace_root: Path):
    raw_dir = workspace_root / "raw"
    raw_dir.mkdir()
    first = raw_dir / "first.txt"
    changed = raw_dir / "changed.txt"
    first.write_text("same", encoding="utf-8")
    changed.write_text("new content", encoding="utf-8")
    ledger = empty_ledger()
    ledger["sources"] = {
        "raw/first.txt": {
            "sha256": sha256_file(first),
            "last_ingested_at": "old",
            "commit": "abc",
            "article_paths": [],
        },
        "raw/changed.txt": {
            "sha256": "oldhash",
            "last_ingested_at": "old",
            "commit": "abc",
            "article_paths": [],
        },
    }

    result = [item.relative_path for item in pending_raw_files(workspace_root, ledger)]

    assert result == ["raw/changed.txt"]
