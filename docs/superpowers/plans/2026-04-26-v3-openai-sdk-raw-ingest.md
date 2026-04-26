# V3 OpenAI SDK Raw Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This project forbids subagents unless the user explicitly asks for them. Steps use checkbox (`- [ ]`) syntax for tracking.

## Implementation Status

Implemented on `feature/v3-multimodal-raw-ingest`:

- `c35e4fb feat: add openai provider protocol`
- `4f80448 feat: add raw input abstraction`
- `8677401 feat: add openai responses llm adapter`
- `0d6f5ca feat: support format-agnostic raw ingest`

Documentation and final verification are tracked in the current Task 5 commit.

**Goal:** Build v3 around two changes: migrate the primary OpenAI path to the official OpenAI SDK Responses API, and let `raw/` accept more file formats without requiring user-side topic classification or preprocessing.

**Architecture:** Keep the v2 git-backed ingest pipeline, but replace the primary OpenAI transport with a focused adapter using `openai.OpenAI().responses.create`. Introduce a `RawInput` abstraction that represents text, image, and file inputs; `ingest raw/<file>` validates files under `raw/`, builds a `RawInput`, and passes it through the same LLM plan -> page compile -> audit -> commit pipeline. Legacy `openai_compatible` remains a text-only fallback.

**Tech Stack:** Python 3.11, official `openai` Python SDK, OpenAI Responses API, stdlib `mimetypes`/`base64`, existing pytest suite.

---

## Existing-Solution Check

- Official SDK/API: Use the official `openai` Python SDK and Responses API. OpenAI docs show `responses.create` accepts text, image, and file inputs; file inputs use `input_file`, images use `input_image`.
- Mature library: Python stdlib `mimetypes` is enough for initial MIME detection. Do not add `python-magic` unless tests reveal stdlib is inadequate.
- Open-source/reference: No external clone is required for this plan. The adjacent `MindOS` project has richer import/conversion flows, but v3 intentionally does not copy that pipeline because the product decision is "raw is the interface" and LLM handles understanding.
- Do not keep hand-written OpenAI HTTP as the primary OpenAI implementation. It remains only as a legacy OpenAI-compatible fallback for text.

References:

- OpenAI Responses API: `https://platform.openai.com/docs/api-reference/responses`
- OpenAI file inputs: `https://platform.openai.com/docs/guides/pdf-files`
- OpenAI image inputs: `https://platform.openai.com/docs/guides/images-vision`

## Confirmed V3 Scope

- `raw/` is the user interface.
- `raw/` no longer requires topic folders.
- `raw/<file>` is valid.
- Nested raw paths remain valid, but they are source identity only, not topic truth.
- Wiki topic/path comes from the LLM ingest plan.
- Keep v2 features: git-backed init, conservative multi-page ingest, audit log, undo, lint.
- Add first-stage support for `.md`, `.txt`, `.html`, `.json`, `.csv`, `.pdf`, `.png`, `.jpg`, `.jpeg`.
- Do not add `capture`, `inbox`, batch ingest, directory ingest, RAG, GUI, MCP, or visible normalization pipeline.

## File Structure

- Modify: `pyproject.toml`
  - Add dependency: `openai`.
- Modify: `README.md`
  - Document v3 scope, SDK requirement, and supported raw formats.
- Modify: `src/llm_wiki/config.py`
  - Allow `provider.protocol` values `openai` and `openai_compatible`.
- Modify: `src/llm_wiki/models.py`
  - Add `RawInput`, `RawInputPart`, and provider capability models.
- Create: `src/llm_wiki/raw_input.py`
  - Build raw input parts from files under `raw/`.
- Modify: `src/llm_wiki/llm.py`
  - Add OpenAI SDK Responses adapter.
  - Keep legacy compatible chat adapter for text-only fallback.
- Modify: `src/llm_wiki/commands/ingest.py`
  - Accept supported non-`.md` files.
  - Stop deriving wiki topic from raw path.
  - Pass `RawInput` into LLM planning and compilation.
- Modify: `src/llm_wiki/prompts/plan_ingest.md`
  - Clarify that raw path is source identity and only weak context.
- Modify: `src/llm_wiki/prompts/compile_page_change.md`
  - Clarify source may be text, image, PDF, or file input.
- Modify: `tests/test_config.py`
- Modify: `tests/test_llm.py`
- Create: `tests/test_raw_input.py`
- Modify: `tests/test_ingest.py`
- Modify: `tests/test_app.py`

---

### Task 1: Add OpenAI SDK Dependency And Provider Protocol

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/llm_wiki/config.py`
- Modify: `src/llm_wiki/models.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Add tests:

