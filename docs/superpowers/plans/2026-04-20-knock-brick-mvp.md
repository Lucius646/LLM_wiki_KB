# Knock-Brick MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python REPL tool for a Karpathy-style LLM wiki MVP with `init`, `ingest`, `query`, and `lint`, using the current directory as a workspace.

**Architecture:** The tool stays split between a thin REPL shell and small workflow modules. Workspace state, wiki file I/O, provider config, and command workflows live in separate modules so `v2` can replace the ingest compiler without rewriting the CLI.

**Tech Stack:** Python 3.11+, `prompt_toolkit`, `rich`, `pytest`, stdlib (`pathlib`, `json`, `dataclasses`, `datetime`, `re`, `textwrap`, `typing`)

---

## File Structure

### New files

- `pyproject.toml`
- `src/llm_wiki/__init__.py`
- `src/llm_wiki/app.py`
- `src/llm_wiki/repl.py`
- `src/llm_wiki/models.py`
- `src/llm_wiki/workspace.py`
- `src/llm_wiki/config.py`
- `src/llm_wiki/llm.py`
- `src/llm_wiki/commands/__init__.py`
- `src/llm_wiki/commands/init.py`
- `src/llm_wiki/commands/ingest.py`
- `src/llm_wiki/commands/query.py`
- `src/llm_wiki/commands/lint.py`
- `src/llm_wiki/wiki/__init__.py`
- `src/llm_wiki/wiki/article.py`
- `src/llm_wiki/wiki/index.py`
- `src/llm_wiki/wiki/log.py`
- `src/llm_wiki/wiki/search.py`
- `src/llm_wiki/prompts/infer_article.md`
- `src/llm_wiki/prompts/compile_article.md`
- `src/llm_wiki/prompts/answer_query.md`
- `tests/test_app.py`
- `tests/test_workspace.py`
- `tests/test_config.py`
- `tests/test_wiki_io.py`
- `tests/test_ingest.py`
- `tests/test_query.py`
- `tests/test_lint.py`
- `demo/README.md`
- `demo/workspace/raw/transformers/attention-notes.md`
- `demo/workspace/raw/transformers/self-attention-history.md`
- `demo/workspace/raw/state-space-models/mamba-notes.md`

### Modified files

- `README.md`
- `.gitignore`

## Shared Implementation Rules

- Keep all workspace-facing paths under the current working directory. Reject paths outside the active workspace.
- `init` creates missing files only. Never overwrite an existing `wiki/index.md` or `wiki/log.md`.
- `ingest` only accepts `raw/.../*.md`.
- `query` is read-only.
- `lint` in `v1` only checks index entries, wiki links, and raw links.
- All commands should return structured result objects first, then render them in the REPL layer.
- Network-dependent LLM calls must be behind a small interface so tests use fakes instead of real APIs.

### Task 1: Bootstrap The Python Package And REPL Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/llm_wiki/__init__.py`
- Create: `src/llm_wiki/app.py`
- Create: `src/llm_wiki/repl.py`
- Create: `src/llm_wiki/models.py`
- Create: `tests/test_app.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing REPL smoke tests**

```python
from llm_wiki.repl import parse_command


def test_parse_query_command_preserves_rest_of_line():
    command = parse_command('query transformer attention solves what problem')
    assert command.name == 'query'
    assert command.args == ['transformer attention solves what problem']


def test_parse_exit_command():
    command = parse_command('exit')
    assert command.name == 'exit'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_app.py`
Expected: FAIL with import errors because `llm_wiki.repl` does not exist yet.

- [ ] **Step 3: Write the minimal package skeleton**

```python
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    name: str
    args: list[str]


def parse_command(line: str) -> ParsedCommand:
    head, _, tail = line.strip().partition(" ")
    if head == "query" and tail:
        return ParsedCommand(name=head, args=[tail])
    return ParsedCommand(name=head, args=tail.split() if tail else [])
