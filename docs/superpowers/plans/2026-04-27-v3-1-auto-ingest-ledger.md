# V3.1 Auto Ingest Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This project forbids subagents unless the user explicitly asks for them. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ingest` with no arguments automatically process new or changed supported files under `raw/`, using a visible git-tracked ledger to skip unchanged sources.

**Architecture:** Add a focused ledger module for JSON schema, hashing, raw discovery, and success/failure records. Keep the existing v3 single-file ingest pipeline as the core primitive, then add a thin auto-ingest orchestration layer that scans pending raw files and calls the single-file primitive sequentially. Update `init` to create `wiki/ingest-ledger.json`, and update the REPL so bare `ingest` means auto-ingest instead of showing usage.

**Tech Stack:** Python 3.11, stdlib `json`, `hashlib`, `datetime`, existing git CLI helpers, pytest.

---

## Existing-Solution Check

This check was performed before implementation. It includes local adjacent projects, mature libraries, and open-source tools. No external repository clone is required for v3.1.

### Local Adjacent Projects

- `E:\LuciusProject\WikiLLM\llmwiki\ingest.py`
  - Relevant ideas: raw source ingestion, changed file list, wiki log update, git commit after ingest.
  - Not adopted directly: it copies sources into topic directories, uses topic classification, creates source summary pages, and supports richer parser flows. That conflicts with this project's v3 philosophy that `raw/` is already the user interface and should not require user-side classification.
- `E:\LuciusProject\WikiLLM\llmwiki\version_history.py`
  - Relevant ideas: rely on git history for rollback/version inspection.
  - Adopted conceptually: keep ledger state git-tracked and rollback-friendly.
- `E:\LuciusProject\MindOS\app\lib\organize-history.ts`
  - Relevant ideas: record per-file organize results with status and source files.
  - Not adopted directly: it stores UI history in localStorage, not workspace git state.
- `E:\LuciusProject\MindOS\app\lib\core\inbox.ts`
  - Relevant ideas: distinguish saved/skipped results, continue processing per file, archive processed files.
  - Not adopted directly: v3.1 does not add Inbox or move raw files after processing. It only records processing state.

### Mature Libraries And Tools Checked

- DVC tracks data files with Git-versioned `.dvc` metadata containing content hashes such as `md5`, and also maintains internal cache/state files for hash optimization. Useful precedent: content hashes are the right primitive for skip/change detection. Not adopted: DVC introduces `.dvc/` internals, external cache semantics, and a data-versioning workflow far heavier than this CLI.
- git-annex uses content-addressed keys and metadata attached to file content. Useful precedent: content identity is separate from filename. Not adopted: it is a large external storage system and changes how files are managed.
- joblib `Memory` caches function outputs on the filesystem based on input arguments. Useful precedent: skip recomputation when inputs match. Not adopted: it creates cache directories and pickled output artifacts, and its hash stability is tied to Python/joblib serialization rather than a simple raw file digest.
- Snakemake uses hashes of steps, parameters, software stacks, and raw inputs for workflow caching. Useful precedent: hash all inputs relevant to a computed result. Not adopted: workflow engine semantics are unnecessary for one sequential raw scan.
- Airflow task state/retry concepts distinguish success, failed, skipped, and retryable work. Useful precedent: record failures separately from successes. Not adopted: a DAG scheduler is far beyond the project scope.

References checked:

- DVC `.dvc` files: `https://doc.dvc.org/user-guide/project-structure/dvc-files`
- git-annex: `https://git-annex.branchable.com/`
- joblib Memory: `https://joblib.readthedocs.io/en/latest/memory.html`
- Snakemake between-workflow caching: `https://snakemake.readthedocs.io/en/stable/executing/caching.html`
- Airflow task concepts: `https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html`

### Decision

