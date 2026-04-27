import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from llm_wiki.raw_input import SUPPORTED_RAW_EXTENSIONS


LEDGER_RELATIVE_PATH = "wiki/ingest-ledger.json"
LEDGER_VERSION = 1


@dataclass
class PendingRawFile:
    path: Path
    relative_path: str
    sha256: str


def empty_ledger() -> dict[str, object]:
    return {"version": LEDGER_VERSION, "sources": {}, "failures": {}}


def read_ledger(path: Path) -> dict[str, object]:
    if not path.exists():
        return empty_ledger()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid ingest ledger JSON: {exc.msg}") from exc
    if not isinstance(data, dict) or data.get("version") != LEDGER_VERSION:
        raise RuntimeError("Invalid ingest ledger schema.")
    if not isinstance(data.get("sources"), dict) or not isinstance(data.get("failures"), dict):
        raise RuntimeError("Invalid ingest ledger schema.")
    return data


def write_ledger(path: Path, ledger: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_supported_raw_files(root: Path) -> list[Path]:
    raw_dir = root / "raw"
    if not raw_dir.is_dir():
        return []
    return sorted(
        (
            path
            for path in raw_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_RAW_EXTENSIONS
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def pending_raw_files(root: Path, ledger: dict[str, object]) -> list[PendingRawFile]:
    sources = ledger.get("sources", {})
    if not isinstance(sources, dict):
        raise RuntimeError("Invalid ingest ledger schema.")
    pending: list[PendingRawFile] = []
    for path in discover_supported_raw_files(root):
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        existing = sources.get(relative)
        if not isinstance(existing, dict) or existing.get("sha256") != digest:
            pending.append(PendingRawFile(path=path, relative_path=relative, sha256=digest))
    return pending


def record_success(
    ledger: dict[str, object],
    *,
    relative_path: str,
    sha256: str,
    commit: str,
    article_paths: list[str],
) -> None:
    sources = ledger.setdefault("sources", {})
    failures = ledger.setdefault("failures", {})
    if not isinstance(sources, dict) or not isinstance(failures, dict):
        raise RuntimeError("Invalid ingest ledger schema.")
    sources[relative_path] = {
        "sha256": sha256,
        "last_ingested_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "article_paths": article_paths,
    }
    failures.pop(relative_path, None)


def record_failure(
    ledger: dict[str, object],
    *,
    relative_path: str,
    sha256: str,
    error: str,
) -> None:
    failures = ledger.setdefault("failures", {})
    if not isinstance(failures, dict):
        raise RuntimeError("Invalid ingest ledger schema.")
    failures[relative_path] = {
        "sha256": sha256,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
