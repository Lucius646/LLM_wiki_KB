# V2 Git-Backed Multi-Page Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This branch's `AGENTS.md` forbids subagents unless the user explicitly asks for them. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build v2 as a git-backed, low-intervention, auditable multi-page wiki compiler.

**Architecture:** Keep the v1 CLI shape, but add small focused modules for git operations and multi-page ingest planning. `init` creates a git-backed workspace, `ingest` auto-applies conservative 1-3 page changes and commits them, `undo` reverts the latest managed ingest commit, and `lint` gains audit/log checks.

**Tech Stack:** Python 3.11, stdlib `subprocess` for git CLI integration, existing Markdown wiki files, pytest.

---

## Confirmed V2 Scope

- `init` requires git as a system dependency.
- `init` runs `git init` when the active workspace is not already a git repo.
- `init` creates `raw/`, `wiki/`, `wiki/index.md`, and `wiki/log.md`, then commits the baseline when changes exist.
- `ingest` defaults to no human confirmation.
- `ingest` can automatically create new wiki pages.
- `ingest` updates a conservative range of 1-3 highly relevant wiki pages.
- `ingest` generates an internal plan before writing pages.
- `ingest` writes structured Markdown audit details to `wiki/log.md`.
- `ingest` automatically commits changed `raw/` and `wiki/` files.
- If `raw/` or `wiki/` have pending changes before ingest, create an automatic checkpoint commit first.
- If files outside `raw/` or `wiki/` have pending changes before ingest, block ingest.
- `undo` uses git, not a hidden database.
- `undo` reverts the latest commit with `LLM-Wiki-Action: ingest`.
- No `.llm-wiki/runs` directory.
- No URL/PDF import, embeddings, GUI, MCP, semantic lint, or web clipper.

## File Structure

- Create: `src/llm_wiki/git.py`
  - Git CLI wrapper: availability, repository detection, init, status parsing, staged commits, finding managed commits, revert.
- Modify: `src/llm_wiki/models.py`
  - Add result dataclasses for git status, commit result, multi-page ingest plan, page change, and undo result.
- Modify: `src/llm_wiki/workspace.py`
  - Extend `init_workspace` to initialize git and commit baseline.
- Modify: `src/llm_wiki/commands/init.py`
  - Preserve current command shape while returning richer initialization information.
- Modify: `src/llm_wiki/repl.py`
  - Update help text, init output, ingest behavior, and add `undo`.
- Modify: `src/llm_wiki/llm.py`
  - Add methods for multi-page plan generation, page compilation, and commit-message generation.
- Create: `src/llm_wiki/prompts/plan_ingest.md`
  - Prompt for conservative 1-3 page ingest plan JSON.
- Create: `src/llm_wiki/prompts/compile_page_change.md`
  - Prompt for compiling one planned page change.
- Create: `src/llm_wiki/prompts/commit_message.md`
  - Prompt for a concise commit subject/body while preserving required trailers.
- Modify: `src/llm_wiki/commands/ingest.py`
  - Replace single-target ingest path with auto multi-page ingest while preserving `--article` only if still useful for tests/backcompat.
- Modify: `src/llm_wiki/wiki/log.py`
  - Add structured Markdown audit entry writer.
- Modify: `src/llm_wiki/commands/lint.py`
  - Add v2 structural lint for required article metadata and log references.
- Create: `src/llm_wiki/commands/undo.py`
  - Implements `undo` command using git revert of the latest managed ingest commit.
- Modify/Create tests:
  - `tests/test_git.py`
  - `tests/test_workspace.py`
  - `tests/test_ingest.py`
  - `tests/test_undo.py`
  - `tests/test_lint.py`
  - `tests/test_app.py`

## Commit Message Contract

Every managed commit must include a machine-readable trailer:

```text
LLM-Wiki-Action: init|checkpoint|ingest|undo
```

Ingest commits must also include:

```text
LLM-Wiki-Source: raw/<topic>/<file>.md
```

The LLM may generate the human-readable subject and summary, but code appends and validates the trailers.

---

### Task 1: Add Git Workspace Foundation

**Files:**
- Create: `src/llm_wiki/git.py`
- Modify: `src/llm_wiki/models.py`
- Modify: `src/llm_wiki/workspace.py`
- Modify: `src/llm_wiki/commands/init.py`
- Modify: `src/llm_wiki/repl.py`
- Test: `tests/test_git.py`
- Test: `tests/test_workspace.py`

