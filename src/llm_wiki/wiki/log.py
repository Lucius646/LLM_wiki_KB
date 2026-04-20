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
