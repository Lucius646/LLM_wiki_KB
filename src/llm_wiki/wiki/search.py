import re
from pathlib import Path

from llm_wiki.models import IndexEntry
from llm_wiki.wiki.index import read_index_entries


def search_index(index_path: Path, query: str) -> list[IndexEntry]:
    tokens = [token for token in re.split(r"\W+", query.lower()) if token]
    scored: list[tuple[int, IndexEntry]] = []
    for entry in read_index_entries(index_path):
        haystack_title = entry.title.lower()
        haystack_summary = entry.summary.lower()
        score = 0
        for token in tokens:
            if token in haystack_title:
                score += 2
            if token in haystack_summary:
                score += 1
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
    return [entry for _, entry in scored]
