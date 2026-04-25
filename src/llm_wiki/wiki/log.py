from pathlib import Path


def append_log_entry(
    log_path: Path,
    date: str,
    action: str,
    title: str,
    extra_lines: list[str] | None = None,
) -> None:
    lines = [f"## [{date}] {action} | {title}", *[f"- {line}" for line in extra_lines or []], ""]
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def append_ingest_audit_entry(
    log_path: Path,
    *,
    date: str,
    source: str,
    summary: str,
    planned: list[str],
    updated: list[str],
    created: list[str],
    warnings: list[str],
    commit: str,
) -> None:
    lines = [
        f"## [{date}] ingest | {source}",
        "",
        f"- Summary: {summary}",
        "- Planned:",
        *[f"  - {item}" for item in planned],
        "- Updated:",
        *[f"  - {item}" for item in updated],
        "- Created:",
        *[f"  - {item}" for item in created],
        "- Warnings:",
        *[f"  - {item}" for item in (warnings or ["none"])],
        f"- Commit: {commit or 'pending'}",
        "",
    ]
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
