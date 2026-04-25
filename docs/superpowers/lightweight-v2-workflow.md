# Lightweight V2 Workflow

This project uses a reduced Superpowers workflow for v2. The goal is to keep the useful gates while avoiding process overhead that is larger than the feature.

## Why This Is Lightweight

`karpathy-llm-wiki` is a small CLI knowledge compiler, not a large multi-surface product. For v2, the main uncertainty is product semantics rather than engineering parallelism:

- What should an internal ingest plan contain?
- Where should the system stop instead of asking for routine confirmation?
- How should one raw source update multiple wiki pages?
- How should the system avoid hallucinated or over-eager rewrites?
- What audit trail is enough?

Because of that, v2 should optimize for short feedback loops and explicit boundaries.

## Keep These Gates

- Discuss a mini spec before writing an implementation plan.
- Keep feature work isolated in the `v2-multi-page-ingest` worktree.
- Use tests before implementation for core behavior.
- When tests fail, identify the root cause before changing code.
- Before claiming completion, run verification commands and report exact results.

## Skip By Default

- No subagents unless the user explicitly asks for them.
- No long plan document unless the spec grows beyond a small checklist.
- No multi-agent execution flow.
- No spec review agent or plan review agent.
- No branch finishing ritual unless the user asks to merge, commit, push, or open a PR.

## V2 Flow

1. Draft the mini spec in chat first.
2. User reviews and edits the spec.
3. After approval, write a compact checklist or short plan.
4. Implement in the v2 worktree with focused tests.
5. Run `pytest -q` and any relevant CLI smoke tests.
6. Summarize what changed, what passed, and any remaining risks.

## Mini Spec Shape

The v2 mini spec should stay short and cover only:

- Goal
- Non-goals
- CLI/user experience
- Data model and files touched
- Acceptance checks

## Default V2 Scope

V2 is currently framed as a git-backed, low-intervention, auditable multi-page knowledge compiler:

```text
raw source -> internal ingest plan -> auto-apply -> audit/log -> git commit
```

The implementation should favor existing-page updates, conservative 1-3 page changes, explicit auditability, and git-backed undo over broad automation or hidden databases.
