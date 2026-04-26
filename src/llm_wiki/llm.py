import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from llm_wiki.config import normalize_base_url
from llm_wiki.models import ArticleDocument, IndexEntry, ProviderConfig, RawInput


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    def complete_with_raw(self, prompt: str, raw_input: RawInput) -> str:
        raise NotImplementedError

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        raise NotImplementedError

    def compile_article(self, **kwargs: object) -> str:
        raise NotImplementedError

    def answer_query(self, **kwargs: object) -> str:
        raise NotImplementedError

    def plan_ingest(self, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError

    def compile_page_change(self, **kwargs: object) -> str:
        raise NotImplementedError

    def generate_commit_message(self, **kwargs: object) -> str:
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

    def complete_with_raw(self, prompt: str, raw_input: RawInput) -> str:
        if raw_input.kind != "text":
            raise RuntimeError("Current provider cannot ingest image/pdf raw files.")
        return self.complete(
            "\n\n".join(
                [
                    prompt.strip(),
                    f"Raw path: {raw_input.relative_path}",
                    "Raw source:",
                    raw_input.text.strip(),
                ]
            )
        )

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

    def plan_ingest(self, **kwargs: object) -> dict[str, object]:
        prompt_template = _load_prompt("plan_ingest.md")
        candidates = kwargs.get("candidates", [])
        candidate_lines = []
        for entry in candidates:
            if isinstance(entry, IndexEntry):
                candidate_lines.append(f"- {entry.title} ({entry.path}): {entry.summary}")
        prompt = "\n\n".join(
            [
                prompt_template.strip(),
                f"Raw path: {kwargs.get('raw_path', '')}",
                "Existing candidate articles:",
                "\n".join(candidate_lines) if candidate_lines else "- (none)",
                "Raw markdown source:",
                str(kwargs.get("raw_text", "")).strip(),
            ]
        )
        raw_response = self.complete(prompt)
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned invalid plan_ingest JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("LLM plan_ingest response must be a JSON object.")
        changes = parsed.get("changes")
        if not isinstance(changes, list) or not 1 <= len(changes) <= 3:
            raise RuntimeError("LLM ingest plan must contain 1-3 changes.")
        return parsed

    def compile_page_change(self, **kwargs: object) -> str:
        prompt_template = _load_prompt("compile_page_change.md")
        prompt = "\n\n".join(
            [
                prompt_template.strip(),
                f"Action: {kwargs.get('action', '')}",
                f"Topic: {kwargs.get('topic', '')}",
                f"Target article slug: {kwargs.get('slug', '')}",
                f"Target article title: {kwargs.get('title', '')}",
                f"Reason: {kwargs.get('reason', '')}",
                f"Raw path: {kwargs.get('raw_path', '')}",
                "Existing article content:",
                str(kwargs.get("existing_article", "")).strip() or "(none)",
                "Raw markdown source:",
                str(kwargs.get("raw_text", "")).strip(),
            ]
        )
        return self.complete(prompt)

    def generate_commit_message(self, **kwargs: object) -> str:
        prompt_template = _load_prompt("commit_message.md")
        changed_paths = kwargs.get("changed_paths", [])
        paths = "\n".join(f"- {path}" for path in changed_paths) if isinstance(changed_paths, list) else ""
        prompt = "\n\n".join(
            [
                prompt_template.strip(),
                f"Source: {kwargs.get('source', '')}",
                f"Summary: {kwargs.get('summary', '')}",
                "Changed paths:",
                paths or "- (none)",
            ]
        )
        return self.complete(prompt)

    def _resolved_base_url(self) -> str:
        return self.base_url or "https://api.openai.com/v1"


@dataclass
class OpenAIResponsesClient:
    model: str
    api_key: str
    sdk_client: object | None = None

    def complete(self, prompt: str) -> str:
        response = self._client().responses.create(model=self.model, input=prompt)
        return _extract_response_text(response)

    def complete_with_raw(self, prompt: str, raw_input: RawInput) -> str:
        response = self._client().responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        self._raw_input_content(raw_input),
                    ],
                }
            ],
        )
        return _extract_response_text(response)

    def infer_article(self, raw_text: str, candidates: list[IndexEntry]) -> dict[str, object]:
        return _parse_json_response(_infer_article_prompt(raw_text, candidates), self.complete)

    def compile_article(self, **kwargs: object) -> str:
        return self.complete(_compile_article_prompt(**kwargs))

    def answer_query(self, **kwargs: object) -> str:
        return self.complete(_answer_query_prompt(**kwargs))

    def plan_ingest(self, **kwargs: object) -> dict[str, object]:
        raw_input = kwargs.get("raw_input")
        prompt = _plan_ingest_prompt(**kwargs)
        if isinstance(raw_input, RawInput):
            parsed = _parse_json_response(prompt, lambda value: self.complete_with_raw(value, raw_input))
        else:
            parsed = _parse_json_response(prompt, self.complete)
        changes = parsed.get("changes")
        if not isinstance(changes, list) or not 1 <= len(changes) <= 3:
            raise RuntimeError("LLM ingest plan must contain 1-3 changes.")
        return parsed

    def compile_page_change(self, **kwargs: object) -> str:
        raw_input = kwargs.get("raw_input")
        prompt = _compile_page_change_prompt(**kwargs)
        if isinstance(raw_input, RawInput):
            return self.complete_with_raw(prompt, raw_input)
        return self.complete(prompt)

    def generate_commit_message(self, **kwargs: object) -> str:
        return self.complete(_commit_message_prompt(**kwargs))

    def _client(self):
        if self.sdk_client is not None:
            return self.sdk_client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for provider.protocol=openai.") from exc
        return OpenAI(api_key=self.api_key)

    def _raw_input_content(self, raw_input: RawInput) -> dict[str, str]:
        if raw_input.kind == "text":
            return {
                "type": "input_text",
                "text": "\n\n".join(
                    [
                        f"Raw path: {raw_input.relative_path}",
                        "Raw source:",
                        raw_input.text,
                    ]
                ),
            }
        encoded = base64.b64encode(raw_input.path.read_bytes()).decode("ascii")
        data_url = f"data:{raw_input.mime_type};base64,{encoded}"
        if raw_input.kind == "image":
            return {"type": "input_image", "image_url": data_url}
        if raw_input.kind == "file":
            return {
                "type": "input_file",
                "filename": raw_input.path.name,
                "file_data": data_url,
            }
        raise RuntimeError(f"Unsupported raw input kind: {raw_input.kind}")