- [ ] **Step 1: Write failing git wrapper tests**

Add tests covering:

```python
def test_git_init_creates_repository(tmp_path):
    ensure_git_available()
    init_git_repo(tmp_path)
    assert (tmp_path / ".git").exists()


def test_git_status_classifies_raw_wiki_and_other_changes(tmp_path):
    init_git_repo(tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "wiki").mkdir()
    (tmp_path / "raw" / "note.md").write_text("raw\n", encoding="utf-8")
    (tmp_path / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    status = get_git_status(tmp_path)
    assert status.raw_wiki_changes
    assert status.other_changes
```

- [ ] **Step 2: Run failing git tests**

Run: `pytest tests/test_git.py -q`

Expected: FAIL because `llm_wiki.git` does not exist.

- [ ] **Step 3: Implement minimal git wrapper**

Create `src/llm_wiki/git.py` with small functions:

```python
def ensure_git_available() -> None: ...
def is_git_repo(root: Path) -> bool: ...
def init_git_repo(root: Path) -> None: ...
def get_git_status(root: Path) -> GitStatus: ...
def commit_paths(root: Path, paths: list[Path], message: str) -> GitCommitResult: ...
```

Use `subprocess.run(..., cwd=root, text=True, capture_output=True)` and raise `RuntimeError` with stderr on failure.

- [ ] **Step 4: Run git tests**

Run: `pytest tests/test_git.py -q`

Expected: PASS.

- [ ] **Step 5: Write failing init tests**

Extend `tests/test_workspace.py`:

```python
def test_init_workspace_initializes_git_repo(workspace_root):
    result = init_workspace(workspace_root)
    assert (workspace_root / ".git").exists()
    assert result.git_initialized is True


def test_init_workspace_creates_baseline_commit(workspace_root):
    init_workspace(workspace_root)
    log = run_git(workspace_root, ["log", "--oneline"]).stdout
    assert log.strip()
```

- [ ] **Step 6: Implement git-backed init**

Update `InitResult` with:

```python
git_initialized: bool = False
baseline_committed: bool = False
warnings: list[str] | None = None
```

Update `init_workspace` to:

- call `ensure_git_available`
- run `git init` if needed
- create v1 files
- commit `raw/`, `wiki/index.md`, `wiki/log.md` when there are changes
- include `LLM-Wiki-Action: init` in commit message

- [ ] **Step 7: Update REPL init output**

Print whether git was initialized and whether baseline was committed.

- [ ] **Step 8: Run focused tests**

Run: `pytest tests/test_git.py tests/test_workspace.py tests/test_app.py -q`

Expected: PASS.

- [ ] **Step 9: Commit task**

```bash
git add src/llm_wiki/git.py src/llm_wiki/models.py src/llm_wiki/workspace.py src/llm_wiki/commands/init.py src/llm_wiki/repl.py tests/test_git.py tests/test_workspace.py tests/test_app.py
git commit -m "feat: add git-backed workspace init"
```

---

### Task 2: Add Conservative Multi-Page Ingest

**Files:**
- Modify: `src/llm_wiki/models.py`
- Modify: `src/llm_wiki/llm.py`
- Modify: `src/llm_wiki/commands/ingest.py`
- Modify: `src/llm_wiki/wiki/log.py`
- Create: `src/llm_wiki/prompts/plan_ingest.md`
- Create: `src/llm_wiki/prompts/compile_page_change.md`
- Create: `src/llm_wiki/prompts/commit_message.md`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write failing multi-page ingest tests**

Use a fake LLM that returns a two-page plan:

```python
class FakeV2Llm:
    def plan_ingest(self, **kwargs):
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

    def compile_page_change(self, **kwargs):
        return f"# {kwargs['title']}\n\n> Sources: Test\n> Raw: [source](../../raw/transformers/source.md)\n\nBody.\n"

    def generate_commit_message(self, **kwargs):
        return "ingest: compile self-attention source"
```

Assert:

- both wiki pages exist
- index contains both entries
- `wiki/log.md` contains plan summary, updated/created pages, source path
- git log contains `LLM-Wiki-Action: ingest`

- [ ] **Step 2: Run failing ingest tests**

Run: `pytest tests/test_ingest.py -q`

Expected: FAIL because v2 methods are not implemented.

