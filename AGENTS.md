# Agent Instructions

This worktree is for v2 development.

Before doing any v2 planning, specification, implementation, verification, merge, or handoff work, read:

```text
docs/superpowers/lightweight-v2-workflow.md
```

Treat that file as the local workflow contract for this branch. It intentionally reduces the default Superpowers process, but the reduced process is still mandatory.

Default rules:

- Discuss and approve a mini spec before writing an implementation plan.
- Keep work in this `v2-multi-page-ingest` worktree unless explicitly instructed otherwise.
- Do not use subagents unless the user explicitly asks for them.
- Use focused tests before implementation for core behavior.
- Run verification before claiming completion.
