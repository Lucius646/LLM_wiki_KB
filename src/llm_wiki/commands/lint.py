from pathlib import Path

from llm_wiki.models import LintResult
from llm_wiki.wiki.article import extract_raw_links, extract_wiki_links, load_article
from llm_wiki.wiki.index import list_indexed_article_paths


def lint_workspace(root: Path) -> LintResult:
    issues: list[str] = []
    issues.extend(find_missing_index_entries(root))
    issues.extend(find_broken_wiki_links(root))
    issues.extend(find_broken_raw_links(root))
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


def _iter_wiki_articles(root: Path):
    wiki_root = root / "wiki"
    for article_path in wiki_root.rglob("*.md"):
        if article_path.name in {"index.md", "log.md"} and article_path.parent == wiki_root:
            continue
        yield article_path
