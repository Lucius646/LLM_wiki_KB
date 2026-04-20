# Knock-Brick MVP Design

**Project:** `karpathy-llm-wiki`
**Date:** `2026-04-20`
**Status:** Approved draft for implementation planning

## 1. Goal

Build a small, honest, demo-ready prototype of a Karpathy-style LLM wiki workflow.

This is not a full product. It is a research-prototype workflow demo that:

- can be explained clearly,
- can run end-to-end,
- preserves the correct abstraction level,
- and can be extended in later versions without changing direction.

The core loop is:

- `init`
- `ingest`
- `query`
- `lint`

The project should serve two purposes at once:

- a real small tool for ongoing personal experimentation,
- a strong demo for lab applications and technical discussion.

## 2. Design Philosophy

This project follows the Karpathy LLM wiki idea as a knowledge-compilation workflow rather than a standard RAG system.

The intended knowledge model is:

- `raw/` stores source materials,
- `wiki/` stores concept-oriented compiled knowledge pages,
- `wiki/index.md` is the global concept index,
- `wiki/log.md` is the append-only operation log.

The important distinction is:

- `raw` is not the wiki,
- `wiki` is not a copy of source files,
- `ingest` is compilation into concept pages, not archive mirroring.

Even though `v1` will be limited, the abstraction must stay correct. The first version must not turn the system into a source-file archiver.

## 3. Product Positioning

The primary positioning is:

- research prototype,
- workflow demo,
- small concept-wiki compiler.

It is explicitly not:

- a heavy knowledge management product,
- a desktop app,
- a general-purpose RAG platform,
- a chat agent product.

The CLI is not the system core. It is a thin interaction shell around the workflow.

## 4. Tool Repo vs Workspace

The tool implementation and knowledge workspace are separate.

### Tool Repository

The repository contains:

- Python source code,
- prompts,
- README,
- demo narrative and sample workspace,
- design and plan documents.

### Knowledge Workspace

A workspace is any directory the tool operates on. It contains:

- `raw/`
- `wiki/`
- `wiki/index.md`
- `wiki/log.md`

The current working directory is treated as the active workspace in `v1`.

This avoids coupling one specific knowledge base to the tool source tree.

## 5. MVP Commands

The `v1` command set is:

- `init`
- `ingest <raw-file>`
- `query <question>`
- `lint`

These commands are exposed through a REPL-style CLI.

### 5.1 `init`

Purpose:

- initialize the current directory as a knowledge workspace.

Behavior:

- create `raw/` if missing,
- create `wiki/` if missing,
- create `wiki/index.md` if missing,
- create `wiki/log.md` if missing,
- do not overwrite existing content.

### 5.2 `ingest <raw-file>`

Purpose:

- compile one source file from `raw/` into one concept-oriented wiki page.

Behavior:

- input must be a workspace-local `raw/.../*.md` file,
- only Markdown is supported in `v1`,
- raw content is treated as plain text,
- URLs are preserved,
- image URLs may remain in source text but image content is not interpreted,
- one ingest updates exactly one wiki concept page in `v1`,
- after ingest, `wiki/index.md` and `wiki/log.md` are updated.

### 5.3 `query <question>`

Purpose:

- answer using existing wiki content.

Behavior:

- reads from `wiki/index.md` and relevant wiki pages,
- prefers wiki content over model prior knowledge,
- prints answer in the console,
- includes citations to wiki page paths,
- does not write files in `v1`.

### 5.4 `lint`

Purpose:

- check structural consistency of the wiki.

Behavior in `v1`:

- check whether `wiki/index.md` covers actual wiki pages,
- check internal wiki links,
- check raw references inside wiki pages,
- report structural issues clearly,
- do not attempt semantic analysis.

## 6. Ingest Compilation Model

This is the most important `v1` design choice.

The system must preserve concept-level compilation even though `v1` only updates one target page per ingest.

### 6.1 Source and Target Semantics

- `raw` files are evidence and source material,
- `wiki` pages are concept entries,
- one source may eventually affect multiple concept pages,
- one concept page may eventually be supported by multiple sources.

`v1` intentionally limits execution to:

- one raw file,
- one target concept page,
- one ingest operation at a time.

That is a scope reduction, not a change in abstraction.

### 6.2 Article Selection Rule

Default behavior:

- read existing entries from `wiki/index.md`,
- prefer matching an existing concept page,
- only propose a new concept page if existing entries do not fit.

This is the `existing-first` rule.

### 6.3 Human Override

The user must be able to override article selection.

So `ingest` supports two paths:

- default LLM-inferred target concept,
- explicit manual target via an override such as `--article <name>`.

If the manually specified article does not exist, the tool may create it.

### 6.4 New Article Confirmation

If the LLM proposes creating a new concept page:

- the REPL must show the proposed article name,
- the user must confirm before the file is created.

This reduces concept fragmentation in `v1`.

### 6.5 Why This Boundary Exists

The system should not create source-title pages by default. That would weaken the project into a source archive and work against the intended knowledge model.

The chosen compromise is:

- preserve concept compilation,
- keep humans in the loop,
- delay multi-page compilation until `v2`.

## 7. Query Boundary

`query` in `v1` is read-only.

It:

- reads the wiki,
- answers in the console,
- cites relevant wiki pages.

It does not:

- archive the answer,
- create new wiki pages,
- write to `outputs/`.

This keeps the roles clean:

- `ingest` writes knowledge,
- `query` reads knowledge,
- `lint` checks knowledge structure.

## 8. Lint Boundary

`lint` in `v1` only performs structural checks.

Included:

- index coverage against actual files,
- broken internal wiki links,
- broken raw references.

Excluded:

