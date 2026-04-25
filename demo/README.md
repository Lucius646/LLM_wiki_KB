# Demo Workspace

This directory contains a fixed demo workspace for the `v2` LLM wiki workflow.

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

The demo workspace starts with raw markdown only. That is intentional. `wiki/` and the workspace git history should be created by `init`, and concept pages should appear only after `ingest`.

## Preparation

1. Install the tool from the repo root with `python -m pip install -e .`
2. Create `~/.llm-wiki/config.json`
3. Change into `demo/workspace`
4. Start the REPL with `llm-wiki`

## Suggested Demo Script

```text
init
ingest raw/transformers/self-attention-history.md
query what does attention do in transformers
lint
undo
exit
```

## Notes

- `v2` only supports local `.md` files under `raw/`
- raw files may contain URLs, but the workflow treats them as markdown text sources
- `init` initializes git and commits the baseline workspace
- `ingest` does not ask for confirmation by default; it auto-applies a conservative 1-3 page plan
- `undo` reverts the latest managed ingest commit using git
