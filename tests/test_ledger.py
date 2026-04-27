import json
import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.ledger import empty_ledger, write_ledger


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