```python
def test_config_accepts_openai_protocol(config_file):
    config_file.write_text(
        '{"provider":{"protocol":"openai","model":"gpt-5.5","api_key":"sk-test"}}',
        encoding="utf-8",
    )
    result = load_config()
    assert result.errors == []
    assert result.provider.protocol == "openai"


def test_config_still_accepts_openai_compatible(config_file):
    config_file.write_text(
        '{"provider":{"protocol":"openai_compatible","model":"gpt-5.4","api_key":"sk-test","base_url":"https://example.com/v1"}}',
        encoding="utf-8",
    )
    result = load_config()
    assert result.errors == []
    assert result.provider.protocol == "openai_compatible"
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_config.py -q`

Expected: FAIL because config currently only allows `openai_compatible`.

- [ ] **Step 3: Add SDK dependency**

Update `pyproject.toml`:

```toml
dependencies = [
  "openai",
  "prompt_toolkit",
  "rich",
]
```

- [ ] **Step 4: Update config validation**

Allow:

```python
SUPPORTED_PROTOCOLS = {"openai", "openai_compatible"}
```

Default protocol should become `openai`, because v3's primary path is official OpenAI SDK.

Compatibility note: if old config omits `protocol`, it now means `openai`. Users who need old compatible endpoint must set `protocol: "openai_compatible"`.

- [ ] **Step 5: Run config tests**

Run: `pytest tests/test_config.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/llm_wiki/config.py src/llm_wiki/models.py tests/test_config.py
git commit -m "feat: add openai provider protocol"
```

---

### Task 2: Add RawInput File Abstraction

**Files:**
- Modify: `src/llm_wiki/models.py`
- Create: `src/llm_wiki/raw_input.py`
- Test: `tests/test_raw_input.py`

- [ ] **Step 1: Write failing raw input tests**

Create tests for:

```python
def test_build_raw_input_accepts_file_at_raw_root(tmp_path):
    raw = tmp_path / "raw" / "paper.txt"
    raw.parent.mkdir()
    raw.write_text("hello", encoding="utf-8")
    result = build_raw_input(tmp_path, raw)
    assert result.relative_path == "raw/paper.txt"
    assert result.mime_type == "text/plain"
    assert result.kind == "text"
    assert result.text == "hello"


def test_build_raw_input_accepts_pdf_file(tmp_path):
    raw = tmp_path / "raw" / "paper.pdf"
    raw.parent.mkdir()
    raw.write_bytes(b"%PDF-1.4 test")
    result = build_raw_input(tmp_path, raw)
    assert result.kind == "file"
    assert result.mime_type == "application/pdf"


def test_build_raw_input_accepts_image_file(tmp_path):
    raw = tmp_path / "raw" / "shot.png"
    raw.parent.mkdir()
    raw.write_bytes(b"png")
    result = build_raw_input(tmp_path, raw)
    assert result.kind == "image"
    assert result.mime_type == "image/png"


def test_build_raw_input_rejects_file_outside_raw(tmp_path):
    outside = tmp_path / "paper.txt"
    outside.write_text("hello", encoding="utf-8")
    result = build_raw_input(tmp_path, outside)
    assert result.ok is False
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_raw_input.py -q`

Expected: FAIL because `llm_wiki.raw_input` does not exist.

- [ ] **Step 3: Add models**

Add dataclasses:

```python
@dataclass
class RawInput:
    ok: bool
    root: Path
    path: Path
    relative_path: str
    mime_type: str
    kind: str
    text: str = ""
    message: str = ""

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()
```

Allowed kinds:

```text
text
file
image
unsupported
```

- [ ] **Step 4: Implement raw_input.py**

Rules:

- Must be inside active workspace.
- Must be under `raw/`.
- Must be a file.
- Text extensions: `.md`, `.txt`, `.html`, `.json`, `.csv`.
- File extensions: `.pdf`.
- Image extensions: `.png`, `.jpg`, `.jpeg`.
- Use `mimetypes.guess_type`, with explicit fallback map for these extensions.
- Text files read as UTF-8.
- No summarization or conversion.

- [ ] **Step 5: Run raw input tests**

Run: `pytest tests/test_raw_input.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/llm_wiki/models.py src/llm_wiki/raw_input.py tests/test_raw_input.py
git commit -m "feat: add raw input abstraction"
```

---

### Task 3: Add OpenAI Responses Adapter

**Files:**
- Modify: `src/llm_wiki/llm.py`
- Modify: `src/llm_wiki/models.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write failing OpenAI SDK adapter tests**

Use a fake SDK client, not network:

```python
class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("Response", (), {"output_text": "hello back"})()


class FakeOpenAI:
    def __init__(self):
        self.responses = FakeResponses()
