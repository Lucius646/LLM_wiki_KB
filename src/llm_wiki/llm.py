import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from llm_wiki.config import normalize_base_url
from llm_wiki.models import ArticleDocument, IndexEntry, ProviderConfig


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        raise NotImplementedError

    def compile_article(self, **kwargs: object) -> str:
        raise NotImplementedError

    def answer_query(self, **kwargs: object) -> str:
        raise NotImplementedError


@dataclass
class OpenAICompatibleClient:
    model: str
    api_key: str
    base_url: str | None = None

    def complete(self, prompt: str) -> str:
        endpoint = f"{self._resolved_base_url()}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code} {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("LLM response did not contain choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            combined = "".join(text_parts).strip()
            if combined:
                return combined
        raise RuntimeError("LLM response did not contain text content.")

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        prompt_template = _load_prompt("infer_article.md")
        candidate_lines = [
            f"- {entry.title} ({entry.path}): {entry.summary}"
            for entry in candidates
        ]
        prompt = "\n\n".join(
            [
                prompt_template.strip(),
                "Return JSON with keys article_slug, article_title, is_new.",
                "Existing candidate articles:",
                "\n".join(candidate_lines) if candidate_lines else "- (none)",
                "Raw markdown source:",
                raw_text.strip(),
            ]
        )
        raw_response = self.complete(prompt)
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned invalid infer_article JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("LLM infer_article response must be a JSON object.")
        return parsed

    def compile_article(self, **kwargs: object) -> str:
        prompt_template = str(kwargs.get("prompt", "")).strip() or _load_prompt("compile_article.md")
        prompt = "\n\n".join(
            [
                prompt_template,
                f"Topic: {kwargs.get('topic', '')}",
                f"Target article slug: {kwargs.get('article_slug', '')}",
                f"Target article title: {kwargs.get('article_title', '')}",
                f"Raw path: {kwargs.get('raw_path', '')}",
                "Existing article content:",
                str(kwargs.get("existing_article", "")).strip() or "(none)",
                "Raw markdown source:",
                str(kwargs.get("raw_text", "")).strip(),
            ]
        )
        return self.complete(prompt)

    def answer_query(self, **kwargs: object) -> str:
        prompt_template = _load_prompt("answer_query.md")
        documents = kwargs.get("documents", [])
        rendered_documents = []
        for document in documents:
            if isinstance(document, ArticleDocument):
                rendered_documents.append(_render_document(document))
        prompt = "\n\n".join(
            [
                prompt_template.strip(),
                f"Question: {kwargs.get('question', '')}",
                "Candidate wiki documents:",
                "\n\n".join(rendered_documents) if rendered_documents else "(none)",
            ]
        )
        return self.complete(prompt)

    def _resolved_base_url(self) -> str:
        return self.base_url or "https://api.openai.com/v1"


def build_openai_compatible_client(provider: ProviderConfig) -> LlmClient:
    kwargs: dict[str, str] = {
        "model": provider.model,
        "api_key": provider.api_key,
    }
    base_url = normalize_base_url(provider.base_url)
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAICompatibleClient(**kwargs)


def _load_prompt(name: str) -> str:
    prompts_dir = Path(__file__).resolve().parent / "prompts"
    return (prompts_dir / name).read_text(encoding="utf-8")


def _render_document(document: ArticleDocument) -> str:
    return "\n".join(
        [
            f"# {document.title}",
            f"> Sources: {document.sources_line}",
            f"> Raw: {document.raw_line}",
            "",
            document.body.strip(),
        ]
    ).strip()
