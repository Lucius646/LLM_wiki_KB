# Demo Workspace

This directory contains a fixed demo workspace for the LLM wiki workflow.

## Layout

```text
demo/
|- README.md
`- workspace/
   `- raw/
      |- transformers/
      |  |- attention-notes.md
      |  `- self-attention-history.md
      `- state-space-models/
         `- mamba-notes.md
```

The demo workspace starts with raw source material only. That is intentional. `wiki/` and the workspace git history should be created by `init`, and concept pages should appear only after `ingest`.

## Preparation

1. Install the tool from the repo root with `python -m pip install -e .`
2. Create `~/.llm-wiki/config.json`
3. Change into `demo/workspace`
4. Start the REPL with `llm-wiki`

## Suggested Demo Script

```text
init
ingest
query what does attention do in transformers
lint
undo
exit
```

V3 root raw examples:

```text
ingest
ingest --show-skipped
ingest raw/paper.pdf
ingest raw/screenshot.png
ingest raw/notes.txt
```

## Notes

- `raw/` is the user interface; topic folders are optional source identity, not required classification
- supported first-stage raw formats are `.md`, `.txt`, `.html`, `.json`, `.csv`, `.pdf`, `.png`, `.jpg`, and `.jpeg`
- `init` initializes git and commits the baseline workspace
- bare `ingest` scans `raw/`, skips unchanged files through `wiki/ingest-ledger.json`, and auto-applies conservative 1-3 page plans
- `ingest raw/<file>` remains available for single-file manual ingest
- `undo` reverts the latest managed ingest commit using git
