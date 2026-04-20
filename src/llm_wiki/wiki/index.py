import re
from collections import OrderedDict
from pathlib import Path

from llm_wiki.models import IndexEntry


ROW_PATTERN = re.compile(r"^\| \[(?P<title>.+?)\]\((?P<path>.+?)\) \| (?P<summary>.+?) \| (?P<updated>.+?) \|$")


def read_index_entries(index_path: Path) -> list[IndexEntry]:
    lines = index_path.read_text(encoding="utf-8").splitlines()
    entries: list[IndexEntry] = []
    current_topic = ""
    for line in lines:
        if line.startswith("## "):
            current_topic = line.removeprefix("## ").strip()
            continue
        match = ROW_PATTERN.match(line.strip())
        if match and current_topic:
            entries.append(
                IndexEntry(
                    topic=current_topic,
                    title=match.group("title"),
                    path=match.group("path"),
                    summary=match.group("summary"),
                    updated=match.group("updated"),
                )
            )
    return entries


def upsert_index_entry(
    index_path: Path,
    topic: str,
    article_title: str,
    article_path: str,
    summary: str,
    updated: str,
) -> None:
    entries = read_index_entries(index_path)
    by_topic: OrderedDict[str, list[IndexEntry]] = OrderedDict()
    for entry in entries:
        by_topic.setdefault(entry.topic, []).append(entry)

    topic_entries = by_topic.setdefault(topic, [])
    replacement = IndexEntry(
        topic=topic,
        title=article_title,
        path=article_path,
        summary=summary,
        updated=updated,
    )

    replaced = False
    for index, entry in enumerate(topic_entries):
        if entry.path == article_path:
            topic_entries[index] = replacement
            replaced = True
            break
    if not replaced:
        topic_entries.append(replacement)

    lines = ["# Knowledge Base Index", ""]
    for topic_name, entries_for_topic in by_topic.items():
        lines.extend(
            [
                f"## {topic_name}",
                "",
                f"Articles in {topic_name}.",
                "",
                "| Article | Summary | Updated |",
                "|---------|---------|---------|",
            ]
        )
        for entry in sorted(entries_for_topic, key=lambda item: item.title.lower()):
            lines.append(
                f"| [{entry.title}]({entry.path}) | {entry.summary} | {entry.updated} |"
            )
        lines.append("")
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def list_indexed_article_paths(index_path: Path) -> set[str]:
    return {entry.path for entry in read_index_entries(index_path)}