- Use Python stdlib only: `hashlib`, `json`, `datetime`, `pathlib`.
- Keep `wiki/ingest-ledger.json` visible and git-tracked.
- Store raw file `sha256` values explicitly.
- Keep `sources` for successful ingests and `failures` for diagnostic state.
- Continue processing after per-file failure, but never mark failed files as successfully ingested.
- Do not add DVC, git-annex, joblib, Snakemake, Airflow, SQLite, localStorage, or hidden cache directories.

## File Structure

- Create: `src/llm_wiki/ledger.py`
  - Owns ledger schema, read/write, validation, sha256 hashing, raw discovery, pending detection, success/failure record updates.
- Modify: `src/llm_wiki/raw_input.py`
  - Expose a single supported extension set for auto discovery.
- Modify: `src/llm_wiki/models.py`
  - Add small dataclasses for `AutoIngestResult` and possibly ledger entries if useful.
- Modify: `src/llm_wiki/workspace.py`
  - Create `wiki/ingest-ledger.json` during `init`.
  - Include the ledger file in the baseline init commit.
- Modify: `src/llm_wiki/commands/ingest.py`
  - Update single-file ingest to record success in the ledger before the ingest commit.
  - Add `ingest_pending_raw_files()` auto-ingest orchestration.
- Modify: `src/llm_wiki/repl.py`
  - Make bare `ingest` run auto-ingest.
  - Keep `ingest raw/<file>` for single-file ingest.
  - Add a minimal optional skipped expansion flag: `ingest --show-skipped`.
- Modify: `README.md`, `demo/README.md`
  - Document v3.1 behavior and ledger.
- Test: `tests/test_ledger.py`, `tests/test_workspace.py`, `tests/test_ingest.py`, `tests/test_app.py`.

## Behavioral Rules

- Bare `ingest` scans `raw/` recursively.
- Supported files are the v3 extensions only: `.md`, `.txt`, `.html`, `.json`, `.csv`, `.pdf`, `.png`, `.jpg`, `.jpeg`.
- Unsupported files are ignored by auto-ingest, not treated as failures.
- A file is pending when it is absent from `sources` or its current sha256 differs from the recorded sha256.
- A successful ingest writes/updates `sources[raw_path]` and clears `failures[raw_path]`.
- A failed ingest writes/updates `failures[raw_path]`, does not write `sources[raw_path]`, and auto-ingest continues.
- Failure-only ledger updates do not create an ingest commit.
- Each successful raw file remains one managed ingest commit.
- Ledger updates for successful ingest are included in that same commit.

---

### Task 1: Add Ledger File On Init

**Files:**
- Modify: `src/llm_wiki/workspace.py`
- Create: `src/llm_wiki/ledger.py`
- Test: `tests/test_workspace.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write failing init test**

Add to `tests/test_workspace.py`:

```python
def test_init_workspace_creates_ingest_ledger(workspace_root: Path):
    result = init_workspace(workspace_root)

    ledger_path = workspace_root / "wiki" / "ingest-ledger.json"
    assert ledger_path.is_file()
    assert json.loads(ledger_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "sources": {},
        "failures": {},
    }
    assert "wiki/ingest-ledger.json" in result.created
```

Add `import json` if missing.

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_workspace.py::test_init_workspace_creates_ingest_ledger -q
```

Expected: FAIL because `wiki/ingest-ledger.json` is not created.

- [ ] **Step 3: Add ledger constants and empty writer**

Create `src/llm_wiki/ledger.py`:

```python
import json
from pathlib import Path

LEDGER_RELATIVE_PATH = "wiki/ingest-ledger.json"
LEDGER_VERSION = 1


def empty_ledger() -> dict[str, object]:
    return {"version": LEDGER_VERSION, "sources": {}, "failures": {}}


def write_ledger(path: Path, ledger: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Update init workspace**

In `src/llm_wiki/workspace.py`, add:

```python
from llm_wiki.ledger import LEDGER_RELATIVE_PATH, empty_ledger, write_ledger
```

Then create the ledger if missing:

```python
ledger_path = root / LEDGER_RELATIVE_PATH
if not ledger_path.exists():
    write_ledger(ledger_path, empty_ledger())
    created.append(LEDGER_RELATIVE_PATH)
