from pathlib import Path

from llm_wiki.models import InitResult, WorkspaceStatus


def init_workspace(root: Path) -> InitResult:
    created: list[str] = []
    raw_dir = root / "raw"
    wiki_dir = root / "wiki"
    index_path = wiki_dir / "index.md"
    log_path = wiki_dir / "log.md"
    for path in (raw_dir, wiki_dir):
        if not path.exists():
            path.mkdir(parents=True)
            created.append(str(path.relative_to(root)))
    if not index_path.exists():
        index_path.write_text("# Knowledge Base Index\n", encoding="utf-8")
        created.append("wiki/index.md")
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n", encoding="utf-8")
        created.append("wiki/log.md")
    return InitResult(created=created)


def detect_workspace(root: Path) -> WorkspaceStatus:
    raw_dir = root / "raw"
    wiki_dir = root / "wiki"
    index_path = wiki_dir / "index.md"
    log_path = wiki_dir / "log.md"
    raw_exists = raw_dir.is_dir()
    wiki_exists = wiki_dir.is_dir()
    index_exists = index_path.is_file()
    log_exists = log_path.is_file()
    raw_file_count = _count_files(raw_dir)
    wiki_page_count = _count_wiki_pages(wiki_dir)
    initialized = raw_exists and wiki_exists and index_exists and log_exists
    return WorkspaceStatus(
        root=root,
        raw_exists=raw_exists,
        wiki_exists=wiki_exists,
        index_exists=index_exists,
        log_exists=log_exists,
        raw_file_count=raw_file_count,
        wiki_page_count=wiki_page_count,
        initialized=initialized,
    )


def _count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file())


def _count_wiki_pages(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    reserved_root_files = {directory / "index.md", directory / "log.md"}
    return sum(
        1
        for path in directory.rglob("*.md")
        if path.is_file() and path not in reserved_root_files
    )
