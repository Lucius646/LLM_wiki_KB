from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedCommand:
    name: str
    args: list[str]


@dataclass
class InitResult:
    created: list[str]
    git_initialized: bool = False
    baseline_committed: bool = False
    warnings: list[str] | None = None


@dataclass
class GitStatus:
    raw_wiki_changes: list[str]
    other_changes: list[str]

    @property
    def dirty(self) -> bool:
        return bool(self.raw_wiki_changes or self.other_changes)


@dataclass
class GitCommitResult:
    committed: bool
    commit_hash: str = ""
    message: str = ""


@dataclass
class WorkspaceStatus:
    root: Path
    raw_exists: bool
    wiki_exists: bool
    index_exists: bool
    log_exists: bool
    raw_file_count: int
    wiki_page_count: int
    initialized: bool


@dataclass
class ProviderConfig:
    protocol: str
    model: str
    api_key: str
    base_url: str = ""


@dataclass
class ConfigLoadResult:
    provider: ProviderConfig | None
    errors: list[str]
    path: Path


@dataclass
class ArticleDocument:
    title: str
    sources_line: str
    raw_line: str
    body: str


@dataclass
class IndexEntry:
    topic: str
    title: str
    path: str
    summary: str
    updated: str


@dataclass
class IngestResult:
    ok: bool
    message: str
    article_path: str = ""
    article_paths: list[str] | None = None


@dataclass
class PageChangePlan:
    action: str
    topic: str
    slug: str
    title: str
    reason: str


@dataclass
class IngestPlan:
    summary: str
    changes: list[PageChangePlan]
    warnings: list[str]


@dataclass
class QueryResult:
    ok: bool
    answer: str


@dataclass
class LintResult:
    ok: bool
    issues: list[str]