```

Include `ledger_path` in the baseline commit paths:

```python
baseline = commit_paths(root, [raw_dir, index_path, log_path, ledger_path], ...)
```

- [ ] **Step 5: Add ledger unit test for deterministic JSON**

Create `tests/test_ledger.py` with local temp fixture like existing tests and:

```python
def test_write_ledger_writes_stable_json(workspace_root: Path):
    path = workspace_root / "wiki" / "ingest-ledger.json"
    write_ledger(path, empty_ledger())

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "sources": {},
        "failures": {},
    }
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_workspace.py tests/test_ledger.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/workspace.py src/llm_wiki/ledger.py tests/test_workspace.py tests/test_ledger.py
git commit -m "feat: create ingest ledger on init"
```

---

### Task 2: Implement Ledger Read, Hash, Discovery, And Pending Detection

**Files:**
- Modify: `src/llm_wiki/ledger.py`
- Modify: `src/llm_wiki/raw_input.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write failing ledger behavior tests**

Add tests:

```python
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

    result = [path.relative_to(workspace_root).as_posix() for path in discover_supported_raw_files(workspace_root)]

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
        "raw/first.txt": {"sha256": sha256_file(first), "last_ingested_at": "old", "commit": "abc", "article_paths": []},
        "raw/changed.txt": {"sha256": "oldhash", "last_ingested_at": "old", "commit": "abc", "article_paths": []},
    }

    result = [item.relative_path for item in pending_raw_files(workspace_root, ledger)]

    assert result == ["raw/changed.txt"]
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
pytest tests/test_ledger.py -q
```

Expected: FAIL because read/hash/discovery/pending helpers do not exist.

- [ ] **Step 3: Expose supported extensions**

In `src/llm_wiki/raw_input.py`, add:

```python
SUPPORTED_RAW_EXTENSIONS = TEXT_EXTENSIONS | FILE_EXTENSIONS | IMAGE_EXTENSIONS
```

- [ ] **Step 4: Implement ledger helpers**

In `src/llm_wiki/ledger.py`, add:

```python
import hashlib

from llm_wiki.raw_input import SUPPORTED_RAW_EXTENSIONS


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
        (path for path in raw_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_RAW_EXTENSIONS),
        key=lambda path: path.relative_to(root).as_posix(),
    )
```

Add a small pending item dataclass in `models.py` or `ledger.py`:

```python
@dataclass
class PendingRawFile:
    path: Path
    relative_path: str
    sha256: str
```

Then implement:

```python
def pending_raw_files(root: Path, ledger: dict[str, object]) -> list[PendingRawFile]:
    sources = ledger.get("sources", {})
    if not isinstance(sources, dict):
        raise RuntimeError("Invalid ingest ledger schema.")
    pending = []
    for path in discover_supported_raw_files(root):
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        existing = sources.get(relative)
        if not isinstance(existing, dict) or existing.get("sha256") != digest:
            pending.append(PendingRawFile(path=path, relative_path=relative, sha256=digest))
    return pending
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/test_ledger.py tests/test_raw_input.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/ledger.py src/llm_wiki/raw_input.py tests/test_ledger.py
git commit -m "feat: add ingest ledger discovery"
```

---

### Task 3: Record Successful Single-File Ingests In Ledger