```

Also add:
- `pyproject.toml` with package metadata, console entry point `llm-wiki = llm_wiki.app:main`, and dependencies `prompt_toolkit`, `rich`
- `app.py` with a `main()` that constructs and runs a `WikiRepl`
- `.gitignore` entries for `.venv/`, `.pytest_cache/`, `__pycache__/`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_app.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src/llm_wiki/__init__.py src/llm_wiki/app.py src/llm_wiki/repl.py src/llm_wiki/models.py tests/test_app.py
git commit -m "feat: scaffold llm wiki python repl"
```

### Task 2: Add Workspace Detection And Initialization

**Files:**
- Create: `src/llm_wiki/workspace.py`
- Create: `src/llm_wiki/commands/init.py`
- Create: `tests/test_workspace.py`
- Modify: `src/llm_wiki/models.py`
- Modify: `src/llm_wiki/repl.py`

- [ ] **Step 1: Write the failing workspace tests**

```python
from pathlib import Path

from llm_wiki.workspace import detect_workspace, init_workspace


def test_init_workspace_creates_expected_files(tmp_path: Path):
    result = init_workspace(tmp_path)
    assert (tmp_path / "raw").is_dir()
    assert (tmp_path / "wiki").is_dir()
    assert (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8").startswith("# Knowledge Base Index")
    assert (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8").startswith("# Wiki Log")
    assert result.created


def test_detect_workspace_requires_raw_and_wiki(tmp_path: Path):
    status = detect_workspace(tmp_path)
    assert status.initialized is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_workspace.py`
Expected: FAIL because `workspace.py` and result models do not exist.

- [ ] **Step 3: Implement workspace status and init**

```python
def init_workspace(root: Path) -> InitResult:
    created: list[str] = []
    raw_dir = root / "raw"
    wiki_dir = root / "wiki"
    index_path = wiki_dir / "index.md"
    log_path = wiki_dir / "log.md"
    for path in (raw_dir, wiki_dir):
        if not path.exists():
            path.mkdir(parents=True)
            created.append(str(path.relative_to(root)))
    if not index_path.exists():
        index_path.write_text("# Knowledge Base Index\n", encoding="utf-8")
        created.append("wiki/index.md")
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n", encoding="utf-8")
        created.append("wiki/log.md")
    return InitResult(created=created)
```

Also add:
- `detect_workspace()` returning initialized state and basic counts
- `init` command handler that uses the current directory
- REPL `status` command wired to workspace detection

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_workspace.py tests/test_app.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/workspace.py src/llm_wiki/commands/init.py src/llm_wiki/models.py src/llm_wiki/repl.py tests/test_workspace.py
git commit -m "feat: add workspace initialization and status"
```

### Task 3: Add Config Loading And OpenAI-Compatible Client Settings

**Files:**
- Create: `src/llm_wiki/config.py`
- Create: `src/llm_wiki/llm.py`
- Create: `tests/test_config.py`
- Modify: `src/llm_wiki/models.py`
- Modify: `src/llm_wiki/repl.py`

- [ ] **Step 1: Write the failing config tests**

```python
from pathlib import Path

from llm_wiki.config import load_config, normalize_base_url


def test_normalize_base_url_trims_whitespace_and_trailing_slash():
    assert normalize_base_url(" https://example.com/v1/ ") == "https://example.com/v1"


def test_load_config_requires_model_and_api_key(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"provider":{"protocol":"openai_compatible","model":"","api_key":""}}', encoding="utf-8")
    errors = load_config().errors
    assert "model" in errors[0].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_config.py`
Expected: FAIL because config loader does not exist yet.

- [ ] **Step 3: Implement config loading and client boundary**

```python
def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/") if url else ""


def get_default_config_path() -> Path:
    home = Path.home()
    return home / ".llm-wiki" / "config.json"
```

Also implement:
- a `ProviderConfig` dataclass with `protocol`, `model`, `api_key`, `base_url`
- `load_config()` returning config data plus validation errors
- a small `LlmClient` protocol in `llm.py`
- a factory that builds an OpenAI-compatible client from config, without hardcoding `base_url` when it is empty
- REPL startup header showing config availability and selected model

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_config.py tests/test_workspace.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/config.py src/llm_wiki/llm.py src/llm_wiki/models.py src/llm_wiki/repl.py tests/test_config.py
git commit -m "feat: add llm wiki config loading"
```

### Task 4: Implement Wiki Index, Log, And Article I/O

