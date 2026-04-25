# LLM Wiki V2

`karpathy-llm-wiki` is a small research prototype for a Karpathy-style LLM wiki workflow. It is not a full knowledge product and it is not a general RAG stack. V2 makes the workflow git-backed, low-intervention, auditable, and capable of conservative multi-page knowledge compilation.

## What This Repo Is

This repo packages the workflow as a thin Python REPL around five operations:

- `init`: initialize a git-backed wiki workspace
- `ingest`: compile one raw markdown source into a conservative set of wiki pages
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
├─ raw/
│  └─ <topic>/
└─ wiki/
   ├─ <topic>/
   ├─ index.md
   └─ log.md
```

Run `init` inside a workspace to create the missing directories, baseline files, and a git repository if needed.

## V2 Boundaries

`v2` is still intentionally narrow.

Included:

- git-backed local workspace initialization
- local `.md` raw files only
- conservative multi-page concept compilation per ingest
- automatic creation of durable concept pages
- structured Markdown audit entries in `wiki/log.md`
- automatic checkpoint and ingest commits with `LLM-Wiki-Action` trailers
- `undo` for reverting the latest managed ingest commit
- read-only query output to the console
- structural lint for index coverage, wiki links, raw links, article metadata, log references, orphan pages, and duplicate candidates
- tool-level config at `~/.llm-wiki/config.json`
- OpenAI-compatible provider settings with `model`, `api_key`, and optional `base_url`

Not included:

- URL ingestion
- PDF ingestion
- image understanding
- semantic lint
- query archiving
- product-grade chat UI
- hidden run database

Git is a required system dependency for V2 workspaces. The tool calls the git CLI directly; it does not depend on GitPython.

## Install And Configure

Create an editable local install:

```bash
python -m pip install -e .
```

Then create `~/.llm-wiki/config.json`:

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

Leave `base_url` empty to use the provider default endpoint. Set it only when you need an OpenAI-compatible override.

## Demo Flow

The fixed demo workspace lives under [demo/workspace](demo/workspace/).

```text
1. cd demo/workspace
2. llm-wiki
3. init
4. ingest raw/transformers/self-attention-history.md
5. query what does attention do in transformers
6. lint
7. undo
```

What to show during the demo:

- `init` creates `raw/`, `wiki/`, `wiki/index.md`, `wiki/log.md`, and a baseline git commit
- `ingest` plans internally, updates or creates 1-3 concept pages, updates `wiki/index.md`, writes `wiki/log.md`, and commits the result
- `query` answers from compiled wiki pages rather than raw files
- `lint` reports structural issues in the current wiki
- `undo` reverts the latest commit with `LLM-Wiki-Action: ingest`

## Command Summary

```text
LLM Wiki REPL

Commands:
- init
- status
- ingest raw/<topic>/<file>.md
- query <question>
- lint
- undo
- help
- exit
```

Managed git commits include machine-readable trailers:

```text
LLM-Wiki-Action: init|checkpoint|ingest|undo
LLM-Wiki-Source: raw/<topic>/<file>.md
```

You can also print help directly:

```bash
python -m llm_wiki.app --help
```

## Demo Assets

See [demo/README.md](demo/README.md) for the prepared sample materials and the walkthrough notes for the fixed demo.

## Why This Exists

This repository is meant to be a credible "knock-brick" project: small enough to explain, real enough to run, and structured so later versions can grow toward stronger knowledge compilation without throwing away the CLI core.