**Files:**
- Modify: `src/llm_wiki/commands/ingest.py`
- Modify: `src/llm_wiki/ledger.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write failing single-file ledger test**

Add to `tests/test_ingest.py`:

```python
def test_single_file_ingest_updates_ledger_success_entry(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "note.txt"
    raw_path.write_text("Transformers use attention.", encoding="utf-8")

    result = ingest_raw_file(tmp_path, raw_path, llm=FakeRawLlm(), article_override=None, confirm_new=lambda _: True)

    ledger = json.loads((tmp_path / "wiki" / "ingest-ledger.json").read_text(encoding="utf-8"))
    entry = ledger["sources"]["raw/note.txt"]
    assert result.ok is True
    assert entry["sha256"]
    assert entry["commit"]
    assert entry["article_paths"] == ["wiki/concepts/raw-source.md"]
    assert "raw/note.txt" not in ledger["failures"]
```

Add `import json` if missing.

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_ingest.py::test_single_file_ingest_updates_ledger_success_entry -q
```

Expected: FAIL because `ingest_raw_file()` does not update the ledger.

- [ ] **Step 3: Add ledger success updater**

In `src/llm_wiki/ledger.py`, add:

```python
from datetime import datetime, timezone


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
```

- [ ] **Step 4: Update ingest commit order**

In `ingest_raw_file()`:

1. Read ledger before compiling.
2. After article/log writes but before commit, compute raw sha and write ledger with temporary commit placeholder or commit after commit hash is known.

Use this practical order:

```python
ledger_path = root / LEDGER_RELATIVE_PATH
ledger = read_ledger(ledger_path)
raw_sha = sha256_file(raw_path)
record_success(ledger, relative_path=relative.as_posix(), sha256=raw_sha, commit="", article_paths=article_paths)
write_ledger(ledger_path, ledger)
commit_result = commit_paths(root, [root / "raw", root / "wiki"], commit_message)
if commit_result.committed:
    ledger = read_ledger(ledger_path)
    record_success(ledger, relative_path=relative.as_posix(), sha256=raw_sha, commit=commit_result.commit_hash, article_paths=article_paths)
    write_ledger(ledger_path, ledger)
    commit_paths(root, [ledger_path], f"ledger: record ingest commit\n\nLLM-Wiki-Action: ledger\nLLM-Wiki-Source: {relative.as_posix()}")
```

Then evaluate this against the spec before implementation. If exact same-commit hash in ledger is required, this is impossible without amending the commit after knowing its hash. Prefer `commit: ""` in the same ingest commit or `commit: "see enclosing git commit"` to keep rollback coherent. The implementation should choose one consistent value and tests should assert non-empty only if a second ledger commit is accepted.

**Recommended adjustment:** record `commit: "see enclosing git commit"` in the same ingest commit. This matches existing `wiki/log.md` behavior and keeps rollback coherent without an extra commit.

Concrete implementation:

```python
record_success(
    ledger,
    relative_path=relative.as_posix(),
    sha256=raw_sha,
    commit="see enclosing git commit",
    article_paths=article_paths,
)
write_ledger(ledger_path, ledger)
commit_paths(root, [root / "raw", root / "wiki"], commit_message)
```

- [ ] **Step 5: Adjust test expectation**

Assert:

```python
assert entry["commit"] == "see enclosing git commit"
```

This is aligned with existing audit log semantics.

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_ingest.py tests/test_ledger.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/commands/ingest.py src/llm_wiki/ledger.py tests/test_ingest.py
git commit -m "feat: record raw ingest ledger success"
```

---

### Task 4: Add Auto-Ingest Orchestration And Failure Recording

**Files:**
- Modify: `src/llm_wiki/commands/ingest.py`
- Modify: `src/llm_wiki/ledger.py`
- Modify: `src/llm_wiki/models.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write failing auto-ingest tests**

Add tests:

```python
def test_auto_ingest_processes_new_raw_files_and_skips_unchanged(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "note.txt"
    raw_path.write_text("Transformers use attention.", encoding="utf-8")
    llm = FakeRawLlm()

    first = ingest_pending_raw_files(tmp_path, llm=llm, confirm_new=lambda _: True)
    second = ingest_pending_raw_files(tmp_path, llm=llm, confirm_new=lambda _: True)

    assert first.ok is True
    assert first.ingested == ["raw/note.txt"]
    assert second.ok is True
    assert second.ingested == []
    assert second.skipped == ["raw/note.txt"]


def test_auto_ingest_reprocesses_changed_raw_file(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "note.txt"
    raw_path.write_text("first", encoding="utf-8")
    ingest_pending_raw_files(tmp_path, llm=FakeRawLlm(), confirm_new=lambda _: True)

    raw_path.write_text("second", encoding="utf-8")
    result = ingest_pending_raw_files(tmp_path, llm=FakeRawLlm(), confirm_new=lambda _: True)

    assert result.ingested == ["raw/note.txt"]


def test_auto_ingest_records_failure_and_continues(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "raw" / "bad.txt").write_text("bad", encoding="utf-8")
    (tmp_path / "raw" / "good.txt").write_text("good", encoding="utf-8")
    llm = FakePartiallyFailingLlm(fail_for={"raw/bad.txt"})

    result = ingest_pending_raw_files(tmp_path, llm=llm, confirm_new=lambda _: True)
    ledger = json.loads((tmp_path / "wiki" / "ingest-ledger.json").read_text(encoding="utf-8"))

    assert result.ok is False
    assert result.ingested == ["raw/good.txt"]
    assert result.failed == ["raw/bad.txt"]
    assert "raw/bad.txt" in ledger["failures"]
    assert "raw/bad.txt" not in ledger["sources"]
```

Create `FakePartiallyFailingLlm` by extending `FakeRawLlm` and raising from `plan_ingest()` when `raw_input.relative_path` is in a configured set.

- [ ] **Step 2: Run failing tests**

Run:

```bash
pytest tests/test_ingest.py::test_auto_ingest_processes_new_raw_files_and_skips_unchanged tests/test_ingest.py::test_auto_ingest_reprocesses_changed_raw_file tests/test_ingest.py::test_auto_ingest_records_failure_and_continues -q
```

Expected: FAIL because `ingest_pending_raw_files` does not exist.

- [ ] **Step 3: Add result model**

In `src/llm_wiki/models.py`:

```python
@dataclass
class AutoIngestResult:
    ok: bool
    message: str
    ingested: list[str]
    skipped: list[str]
    failed: list[str]
```

- [ ] **Step 4: Add failure updater**

In `src/llm_wiki/ledger.py`:

```python
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
```

- [ ] **Step 5: Implement auto-ingest**

In `src/llm_wiki/commands/ingest.py`, add:

```python
def ingest_pending_raw_files(
    root: Path,
    llm: object,
    confirm_new,
    show_skipped: bool = False,
) -> AutoIngestResult:
    ledger_path = root / LEDGER_RELATIVE_PATH
    ledger = read_ledger(ledger_path)
    supported_files = discover_supported_raw_files(root)
    pending = pending_raw_files(root, ledger)
    pending_paths = {item.relative_path for item in pending}
    skipped = [
        path.relative_to(root).as_posix()
        for path in supported_files
        if path.relative_to(root).as_posix() not in pending_paths
    ]
    ingested: list[str] = []
    failed: list[str] = []
    for item in pending:
        try:
            result = ingest_raw_file(root, item.path, llm=llm, article_override=None, confirm_new=confirm_new)
        except RuntimeError as exc:
            result = IngestResult(ok=False, message=str(exc))
        if result.ok:
            ingested.append(item.relative_path)
            continue
        ledger = read_ledger(ledger_path)
        record_failure(ledger, relative_path=item.relative_path, sha256=item.sha256, error=result.message)
        write_ledger(ledger_path, ledger)
        failed.append(item.relative_path)
    ok = not failed
    return AutoIngestResult(
        ok=ok,
        message=_build_auto_ingest_message(ingested, skipped, failed, show_skipped),
        ingested=ingested,
        skipped=skipped,
        failed=failed,
    )
```

Important: `ingest_raw_file()` itself reads and writes ledger on success, so auto-ingest should re-read before recording failures to avoid overwriting success records from previous files.

- [ ] **Step 6: Add summary message helper**

```python
def _build_auto_ingest_message(ingested: list[str], skipped: list[str], failed: list[str], show_skipped: bool) -> str:
    lines = [
        f"Auto ingest complete: {len(ingested)} ingested, {len(skipped)} skipped, {len(failed)} failed."
    ]
    if ingested:
        lines.append("Ingested:")
        lines.extend(f"- {path}" for path in ingested)
    if failed:
        lines.append("Failed:")
        lines.extend(f"- {path}" for path in failed)
    if show_skipped and skipped:
        lines.append("Skipped:")
        lines.extend(f"- {path}" for path in skipped)
    return "\n".join(lines)
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
pytest tests/test_ingest.py tests/test_ledger.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/llm_wiki/commands/ingest.py src/llm_wiki/ledger.py src/llm_wiki/models.py tests/test_ingest.py
git commit -m "feat: add automatic raw ingest"
```

---

### Task 5: Wire REPL UX And Docs

**Files:**
- Modify: `src/llm_wiki/repl.py`
- Modify: `README.md`
- Modify: `demo/README.md`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing REPL/help tests**

Add to `tests/test_app.py`:

```python
def test_help_lists_bare_ingest_auto_mode():
    from llm_wiki.repl import HELP_TEXT

    assert "- ingest" in HELP_TEXT
    assert "ingest raw/<file>" in HELP_TEXT
    assert "ingest --show-skipped" in HELP_TEXT
```

If testing `_run_ingest()` directly is practical, add a small test that monkeypatches `llm_wiki.repl.ingest_pending_raw_files` and verifies bare `ingest` calls it.

- [ ] **Step 2: Run failing tests**

Run:

```bash
pytest tests/test_app.py -q
```

Expected: FAIL because help still treats ingest as single-file only.

- [ ] **Step 3: Update REPL imports and help**

In `src/llm_wiki/repl.py`:

```python
from llm_wiki.commands.ingest import ingest_pending_raw_files, ingest_raw_file
```

Update help:

```text
- ingest
- ingest --show-skipped
- ingest raw/<file>
```

- [ ] **Step 4: Update `_run_ingest()`**

Behavior:

```python
show_skipped = "--show-skipped" in args
file_args = [arg for arg in args if arg != "--show-skipped"]
if not file_args:
    result = ingest_pending_raw_files(Path.cwd(), llm=client, confirm_new=self._confirm_new_article, show_skipped=show_skipped)
    print(result.message)
    return
```

If `file_args` exists, keep single-file behavior with `file_args[0]`.

- [ ] **Step 5: Update docs**

README command summary:

```text
- ingest
- ingest --show-skipped
- ingest raw/<file>
```

Mention `wiki/ingest-ledger.json` as a system-maintained file.

Demo README:

```text
ingest
ingest --show-skipped
ingest raw/notes.txt
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_app.py tests/test_ingest.py tests/test_workspace.py tests/test_ledger.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/llm_wiki/repl.py README.md demo/README.md tests/test_app.py
git commit -m "docs: document v3.1 auto ingest workflow"
```

---

## Final Verification

- [ ] Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] Run:

```bash
python -m llm_wiki.app --help
```

Expected: help prints and includes `ingest`, `ingest --show-skipped`, and `ingest raw/<file>`.

- [ ] Run:

```bash
git status --short --branch
```

Expected: clean feature branch/spec branch after commits.

## Release Steps After Implementation

After implementation is complete and verified:

1. Merge the implementation branch back to `main`.
2. Run `pytest -q` and `python -m llm_wiki.app --help` on `main`.
3. Tag `v3.1.0`.
4. Push `main` and `v3.1.0`.

## Known Risks

- The exact commit hash cannot be known before the commit is created. Use `commit: "see enclosing git commit"` in `wiki/ingest-ledger.json` to keep ledger and wiki changes in the same commit, matching `wiki/log.md`.
- Failure-only ledger writes may leave `wiki/ingest-ledger.json` dirty after an auto-ingest run with failures. This is intentional diagnostic state; planning should decide whether to checkpoint it separately later, but v3.1 should not create managed ingest commits for failures.
- Existing dirty-workspace checks may need a narrow adjustment if failure-only ledger state blocks the next ingest. Keep any adjustment specific to `wiki/ingest-ledger.json`.
