from pathlib import Path
import re

from llm_wiki.models import LintResult
from llm_wiki.wiki.article import extract_raw_links, extract_wiki_links, load_article
from llm_wiki.wiki.index import list_indexed_article_paths


def lint_workspace(root: Path) -> LintResult:
    issues: list[str] = []
    issues.extend(find_missing_index_entries(root))
    issues.extend(find_missing_article_metadata(root))
    issues.extend(find_broken_wiki_links(root))
    issues.extend(find_broken_raw_links(root))
    issues.extend(find_broken_log_references(root))
    issues.extend(find_orphan_pages(root))
    issues.extend(find_duplicate_candidates(root))
    return LintResult(ok=not issues, issues=issues)


def find_missing_index_entries(root: Path) -> list[str]:
    wiki_root = root / "wiki"
    indexed = list_indexed_article_paths(wiki_root / "index.md")
    issues: list[str] = []
    for article_path in wiki_root.rglob("*.md"):
        if article_path.name in {"index.md", "log.md"} and article_path.parent == wiki_root:
            continue
        relative = article_path.relative_to(wiki_root).as_posix()
        if relative not in indexed:
            issues.append(f"Wiki page missing from index: {relative}")
    return issues


def find_broken_wiki_links(root: Path) -> list[str]:
    issues: list[str] = []
    for article_path in _iter_wiki_articles(root):
        document = load_article(article_path)
        for target in extract_wiki_links(article_path, document):
            if not Path(target).exists():
                issues.append(f"Broken wiki link in {article_path.relative_to(root).as_posix()}: {target}")
    return issues


def find_broken_raw_links(root: Path) -> list[str]:
    issues: list[str] = []
    for article_path in _iter_wiki_articles(root):
        document = load_article(article_path)
        for target in extract_raw_links(article_path, document):
            if not Path(target).exists():
                issues.append(f"Broken raw reference in {article_path.relative_to(root).as_posix()}: {target}")
    return issues


def find_missing_article_metadata(root: Path) -> list[str]:
    issues: list[str] = []
    for article_path in _iter_wiki_articles(root):
        document = load_article(article_path)
        relative = article_path.relative_to(root).as_posix()
        if not document.sources_line:
            issues.append(f"Wiki page missing Sources metadata: {relative}")
        if not document.raw_line:
            issues.append(f"Wiki page missing Raw metadata: {relative}")
    return issues


def find_broken_log_references(root: Path) -> list[str]:
    log_path = root / "wiki" / "log.md"
    if not log_path.is_file():
        return []
    text = log_path.read_text(encoding="utf-8")
    issues: list[str] = []
    for source in re.findall(r"^## \[[^\]]+\] ingest \| (?P<source>raw/[^\s]+)$", text, flags=re.MULTILINE):
        if not (root / source).exists():
            issues.append(f"Log references missing raw source: {source}")
    for wiki_path in sorted(set(re.findall(r"wiki/[^\s)]+\.md", text))):
        if not (root / wiki_path).exists():
            issues.append(f"Log references missing wiki page: {wiki_path}")
    return issues


def find_orphan_pages(root: Path) -> list[str]:
    articles = list(_iter_wiki_articles(root))
    incoming: set[Path] = set()
    for article_path in articles:
        document = load_article(article_path)
        for target in extract_wiki_links(article_path, document):
            incoming.add(Path(target).resolve())
    issues: list[str] = []
    for article_path in articles:
        if article_path.resolve() not in incoming:
            issues.append(f"Report-only orphan wiki page: {article_path.relative_to(root).as_posix()}")
    return issues


def find_duplicate_candidates(root: Path) -> list[str]:
    by_title: dict[str, list[str]] = {}
    by_slug: dict[str, list[str]] = {}
    for article_path in _iter_wiki_articles(root):
        document = load_article(article_path)
        relative = article_path.relative_to(root).as_posix()
        if document.title:
            by_title.setdefault(document.title.strip().lower(), []).append(relative)
        by_slug.setdefault(article_path.stem.lower(), []).append(relative)

    issues: list[str] = []
    for title, paths in by_title.items():
        if len(paths) > 1:
            issues.append(f"Report-only duplicate title candidate '{title}': {', '.join(paths)}")
    for slug, paths in by_slug.items():
        if len(paths) > 1:
            issues.append(f"Report-only duplicate slug candidate '{slug}': {', '.join(paths)}")
    return issues


def _iter_wiki_articles(root: Path):
    wiki_root = root / "wiki"
    for article_path in wiki_root.rglob("*.md"):
        if article_path.name in {"index.md", "log.md"} and article_path.parent == wiki_root:
            continue
        yield article_path