**Files:**
- Create: `src/llm_wiki/wiki/article.py`
- Create: `src/llm_wiki/wiki/index.py`
- Create: `src/llm_wiki/wiki/log.py`
- Create: `src/llm_wiki/wiki/search.py`
- Create: `tests/test_wiki_io.py`
- Modify: `src/llm_wiki/models.py`

- [ ] **Step 1: Write the failing wiki I/O tests**

```python
from pathlib import Path

from llm_wiki.workspace import init_workspace
from llm_wiki.wiki.index import upsert_index_entry, read_index_entries
from llm_wiki.wiki.log import append_log_entry


def test_upsert_index_entry_creates_topic_section(tmp_path: Path):
    init_workspace(tmp_path)
    upsert_index_entry(
        tmp_path / "wiki" / "index.md",
        topic="transformers",
        article_title="Attention Mechanism",
        article_path="transformers/attention-mechanism.md",
        summary="How attention routes token interactions.",
        updated="2026-04-20",
    )
    content = (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "## transformers" in content
    assert "[Attention Mechanism](transformers/attention-mechanism.md)" in content


def test_append_log_entry_adds_operation_block(tmp_path: Path):
    init_workspace(tmp_path)
    append_log_entry(tmp_path / "wiki" / "log.md", "2026-04-20", "ingest", "Attention Mechanism", ["Updated: Self-Attention"])
    content = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "## [2026-04-20] ingest | Attention Mechanism" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_wiki_io.py`
Expected: FAIL because wiki helpers do not exist yet.

- [ ] **Step 3: Implement deterministic markdown I/O helpers**

```python
def append_log_entry(log_path: Path, date: str, action: str, title: str, extra_lines: list[str] | None = None) -> None:
    lines = [f"## [{date}] {action} | {title}", *[f"- {line}" for line in extra_lines or []], ""]
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
```

Also implement:
- `ArticleDocument` parsing/writing for wiki pages
- index entry parsing into structured rows
- `search_index()` returning candidate article paths for query and ingest matching
- idempotent `upsert_index_entry()`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_wiki_io.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/wiki/article.py src/llm_wiki/wiki/index.py src/llm_wiki/wiki/log.py src/llm_wiki/wiki/search.py src/llm_wiki/models.py tests/test_wiki_io.py
git commit -m "feat: add wiki markdown io helpers"
```

### Task 5: Implement `ingest` With Existing-First Concept Selection

**Files:**
- Create: `src/llm_wiki/prompts/infer_article.md`
- Create: `src/llm_wiki/prompts/compile_article.md`
- Create: `tests/test_ingest.py`
- Modify: `src/llm_wiki/commands/ingest.py`
- Modify: `src/llm_wiki/wiki/article.py`
- Modify: `src/llm_wiki/wiki/index.py`
- Modify: `src/llm_wiki/wiki/log.py`
- Modify: `src/llm_wiki/repl.py`
- Modify: `src/llm_wiki/llm.py`

- [ ] **Step 1: Write the failing ingest tests**

```python
from pathlib import Path

from llm_wiki.commands.ingest import ingest_raw_file
from llm_wiki.workspace import init_workspace


class FakeLlm:
    def infer_article(self, raw_text, candidates):
        return {"article_slug": "attention-mechanism", "article_title": "Attention Mechanism", "is_new": False}

    def compile_article(self, **kwargs):
        return "# Attention Mechanism\n\n> Sources: Test Source, 2026-04-20\n> Raw: [attention-notes](../../raw/transformers/attention-notes.md)\n\n## Overview\n\nAttention routes token interactions.\n"


