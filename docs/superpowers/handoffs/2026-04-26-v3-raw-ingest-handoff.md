# V3 Raw Ingest Handoff

Date: 2026-04-26
Branch: `feature/v3-multimodal-raw-ingest`
Worktree: `E:\LuciusProject\karpathy-llm-wiki\.worktrees\feature-v3-multimodal-raw-ingest`
Remote: `git@github.com:Lucius646/LLM_wiki_KB.git`

## Current State

V3 implementation is complete on the feature branch, but not merged to `main` and not tagged.

Implemented commits:

- `234d6e6 docs: add v3 raw ingest implementation plan`
- `c35e4fb feat: add openai provider protocol`
- `4f80448 feat: add raw input abstraction`
- `8677401 feat: add openai responses llm adapter`
- `0d6f5ca feat: support format-agnostic raw ingest`
- `933291d docs: document v3 raw ingest workflow`

## V3 Scope

V3 intentionally does only two product changes:

- Use the official OpenAI SDK / Responses API as the primary provider path.
- Let `raw/` accept more first-stage formats: `.md`, `.txt`, `.html`, `.json`, `.csv`, `.pdf`, `.png`, `.jpg`, `.jpeg`.

Do not add capture, inbox, batch ingest, directory ingest, topic parameters, RAG, GUI, MCP, or a visible normalization pipeline unless the user explicitly reopens scope.

## Product Philosophy

`raw/` is the user interface. The user drops materials into `raw/`; the LLM handles routine interpretation and decides wiki topic/path through the ingest plan. Raw nested folders are allowed, but they are source identity or weak context only, not required user classification.

## Verification Already Run

Latest post-commit verification:

```text
pytest -q
65 passed in 24.22s
```

```text
python -m llm_wiki.app --help
LLM Wiki REPL

Commands:
- init
- status
- ingest raw/<file>
- query <question>
- lint
- undo
- help
- exit
```

Feature branch was clean before this handoff file was added.

## Next Session

Recommended next steps:

1. Read `AGENTS.md` and relevant docs under `docs/superpowers/`.
2. Check `git status --short --branch` in the feature worktree.
3. Commit this handoff if it is not already committed.
4. Merge `feature/v3-multimodal-raw-ingest` back to `main`.
5. Run `pytest -q` and `python -m llm_wiki.app --help` on `main`.
6. Tag `v3.0.0` after verification.
7. Push `main` and `v3.0.0`.
8. Delete the temporary feature branch/worktree only after push is confirmed.

## Known Notes

- `openai_compatible` remains text-only fallback. Image/PDF raw ingest requires `provider.protocol = "openai"`.
- Runtime OpenAI model capability still matters for file/image inputs.
- Pytest may emit cache permission warnings in this environment when it cannot write `.pytest_cache`; previous verification still exited 0.
