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
