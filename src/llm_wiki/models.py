from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedCommand:
    name: str
    args: list[str]


@dataclass
class InitResult:
    created: list[str]


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


@dataclass
class QueryResult:
    ok: bool
    answer: str


@dataclass
class LintResult:
    ok: bool
    issues: list[str]