- contradiction detection,
- missing concept detection,
- orphan pages,
- semantic cross-link suggestions,
- outdated claim detection.

The goal is stable, explainable, deterministic validation.

## 9. REPL Form

The external interface is a REPL-style interactive CLI.

Example:

```text
llm-wiki
> init
> ingest raw/transformers/attention-notes.md
> query transformer attention solves what problem
> lint
```

The REPL is not a chat agent.

It is a command shell with a clean interaction model.

### 9.1 Included REPL Features

- startup header,
- single-line command input,
- structured output formatting,
- minimal confirmation prompts,
- built-in helper commands:
  - `help`
  - `status`
  - `exit`

### 9.2 Excluded REPL Features

- chat bubbles,
- natural-language intent parsing,
- multi-pane terminal UI,
- agent-style conversation state,
- complex slash-command framework.

The interface should feel intentional and usable, but not product-heavy.

## 10. Workspace Rules

`v1` uses the current working directory as the active workspace.

That means:

- `llm-wiki` operates on the current directory,
- `init` initializes the current directory,
- no workspace switching exists inside the REPL in `v1`.

Later versions may add:

- `--workspace <path>` on startup,
- or REPL workspace switching.

But those are out of scope for the MVP.

## 11. Raw File Rules

The workspace may contain non-Markdown files, but `v1` ingest only accepts Markdown.

Rules:

- supported ingest target: `*.md`,
- unsupported file types are rejected,
- non-`.md` files do not participate in compilation,
- raw Markdown is treated as text input.

This keeps input handling simple without over-constraining what users may store in `raw/`.

## 12. Configuration

`v1` uses a tool-level config file, not per-workspace provider config.

Suggested path:

- `~/.llm-wiki/config.json`

Suggested minimum shape:

```json
{
  "provider": {
    "protocol": "openai_compatible",
    "model": "gpt-5.4",
    "api_key": "sk-...",
    "base_url": ""
  }
}
```

Rules:

- `protocol` is fixed to `openai_compatible` in `v1`,
- `model` is required,
- `api_key` is required,
- `base_url` is optional,
- if `base_url` is empty, the SDK default endpoint is used,
- if `base_url` is provided, it is passed through after only light normalization.

No config command is required in `v1`. Manual editing is acceptable.

## 13. LLM Provider Boundary

The `v1` LLM layer is intentionally narrow.

It only needs to support:

- infer target concept page,
- compile/update one concept page,
- answer a query from selected wiki pages.

It does not need:

- tool calling,
- multimodal inputs,
- provider-specific capability negotiation,
- large provider registries,
- complex endpoint fallback logic.

This keeps provider complexity proportional to the MVP goal.

## 14. Failure Handling

The rule is:

`v1` should fail clearly instead of pretending to succeed.

### 14.1 Initialization Errors

- if already initialized, `init` reports that the workspace already exists,
- it does not overwrite existing files.

### 14.2 Ingest Errors

- uninitialized workspace: reject and ask for `init`,
- missing config: reject and point to config path,
- missing raw file: reject,
- unsupported extension: reject,
- target inference failure: ask for manual `--article`,
- proposed new article: require confirmation,
- invalid or empty compile result: abort without writing broken files.

### 14.3 Query Errors

- uninitialized workspace: reject,
- no wiki pages yet: ask the user to ingest content first,
- no relevant wiki content found: report insufficient evidence instead of fabricating an answer.

### 14.4 Lint Errors

- uninitialized workspace: reject,
- missing index or log: report clearly,
- structural issues: report exactly what is wrong.

## 15. Technical Direction

The recommended `v1` stack is:

- Python 3.11+
- `prompt_toolkit` for REPL behavior
- `rich` for console formatting
- Python standard library for filesystem and parsing work

The repository should be organized around replaceable responsibilities:

```text
src/llm_wiki/
├─ app.py
├─ repl.py
├─ workspace.py
├─ llm.py
├─ models.py
├─ commands/
│  ├─ init.py
│  ├─ ingest.py
│  ├─ query.py
│  └─ lint.py
├─ wiki/
│  ├─ index.py
│  ├─ log.py
│  ├─ article.py
│  └─ search.py
└─ prompts/
   ├─ infer_article.md
   ├─ compile_article.md
   └─ answer_query.md
```

This structure keeps `v1` simple while leaving clear replacement points for `v2`.

## 16. Demo Narrative

The README and demo should present the system as a workflow demo first, not a generic CLI utility.

Recommended narrative order:

1. This is not standard RAG.
2. The system compiles raw materials into concept-oriented wiki pages.
3. The MVP demonstrates `init -> ingest -> query -> lint`.
4. `v1` is intentionally narrow but structurally correct.
5. `v2` will expand ingest from single-target compilation to multi-page compilation.

The demo should use a fixed small dataset:

- 2 to 3 raw Markdown source files,
- one or two existing concept pages,
- at least one case where ingest updates an existing concept,
- optionally one case where ingest proposes a new concept page.

## 17. Explicit Non-Goals for V1

Do not include these in the first version:

- URL ingestion,
- PDF ingestion,
- text or HTML input normalization beyond Markdown,
- image understanding,
- one-to-many concept compilation,
- cascade updates,
- automatic cross-topic linking,
- query archiving,
- semantic lint,
- multi-workspace switching inside REPL,
- chat-agent UI.

## 18. V2 Direction

The expected next version expands the ingest compiler rather than changing the overall architecture.

Main upgrades:

- one raw file may update multiple concept pages,
- stronger merge behavior for existing concepts,
- cascade updates,
- cross-link generation,
- better de-duplication and concept naming,
- richer lint heuristics,
- optional query archiving.

That means `v1` is not a dead-end demo. It is the first constrained implementation of the right system model.
