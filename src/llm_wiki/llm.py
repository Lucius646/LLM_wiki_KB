from dataclasses import dataclass
from typing import Protocol

from llm_wiki.models import ProviderConfig


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key: str
    base_url: str | None = None

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


def build_openai_compatible_client(provider: ProviderConfig) -> LlmClient:
    kwargs: dict[str, str] = {
        "model": provider.model,
        "api_key": provider.api_key,
    }
    if provider.base_url:
        kwargs["base_url"] = provider.base_url
    return OpenAICompatibleClient(**kwargs)