- [ ] **Step 3: Add ingest plan models**

Add dataclasses:

```python
@dataclass
class PageChangePlan:
    action: str
    topic: str
    slug: str
    title: str
    reason: str


@dataclass
class IngestPlan:
    summary: str
    changes: list[PageChangePlan]
    warnings: list[str]
```

- [ ] **Step 4: Add LLM methods**

Add methods to `LlmClient` and `OpenAICompatibleClient`:

```python
def plan_ingest(self, **kwargs: object) -> dict[str, object]: ...
def compile_page_change(self, **kwargs: object) -> str: ...
def generate_commit_message(self, **kwargs: object) -> str: ...
```

`plan_ingest` must parse JSON and enforce 1-3 changes.

- [ ] **Step 5: Add prompts**

`plan_ingest.md` must require:

- JSON only
- 1-3 page changes
- prefer updating existing pages
- create pages only for distinct durable concepts
- no broad reorganization

`compile_page_change.md` must require complete Markdown article output.

`commit_message.md` must require a concise subject and no trailers.

- [ ] **Step 6: Implement multi-page ingest**

Update `ingest_raw_file` flow:

1. Validate raw path.
2. Check git dirty state.
3. If only raw/wiki changes exist, checkpoint before ingest.
4. If other changes exist, fail.
5. Ask LLM for conservative ingest plan.
6. Compile each planned page.
7. Write pages.
8. Upsert index entries.
9. Append structured audit entry to `wiki/log.md`.
10. Commit touched raw/wiki files with required trailers.

- [ ] **Step 7: Remove default new-page confirmation**

Keep the function parameter only if needed for backward compatibility, but do not prompt in normal v2 ingest.

- [ ] **Step 8: Run focused ingest tests**

Run: `pytest tests/test_ingest.py -q`

Expected: PASS.

- [ ] **Step 9: Run related tests**

Run: `pytest tests/test_ingest.py tests/test_workspace.py tests/test_app.py -q`

Expected: PASS.

- [ ] **Step 10: Commit task**

```bash
git add src/llm_wiki/models.py src/llm_wiki/llm.py src/llm_wiki/commands/ingest.py src/llm_wiki/wiki/log.py src/llm_wiki/prompts/plan_ingest.md src/llm_wiki/prompts/compile_page_change.md src/llm_wiki/prompts/commit_message.md tests/test_ingest.py
git commit -m "feat: add conservative multi-page ingest"
```

---

### Task 3: Add Git-Backed Undo

**Files:**
- Modify: `src/llm_wiki/git.py`
- Create: `src/llm_wiki/commands/undo.py`
- Modify: `src/llm_wiki/repl.py`
- Modify: `src/llm_wiki/models.py`
- Test: `tests/test_undo.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing undo tests**

Create a temp git workspace with:

- an init commit
- an ingest commit containing `LLM-Wiki-Action: ingest`
- changed wiki content

Assert:

```python
result = undo_last_ingest(root)
assert result.ok is True
assert "reverted" in result.message.lower()
assert "LLM-Wiki-Action: undo" in git_log_body
```

Also test no ingest commit:

```python
result = undo_last_ingest(root)
assert result.ok is False
assert "no llm-wiki ingest commit" in result.message.lower()
```

- [ ] **Step 2: Run failing undo tests**

Run: `pytest tests/test_undo.py -q`

Expected: FAIL because undo module does not exist.

- [ ] **Step 3: Implement managed commit search**

In `git.py`, add:

```python
def find_latest_managed_commit(root: Path, action: str) -> str | None: ...
def revert_commit(root: Path, commit: str, message: str) -> GitCommitResult: ...
```

Search commits using `git log --format=%H%x00%B%x00END` and match exact trailer lines.

- [ ] **Step 4: Implement undo command**

Create `commands/undo.py`:

```python
def undo_last_ingest(root: Path) -> UndoResult:
    ...
```

Rules:

- fail if not git repo
- fail if workspace has uncommitted changes
- find latest `LLM-Wiki-Action: ingest`
- run `git revert --no-edit <hash>`
- amend or create revert message with `LLM-Wiki-Action: undo`

- [ ] **Step 5: Wire REPL command**

Update `HELP_TEXT` with `undo`.

Route `undo` to `undo_last_ingest(Path.cwd())`.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_undo.py tests/test_app.py -q`

