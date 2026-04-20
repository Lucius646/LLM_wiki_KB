# Demo Workspace

This directory contains a fixed demo workspace for the `v1` LLM wiki MVP.

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

The demo workspace starts with raw markdown only. That is intentional. `wiki/` should be created by `init`, and concept pages should appear only after `ingest`.

## Preparation

1. Install the tool from the repo root with `python -m pip install -e .`
2. Create `~/.llm-wiki/config.json`
3. Change into `demo/workspace`
4. Start the REPL with `llm-wiki`

## Suggested Demo Script

```text
init
ingest raw/transformers/attention-notes.md
query what does attention do in transformers
lint
exit
```

## Notes

- `v1` only supports local `.md` files under `raw/`
- raw files may contain URLs, but the workflow treats them as markdown text sources
- if the model proposes a brand-new article, the REPL asks for confirmation before writing it