```

Tests:

```python
def test_openai_responses_client_sends_text_input():
    sdk = FakeOpenAI()
    client = OpenAIResponsesClient(model="gpt-5.5", api_key="sk-test", sdk_client=sdk)
    result = client.complete("hello")
    assert result == "hello back"
    assert sdk.responses.calls[0]["model"] == "gpt-5.5"
    assert sdk.responses.calls[0]["input"] == "hello"


def test_openai_responses_client_sends_image_raw_input(tmp_path):
    raw_input = RawInput(...)
    client.complete_with_raw(prompt="describe", raw_input=raw_input)
    content = sdk.responses.calls[0]["input"][0]["content"]
    assert {"type": "input_text", "text": "describe"} in content
    assert content[1]["type"] == "input_image"


def test_openai_responses_client_sends_pdf_raw_input(tmp_path):
    raw_input = RawInput(...)
    client.complete_with_raw(prompt="read", raw_input=raw_input)
    content = sdk.responses.calls[0]["input"][0]["content"]
    assert content[1]["type"] == "input_file"
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_llm.py -q`

Expected: FAIL because `OpenAIResponsesClient` and `complete_with_raw` do not exist.

- [ ] **Step 3: Add LlmClient raw method**

Extend protocol:

```python
def complete_with_raw(self, prompt: str, raw_input: RawInput) -> str:
    ...
```

Legacy `OpenAICompatibleClient.complete_with_raw`:

- If `raw_input.kind == "text"`, append `raw_input.text` to prompt and call `complete`.
- If image/file, raise `RuntimeError("Current provider cannot ingest image/pdf raw files.")`.

- [ ] **Step 4: Implement OpenAIResponsesClient**

Use official SDK:

```python
from openai import OpenAI
```

Constructor:

```python
@dataclass
class OpenAIResponsesClient:
    model: str
    api_key: str
    sdk_client: object | None = None
```

Build SDK client lazily:

```python
client = self.sdk_client or OpenAI(api_key=self.api_key)
```

Response text extraction:

- Prefer `response.output_text` when present.
- Fallback to iterating `response.output[*].content[*].text`.
- Raise clear error if no text.

- [ ] **Step 5: Implement raw content conversion**

For text:

```python
input = [
  {"role": "user", "content": [
    {"type": "input_text", "text": prompt},
    {"type": "input_text", "text": raw_input.text},
  ]}
]
```

For image:

```python
{"type": "input_image", "image_url": f"data:{mime};base64,{base64}"}
```

For PDF/file:

```python
{"type": "input_file", "filename": raw_input.path.name, "file_data": f"data:{mime};base64,{base64}"}
```

- [ ] **Step 6: Update factory**

`build_openai_compatible_client` should be renamed or wrapped as:

```python
def build_llm_client(provider: ProviderConfig) -> LlmClient:
    if provider.protocol == "openai":
        return OpenAIResponsesClient(...)
    return OpenAICompatibleClient(...)
```

Keep old `build_openai_compatible_client` as a compatibility wrapper if tests/imports use it.

- [ ] **Step 7: Run llm tests**

Run: `pytest tests/test_llm.py tests/test_config.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/llm_wiki/llm.py src/llm_wiki/models.py tests/test_llm.py tests/test_config.py
git commit -m "feat: add openai responses llm adapter"
```

---

### Task 4: Wire RawInput Into Ingest

**Files:**
- Modify: `src/llm_wiki/commands/ingest.py`
- Modify: `src/llm_wiki/repl.py`
- Modify: `src/llm_wiki/llm.py`
- Modify: `src/llm_wiki/prompts/plan_ingest.md`
- Modify: `src/llm_wiki/prompts/compile_page_change.md`
- Test: `tests/test_ingest.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing ingest tests for root raw files and non-md**

Add fake LLM:

```python
class FakeRawLlm(FakeV2Llm):
    def plan_ingest_with_raw(self, **kwargs): ...
    def compile_page_change_with_raw(self, **kwargs): ...
```

Or use `complete_with_raw` depending on final adapter shape.

Tests:

```python
def test_ingest_accepts_txt_at_raw_root(tmp_path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "note.txt"
    raw_path.write_text("Transformers use attention.", encoding="utf-8")
    result = ingest_raw_file(...)
    assert result.ok is True


def test_ingest_accepts_pdf_at_raw_root(tmp_path):
    init_workspace(tmp_path)
    raw_path = tmp_path / "raw" / "paper.pdf"
    raw_path.write_bytes(b"%PDF-1.4")
    result = ingest_raw_file(...)
    assert result.ok is True


def test_ingest_rejects_unsupported_raw_type(tmp_path):
    raw_path = tmp_path / "raw" / "archive.zip"
    result = ingest_raw_file(...)
    assert result.ok is False
    assert "unsupported raw file type" in result.message.lower()
```

