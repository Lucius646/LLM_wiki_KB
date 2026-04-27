import json
from pathlib import Path


LEDGER_RELATIVE_PATH = "wiki/ingest-ledger.json"
LEDGER_VERSION = 1


def empty_ledger() -> dict[str, object]:
    return {"version": LEDGER_VERSION, "sources": {}, "failures": {}}


def write_ledger(path: Path, ledger: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