def build_llm_client(provider: ProviderConfig) -> LlmClient:
    if provider.protocol == "openai":
        return OpenAIResponsesClient(model=provider.model, api_key=provider.api_key)
    return build_openai_compatible_client(provider)


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


def _extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = getattr(response, "output", None)
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                for part in content:
                    text = getattr(part, "text", None)
                    if isinstance(text, str):
                        text_parts.append(text)
        combined = "".join(text_parts).strip()
        if combined:
            return combined
    raise RuntimeError("LLM response did not contain text content.")


def _parse_json_response(prompt: str, complete) -> dict[str, object]:
    raw_response = complete(prompt)
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned invalid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM JSON response must be an object.")
    return parsed


def _infer_article_prompt(raw_text: str, candidates: list[IndexEntry]) -> str:
    prompt_template = _load_prompt("infer_article.md")
    candidate_lines = [
        f"- {entry.title} ({entry.path}): {entry.summary}"
        for entry in candidates
    ]
    return "\n\n".join(
        [
            prompt_template.strip(),
            "Return JSON with keys article_slug, article_title, is_new.",
            "Existing candidate articles:",
            "\n".join(candidate_lines) if candidate_lines else "- (none)",
            "Raw markdown source:",
            raw_text.strip(),
        ]
    )


def _compile_article_prompt(**kwargs: object) -> str:
    prompt_template = str(kwargs.get("prompt", "")).strip() or _load_prompt("compile_article.md")
    return "\n\n".join(
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


def _answer_query_prompt(**kwargs: object) -> str:
    prompt_template = _load_prompt("answer_query.md")
    documents = kwargs.get("documents", [])
    rendered_documents = []
    for document in documents:
        if isinstance(document, ArticleDocument):
            rendered_documents.append(_render_document(document))
    return "\n\n".join(
        [
            prompt_template.strip(),
            f"Question: {kwargs.get('question', '')}",
            "Candidate wiki documents:",
            "\n\n".join(rendered_documents) if rendered_documents else "(none)",
        ]
    )


def _plan_ingest_prompt(**kwargs: object) -> str:
    prompt_template = _load_prompt("plan_ingest.md")
    candidates = kwargs.get("candidates", [])
    candidate_lines = []
    for entry in candidates:
        if isinstance(entry, IndexEntry):
            candidate_lines.append(f"- {entry.title} ({entry.path}): {entry.summary}")
    raw_input = kwargs.get("raw_input")
    raw_path = raw_input.relative_path if isinstance(raw_input, RawInput) else kwargs.get("raw_path", "")
    raw_text = raw_input.text if isinstance(raw_input, RawInput) and raw_input.kind == "text" else str(kwargs.get("raw_text", "")).strip()
    sections = [
        prompt_template.strip(),
        f"Raw path: {raw_path}",
        "Existing candidate articles:",
        "\n".join(candidate_lines) if candidate_lines else "- (none)",
    ]
    if raw_text:
        sections.extend(["Raw markdown source:", raw_text])
    else:
        sections.append("Raw content is attached as a model-readable file or image input.")
    return "\n\n".join(sections)


def _compile_page_change_prompt(**kwargs: object) -> str:
    prompt_template = _load_prompt("compile_page_change.md")
    raw_input = kwargs.get("raw_input")
    raw_path = raw_input.relative_path if isinstance(raw_input, RawInput) else kwargs.get("raw_path", "")
    raw_text = raw_input.text if isinstance(raw_input, RawInput) and raw_input.kind == "text" else str(kwargs.get("raw_text", "")).strip()
    sections = [
        prompt_template.strip(),
        f"Action: {kwargs.get('action', '')}",
        f"Topic: {kwargs.get('topic', '')}",
        f"Target article slug: {kwargs.get('slug', '')}",
        f"Target article title: {kwargs.get('title', '')}",
        f"Reason: {kwargs.get('reason', '')}",
        f"Raw path: {raw_path}",
        "Existing article content:",
        str(kwargs.get("existing_article", "")).strip() or "(none)",
    ]
    if raw_text:
        sections.extend(["Raw markdown source:", raw_text])
    else:
        sections.append("Raw content is attached as a model-readable file or image input.")
    return "\n\n".join(sections)


def _commit_message_prompt(**kwargs: object) -> str:
    prompt_template = _load_prompt("commit_message.md")
    changed_paths = kwargs.get("changed_paths", [])
    paths = "\n".join(f"- {path}" for path in changed_paths) if isinstance(changed_paths, list) else ""
    return "\n\n".join(
        [
            prompt_template.strip(),
            f"Source: {kwargs.get('source', '')}",
            f"Summary: {kwargs.get('summary', '')}",
            "Changed paths:",
            paths or "- (none)",
        ]
    )


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
