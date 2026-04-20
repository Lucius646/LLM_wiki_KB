# LLM Wiki Knock-Brick MVP

`karpathy-llm-wiki` is a small research prototype for a Karpathy-style LLM wiki workflow. It is not a full knowledge product and it is not a general RAG stack. The goal of `v1` is narrower: make `init -> ingest -> query -> lint` concrete enough to run, explain, and demo.

## What This Repo Is

This repo packages the workflow as a thin Python REPL around four operations:

- `init`: initialize a wiki workspace
- `ingest`: compile one raw markdown source into one concept article
- `query`: answer from the wiki only
- `lint`: check structural consistency

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

Run `init` inside a workspace to create the missing directories and baseline files.

## V1 Boundaries

`v1` is intentionally narrow.

Included:

- local workspace initialization
- local `.md` raw files only
- single-target concept compilation per ingest
- read-only query output to the console
- structural lint for index coverage, wiki links, and raw links
- tool-level config at `~/.llm-wiki/config.json`
- OpenAI-compatible provider settings with `model`, `api_key`, and optional `base_url`

Not included:

- URL ingestion
- PDF ingestion
- image understanding
- multi-article compile and cascade update
- semantic lint
- query archiving
- product-grade chat UI

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
4. ingest raw/transformers/attention-notes.md
5. query what does attention do in transformers
6. lint
```

What to show during the demo:

- `init` creates `raw/`, `wiki/`, `wiki/index.md`, and `wiki/log.md`
- `ingest` picks an existing concept page when possible and updates `wiki/index.md` and `wiki/log.md`
- `query` answers from compiled wiki pages rather than raw files
- `lint` reports structural issues in the current wiki

## Command Summary

```text
LLM Wiki REPL

Commands:
- init
- status
- ingest raw/<topic>/<file>.md [--article <slug>]
- query <question>
- lint
- help
- exit
```

You can also print help directly:

```bash
python -m llm_wiki.app --help
```

## Demo Assets

See [demo/README.md](demo/README.md) for the prepared sample materials and the walkthrough notes for the fixed demo.

## Why This Exists

This repository is meant to be a credible "knock-brick" project: small enough to explain, real enough to run, and structured so `v2` can grow toward stronger knowledge compilation without throwing away the `v1` core.
