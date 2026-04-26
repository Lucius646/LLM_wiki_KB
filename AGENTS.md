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
- Before implementing a requirement, run an existing-solution check. Look broadly: official SDKs, mature libraries, current docs, open-source projects, adjacent local projects, and web search when the answer is not already known. Prefer adopting, adapting, or simplifying proven implementations over rebuilding them.
- Do not limit the search to projects the user named. Use independent technical judgment to identify relevant mainstream tools and references.
- If cloning an external repository would materially improve understanding, ask for approval first. State the repository URL, target directory, purpose, expected borrowed ideas, and whether the use is read-only reference or code reuse.
- For OpenAI API work, use the official OpenAI SDK and current official API shape unless there is a specific reason not to.
