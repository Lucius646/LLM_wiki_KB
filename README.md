# LLM Wiki KB

`LLM_wiki_KB` is a second-development knowledge-base project built from the lightweight `karpathy-llm-wiki` seed. The upstream seed provided the basic Superpowers-style skills, templates, and knock-brick direction; this repository turns that base into a runnable LLM-maintained local Markdown wiki.

The product philosophy is Karpathy-style knowledge compilation, not RAG: humans provide raw materials and direction, while the LLM handles routine organization with minimal human intervention. V3 makes `raw/` the user interface: drop source files there, then let the LLM decide the wiki topic/path and compile durable concept pages. V3.1 makes bare `ingest` scan `raw/` automatically and skip unchanged sources.

## What This Repo Is

This repo packages the workflow as a thin Python REPL around five operations:

- `init`: initialize a git-backed wiki workspace
- `ingest`: compile pending raw sources into a conservative set of wiki pages
- `query`: answer from the wiki only
- `lint`: check structural consistency
- `undo`: revert the latest managed ingest commit

The core idea is `knowledge compilation`, not plain retrieval. `raw/` holds source material. `wiki/` holds concept-oriented pages that accumulate knowledge over time.

## Workspace Model

The tool repo and the knowledge workspace are separate.

- This repository contains the implementation, prompts, tests, and demo assets.
- A workspace is any directory that contains `raw/` and `wiki/`.
- The current working directory is the active workspace.

Minimal workspace layout:

```text
my-wiki/
|- raw/
|  `- <dropped source files>
`- wiki/
   |- <llm-decided topic>/
   |- index.md
   |- ingest-ledger.json
   `- log.md
```

Run `init` inside a workspace to create the missing directories, baseline files, and a git repository if needed.

## V3.1 Boundaries

`v3.1` is still intentionally narrow. The important change is that raw source handling moves closer to the product philosophy: the user drops material into `raw/`; bare `ingest` detects which supported files are new or changed.

Included:

- git-backed local workspace initialization
- local raw files under `raw/`, including `.md`, `.txt`, `.html`, `.json`, `.csv`, `.pdf`, `.png`, `.jpg`, and `.jpeg`
- automatic raw scanning with content-hash skip detection
- system-maintained `wiki/ingest-ledger.json`
- conservative multi-page concept compilation per ingest
- automatic creation of durable concept pages
- structured Markdown audit entries in `wiki/log.md`
- automatic checkpoint and ingest commits with `LLM-Wiki-Action` trailers
- `undo` for reverting the latest managed ingest commit
- read-only query output to the console
- structural lint for index coverage, wiki links, raw links, article metadata, log references, orphan pages, and duplicate candidates
- tool-level config at `~/.llm-wiki/config.json`
- official OpenAI SDK provider via `provider.protocol = "openai"`
- text-only OpenAI-compatible fallback via `provider.protocol = "openai_compatible"`

Not included:

- URL ingestion
- directory/batch ingest
- semantic lint
- query archiving
- product-grade chat UI
- hidden run database

Git is a required system dependency for workspaces. The tool calls the git CLI directly; it does not depend on GitPython. The OpenAI SDK is the primary provider path for v3 multimodal raw ingest.

## Install And Configure

Create an editable local install:

```bash
python -m pip install -e .
```

Then create `~/.llm-wiki/config.json`:

```json
{
  "provider": {
    "protocol": "openai",
    "model": "gpt-5.5",
    "api_key": "sk-..."
  }
}
```

For OpenAI-compatible text-only endpoints, use:

```json
{
  "provider": {
    "protocol": "openai_compatible",
    "model": "gpt-5.4",
    "api_key": "sk-...",
    "base_url": "https://example.com/v1"
  }
}
```

## Demo Flow

The fixed demo workspace lives under [demo/workspace](demo/workspace/).

```text
1. cd demo/workspace
2. llm-wiki
3. init
4. ingest
5. query what does attention do in transformers
6. lint
7. undo
```

V3 also accepts root raw files such as:

```text
ingest
ingest --show-skipped
ingest raw/paper.pdf
ingest raw/screenshot.png
ingest raw/notes.txt
```

What to show during the demo:

- `init` creates `raw/`, `wiki/`, `wiki/index.md`, `wiki/log.md`, `wiki/ingest-ledger.json`, and a baseline git commit
- `ingest` plans internally, updates or creates 1-3 concept pages, updates `wiki/index.md`, writes `wiki/log.md`, and commits the result
- `wiki/ingest-ledger.json` records processed raw hashes so unchanged files are skipped
- `query` answers from compiled wiki pages rather than raw files
- `lint` reports structural issues in the current wiki
- `undo` reverts the latest commit with `LLM-Wiki-Action: ingest`

## Command Summary

```text
LLM Wiki REPL

Commands:
- init
- status
- ingest
- ingest --show-skipped
- ingest raw/<file>
- query <question>
- lint
- undo
- help
- exit
```

Managed git commits include machine-readable trailers:

```text
LLM-Wiki-Action: init|checkpoint|ingest|undo
LLM-Wiki-Source: raw/<file>
```

You can also print help directly:

```bash
python -m llm_wiki.app --help
```

## Demo Assets

See [demo/README.md](demo/README.md) for the prepared sample materials and the walkthrough notes for the fixed demo.

## Repository

Canonical remote:

```text
git@github.com:Lucius646/LLM_wiki_KB.git
```

## Why This Exists

This repository is a personal KB tool experiment: small enough to explain, real enough to run, and structured so later versions can grow toward stronger knowledge compilation without throwing away the CLI core.
