from dataclasses import dataclass
from typing import Protocol

from llm_wiki.config import normalize_base_url
from llm_wiki.models import IndexEntry, ProviderConfig


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        raise NotImplementedError

    def compile_article(self, **kwargs: object) -> str:
        raise NotImplementedError


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key: str
    base_url: str | None = None

    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        raise NotImplementedError

    def compile_article(self, **kwargs: object) -> str:
        raise NotImplementedError


def build_openai_compatible_client(provider: ProviderConfig) -> LlmClient:
    kwargs: dict[str, str] = {
        "model": provider.model,
        "api_key": provider.api_key,
    }
    base_url = normalize_base_url(provider.base_url)
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAICompatibleClient(**kwargs)