- [ ] **Step 2: Run failing ingest tests**

Run: `pytest tests/test_ingest.py -q`

Expected: FAIL because ingest still only accepts `.md` and reads `raw_text`.

- [ ] **Step 3: Refactor LLM plan/compile methods**

Keep public names but pass `RawInput`:

```python
llm.plan_ingest(raw_input=raw_input, candidates=entries)
llm.compile_page_change(raw_input=raw_input, ...)
```

OpenAIResponsesClient implementation should call `complete_with_raw` and parse JSON for plan.

Legacy compatible implementation should allow `raw_input.kind == "text"` only.

- [ ] **Step 4: Update ingest validation**

Replace suffix check:

```python
if not relative.parts or relative.parts[0] != "raw" or raw_path.suffix.lower() != ".md":
```

with:

```python
raw_input = build_raw_input(root, raw_path)
if not raw_input.ok:
    return IngestResult(ok=False, message=raw_input.message)
```

- [ ] **Step 5: Remove raw path topic dependency**

Delete unused `_determine_topic` or leave only if tests still need it. New page path must use `change.topic` from LLM plan only.

Raw nested paths may be included in prompt as weak context but must not determine wiki topic.

- [ ] **Step 6: Update prompts**

`plan_ingest.md`:

- Raw path is source identity and weak context only.
- Decide wiki topic from content.
- Do not infer topic solely from raw directory name.

`compile_page_change.md`:

- Source may be markdown, text, HTML, JSON, CSV, PDF, or image.
- Use only supported evidence from the raw input.

- [ ] **Step 7: Update REPL client factory**

Replace:

```python
from llm_wiki.llm import build_openai_compatible_client
```

with:

```python
from llm_wiki.llm import build_llm_client
```

Use `build_llm_client` for query and ingest.

- [ ] **Step 8: Run focused tests**

Run: `pytest tests/test_ingest.py tests/test_app.py tests/test_llm.py -q`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/llm_wiki/commands/ingest.py src/llm_wiki/repl.py src/llm_wiki/llm.py src/llm_wiki/prompts/plan_ingest.md src/llm_wiki/prompts/compile_page_change.md tests/test_ingest.py tests/test_app.py tests/test_llm.py
git commit -m "feat: support format-agnostic raw ingest"
```

---

### Task 5: Documentation And Release Prep

**Files:**
- Modify: `README.md`
- Modify: `demo/README.md`
- Modify: `docs/superpowers/plans/2026-04-26-v3-openai-sdk-raw-ingest.md`
- Test: `tests/test_app.py`

- [ ] **Step 1: Update README**

Document v3:

```text
V3 = Raw Is The Interface
```

Update supported raw formats:

```text
.md .txt .html .json .csv .pdf .png .jpg .jpeg
```

Update config example:

```json
{
  "provider": {
    "protocol": "openai",
    "model": "gpt-5.5",
    "api_key": "sk-..."
  }
}
```

Document fallback:

```text
openai_compatible remains available for text-only compatible endpoints.
```

- [ ] **Step 2: Update demo docs**

Show root raw file examples:

```text
ingest raw/paper.pdf
ingest raw/screenshot.png
ingest raw/notes.txt
```

- [ ] **Step 3: Update CLI help if needed**

Keep help simple:

```text
ingest raw/<file>
```

- [ ] **Step 4: Run full verification**

Run: `pytest -q`

Expected: PASS.

Run: `python -m llm_wiki.app --help`

Expected: help prints and ingest command remains simple.

- [ ] **Step 5: Commit**

```bash
git add README.md demo/README.md docs/superpowers/plans/2026-04-26-v3-openai-sdk-raw-ingest.md tests/test_app.py
git commit -m "docs: document v3 raw ingest workflow"
```

---

## Final Verification

- [ ] Run: `pytest -q`
  - Expected: all tests pass.
- [ ] Run: `python -m llm_wiki.app --help`
  - Expected: help prints successfully.
- [ ] Run: `git status --short --branch`
  - Expected: clean feature branch.

## Merge/Release After Implementation

After implementation is complete and verified:

1. Merge `feature/v3-multimodal-raw-ingest` back to `main`.
2. Run full verification on `main`.
3. Tag `v3.0.0`.
4. Push `main` and `v3.0.0`.
5. Delete the temporary feature branch/worktree.

## Known Risks

- The official OpenAI SDK dependency must be installed for tests/imports. If dependency installation fails because the environment lacks network access, request approval and run `pip install -e .` or equivalent only after explaining why.
- Provider compatibility is intentionally narrow: non-OpenAI providers may remain text-only.
- Base64 file inputs can be large. v3 first stage does not optimize uploads or caching.
- OpenAI file/image support depends on selected model capabilities. Runtime errors should be clear and actionable.