Expected: PASS.

- [ ] **Step 7: Commit task**

```bash
git add src/llm_wiki/git.py src/llm_wiki/commands/undo.py src/llm_wiki/repl.py src/llm_wiki/models.py tests/test_undo.py tests/test_app.py
git commit -m "feat: add git-backed ingest undo"
```

---

### Task 4: Add V2 Audit And Lint Checks

**Files:**
- Modify: `src/llm_wiki/wiki/log.py`
- Modify: `src/llm_wiki/commands/lint.py`
- Test: `tests/test_lint.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write failing audit format tests**

Assert `wiki/log.md` includes:

```markdown
## [YYYY-MM-DD] ingest | raw/transformers/source.md

- Summary:
- Planned:
- Updated:
- Created:
- Warnings:
- Commit:
```

- [ ] **Step 2: Write failing lint tests**

Add tests for:

- article missing `> Sources:` is reported
- article missing `> Raw:` is reported
- log references missing raw source are reported
- orphan pages are report-only issues with clear wording
- duplicate title/slug candidates are report-only issues

- [ ] **Step 3: Run failing lint tests**

Run: `pytest tests/test_lint.py tests/test_ingest.py -q`

Expected: FAIL for new v2 checks.

- [ ] **Step 4: Implement structured audit writer**

Add function:

```python
def append_ingest_audit_entry(
    log_path: Path,
    *,
    date: str,
    source: str,
    summary: str,
    planned: list[str],
    updated: list[str],
    created: list[str],
    warnings: list[str],
    commit: str,
) -> None: ...
```

- [ ] **Step 5: Implement lint checks**

Add functions:

```python
def find_missing_article_metadata(root: Path) -> list[str]: ...
def find_broken_log_references(root: Path) -> list[str]: ...
def find_orphan_pages(root: Path) -> list[str]: ...
def find_duplicate_candidates(root: Path) -> list[str]: ...
```

Keep all checks deterministic and file-based. Do not call the LLM from lint.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_lint.py tests/test_ingest.py -q`

Expected: PASS.

- [ ] **Step 7: Commit task**

```bash
git add src/llm_wiki/wiki/log.py src/llm_wiki/commands/lint.py tests/test_lint.py tests/test_ingest.py
git commit -m "feat: add v2 audit and lint checks"
```

---

### Task 5: Documentation And Smoke Verification

**Files:**
- Modify: `README.md`
- Modify: `demo/README.md`
- Modify: `docs/superpowers/lightweight-v2-workflow.md`
- Test: `tests/test_app.py`

- [ ] **Step 1: Update README command summary**

Document:

```text
init
status
ingest raw/<topic>/<file>.md
query <question>
lint
undo
help
exit
```

Explain git requirement and managed commit trailers.

- [ ] **Step 2: Update demo notes**

Show v2 flow:

```text
init
ingest raw/transformers/self-attention-history.md
lint
undo
```

- [ ] **Step 3: Update lightweight workflow**

Replace the old human-confirmation wording with:

```text
raw source -> internal ingest plan -> auto-apply -> audit/log -> git commit
```

- [ ] **Step 4: Run full test suite**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Run CLI help smoke test**

Run: `python -m llm_wiki.app --help`

Expected: help includes `undo` and v2 command summary.

- [ ] **Step 6: Commit task**

```bash
git add README.md demo/README.md docs/superpowers/lightweight-v2-workflow.md tests/test_app.py
git commit -m "docs: document v2 git-backed workflow"
```

---

## Final Verification

- [ ] Run: `pytest -q`
  - Expected: all tests pass.
- [ ] Run: `python -m llm_wiki.app --help`
  - Expected: help prints successfully and includes `undo`.
- [ ] Run: `git log --oneline -5`
  - Expected: task commits are present on `v2-multi-page-ingest`.
- [ ] Run: `git status --short --branch`
  - Expected: clean branch except intentionally uncommitted files, if any.

## Known Risks

- Git must exist on PATH. Tests should skip git-dependent cases only if git is absent; product `init` should fail clearly.
- `git revert` can conflict if later commits changed the same files. `undo` should report the conflict and stop rather than trying to resolve it.
- LLM-generated plans may be malformed. The parser must validate JSON shape and change count before writing any files.
- Automatic checkpointing can still commit user raw/wiki drafts. This is intentional per v2 design, but messages must make that visible.
