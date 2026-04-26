# Project Agent Instructions

This repository is `LLM_wiki_KB`. These rules apply to project work on every branch and version.

Before doing planning, specification, implementation, verification, merge, or handoff work, check for relevant local workflow docs under:

```text
docs/superpowers/
```

Historical version-specific workflow docs may exist there. Treat them as scoped to that version unless this file says otherwise.

Default rules:

- Discuss and approve a mini spec before writing an implementation plan.
- Keep feature work isolated in a temporary feature branch or worktree unless explicitly instructed otherwise.
- Merge completed feature work back to `main`; use tags/releases such as `v2.0.0` or `v3.0.0` to mark product versions.
- Do not use long-lived version branches as the primary versioning model.
- Do not use subagents unless the user explicitly asks for them.
- Use focused tests before implementation for core behavior.
- Run verification before claiming completion.
- Before implementing a requirement, run an existing-solution check. Look broadly: official SDKs, mature libraries, current docs, open-source projects, adjacent local projects, and web search when the answer is not already known. Prefer adopting, adapting, or simplifying proven implementations over rebuilding them.
- Do not limit the search to projects the user named. Use independent technical judgment to identify relevant mainstream tools and references.
- If cloning an external repository would materially improve understanding, ask for approval first. State the repository URL, target directory, purpose, expected borrowed ideas, and whether the use is read-only reference or code reuse.
- For OpenAI API work, use the official OpenAI SDK and current official API shape unless there is a specific reason not to.