def test_ingest_updates_existing_article_and_index(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "attention-notes.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("# Attention Notes\n\nTransformers use attention.", encoding="utf-8")
    result = ingest_raw_file(tmp_path, raw_path, llm=FakeLlm(), article_override=None, confirm_new=lambda _: True)
    assert result.article_path == "wiki/transformers/attention-mechanism.md"
    assert (tmp_path / result.article_path).exists()
    assert "Attention Mechanism" in (tmp_path / "wiki" / "index.md").read_text(encoding="utf-8")


def test_ingest_rejects_non_markdown(tmp_path: Path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "transformers" / "paper.pdf"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("not markdown", encoding="utf-8")
    result = ingest_raw_file(tmp_path, raw_path, llm=FakeLlm(), article_override=None, confirm_new=lambda _: True)
    assert result.ok is False
    assert "only .md" in result.message.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_ingest.py`
Expected: FAIL because `ingest_raw_file` and prompt-backed client methods do not exist.

- [ ] **Step 3: Implement single-target concept compilation**

```python
def ensure_workspace_raw_markdown(root: Path, raw_path: Path) -> str | None:
    relative = raw_path.relative_to(root)
    if relative.parts[0] != "raw" or raw_path.suffix.lower() != ".md":
        return "Unsupported raw file type: only .md is supported in v1."
    return None
```

Also implement:
- `ingest_raw_file()` orchestrating validation, existing-first article inference, optional manual override, new-article confirmation, article write, index update, and log append
- prompt loading from `src/llm_wiki/prompts/*.md`
- an `LlmClient` interface with `infer_article()` and `compile_article()`
- REPL command support:
  - `ingest raw/topic/file.md`
  - `ingest raw/topic/file.md --article attention-mechanism`
- clear failure result when inference cannot determine a target article

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_ingest.py tests/test_wiki_io.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/prompts/infer_article.md src/llm_wiki/prompts/compile_article.md src/llm_wiki/commands/ingest.py src/llm_wiki/wiki/article.py src/llm_wiki/wiki/index.py src/llm_wiki/wiki/log.py src/llm_wiki/repl.py src/llm_wiki/llm.py tests/test_ingest.py
git commit -m "feat: add single-target concept ingest"
```

### Task 6: Implement Read-Only `query`

**Files:**
- Create: `src/llm_wiki/prompts/answer_query.md`
- Create: `tests/test_query.py`
- Modify: `src/llm_wiki/commands/query.py`
- Modify: `src/llm_wiki/wiki/search.py`
- Modify: `src/llm_wiki/repl.py`
- Modify: `src/llm_wiki/llm.py`

- [ ] **Step 1: Write the failing query tests**

```python
from pathlib import Path

from llm_wiki.commands.query import answer_query
from llm_wiki.workspace import init_workspace


class FakeQueryLlm:
    def answer_query(self, **kwargs):
        return "Attention helps models relate tokens across positions.\n\nSources:\n- wiki/transformers/attention-mechanism.md"


def test_query_reads_wiki_and_returns_console_answer(tmp_path: Path):
    init_workspace(tmp_path)
    article = tmp_path / "wiki" / "transformers" / "attention-mechanism.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Attention Mechanism\n\n## Overview\n\nAttention relates tokens.\n", encoding="utf-8")
    (tmp_path / "wiki" / "index.md").write_text(
        "# Knowledge Base Index\n\n## transformers\n\nTransformer concepts.\n\n| Article | Summary | Updated |\n|---------|---------|---------|\n| [Attention Mechanism](transformers/attention-mechanism.md) | Attention relates tokens. | 2026-04-20 |\n",
        encoding="utf-8",
    )
    result = answer_query(tmp_path, "what does attention do", llm=FakeQueryLlm())
    assert result.ok is True
    assert "relate tokens" in result.answer.lower()
    assert "wiki/transformers/attention-mechanism.md" in result.answer
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_query.py`
Expected: FAIL because `answer_query` is not implemented.

- [ ] **Step 3: Implement read-only wiki query**

```python
def answer_query(root: Path, question: str, llm: LlmClient) -> QueryResult:
    candidates = search_index(root / "wiki" / "index.md", question)
    if not candidates:
        return QueryResult(ok=False, answer="No relevant wiki content found. Ingest more material first.")
    documents = [load_article(root / "wiki" / candidate.path) for candidate in candidates[:3]]
    answer = llm.answer_query(question=question, documents=documents)
    return QueryResult(ok=True, answer=answer)
```

Also implement:
- candidate ranking with a simple lexical score from title and summary
- REPL rendering for `query`
- no file writes anywhere in the command path

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_query.py tests/test_ingest.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/prompts/answer_query.md src/llm_wiki/commands/query.py src/llm_wiki/wiki/search.py src/llm_wiki/repl.py src/llm_wiki/llm.py tests/test_query.py
git commit -m "feat: add read only wiki query"
```

### Task 7: Implement Structural `lint`

**Files:**
- Create: `tests/test_lint.py`
- Modify: `src/llm_wiki/commands/lint.py`
- Modify: `src/llm_wiki/wiki/index.py`
- Modify: `src/llm_wiki/wiki/article.py`
- Modify: `src/llm_wiki/repl.py`

- [ ] **Step 1: Write the failing lint tests**

```python
from pathlib import Path

from llm_wiki.commands.lint import lint_workspace
from llm_wiki.workspace import init_workspace


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_lint.py`
Expected: FAIL because `lint_workspace` does not exist.

- [ ] **Step 3: Implement deterministic structural lint**

```python
def lint_workspace(root: Path) -> LintResult:
    issues: list[str] = []
    issues.extend(find_missing_index_entries(root))
    issues.extend(find_broken_wiki_links(root))
    issues.extend(find_broken_raw_links(root))
    return LintResult(ok=not issues, issues=issues)
```

Also implement:
- index coverage check against actual `wiki/**/*.md` excluding `index.md` and `log.md`
- wiki link extraction from article bodies and `Sources` metadata
- raw link extraction from `Raw` metadata
- REPL summary formatting with total issue count

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest -q tests/test_lint.py tests/test_wiki_io.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/commands/lint.py src/llm_wiki/wiki/index.py src/llm_wiki/wiki/article.py src/llm_wiki/repl.py tests/test_lint.py
git commit -m "feat: add structural wiki lint"
```

### Task 8: Finish Demo Assets, README, And End-To-End Verification

**Files:**
- Create: `demo/README.md`
- Create: `demo/workspace/raw/transformers/attention-notes.md`
- Create: `demo/workspace/raw/transformers/self-attention-history.md`
- Create: `demo/workspace/raw/state-space-models/mamba-notes.md`
- Modify: `README.md`

- [ ] **Step 1: Write the failing documentation and smoke verification checklist**

Document the expected demo flow before editing files:

```text
1. cd demo/workspace
2. llm-wiki
3. init
4. ingest raw/transformers/attention-notes.md
5. query what does attention do in transformers
6. lint
```

Add one test-like smoke assertion to `tests/test_app.py`:

```python
def test_help_lists_core_commands():
    from llm_wiki.repl import HELP_TEXT
    assert "init" in HELP_TEXT
    assert "ingest" in HELP_TEXT
    assert "query" in HELP_TEXT
    assert "lint" in HELP_TEXT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_app.py`
Expected: FAIL until help text is finalized.

- [ ] **Step 3: Write final demo and README updates**

Update `README.md` to:
- reposition the repo as a workflow demo plus thin CLI
- explain the workspace model
- explain `v1` boundaries
- show the demo flow

Write `demo/README.md` with:
- workspace prep steps
- expected `init -> ingest -> query -> lint` sequence
- notes about manual raw placement

Create small demo raw Markdown sources that are text-only and URL-preserving.

- [ ] **Step 4: Run full verification**

Run: `pytest -q`
Expected: PASS

Run: `python -m llm_wiki.app --help`
Expected: shows the tool name or exits cleanly with a REPL/help entry point

Manual check:
- from `demo/workspace`, run the REPL
- confirm startup header shows workspace and config state
- run `init`
- run one `ingest`
- run one `query`
- run `lint`

- [ ] **Step 5: Commit**

```bash
git add README.md demo/README.md demo/workspace/raw/transformers/attention-notes.md demo/workspace/raw/transformers/self-attention-history.md demo/workspace/raw/state-space-models/mamba-notes.md tests/test_app.py
git commit -m "feat: ship knock brick llm wiki mvp"
```

## Review Notes

- Use fake LLM clients in tests. Do not make real network calls in `pytest`.
- Keep prompt files plain Markdown so prompt iteration stays separate from Python flow logic.
- Do not add `query --save`, URL ingestion, PDF parsing, or semantic lint during this plan.
- If `ingest` implementation starts growing beyond one target article, stop and defer that work to `v2`.
