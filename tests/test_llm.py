import json

from llm_wiki.llm import OpenAICompatibleClient
from llm_wiki.models import ArticleDocument, IndexEntry


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_complete_posts_openai_compatible_chat_request(monkeypatch):
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=30):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "hello back",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("llm_wiki.llm.urlopen", fake_urlopen)

    client = OpenAICompatibleClient(
        model="gpt-5.4",
        api_key="sk-test",
        base_url="https://example.com/v1",
    )

    result = client.complete("hello")

    assert result == "hello back"
    assert captured["url"] == "https://example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["content_type"] == "application/json"
    assert captured["body"] == {
        "model": "gpt-5.4",
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert captured["timeout"] == 30


def test_infer_article_parses_json_response_from_complete(monkeypatch):
    client = OpenAICompatibleClient(model="gpt-5.4", api_key="sk-test")
    monkeypatch.setattr(
        client,
        "complete",
        lambda prompt: '{"article_slug":"attention-mechanism","article_title":"Attention Mechanism","is_new":false}',
    )

    result = client.infer_article(
        raw_text="# Attention Notes\n\nTransformers use attention.",
        candidates=[
            IndexEntry(
                topic="transformers",
                title="Attention Mechanism",
                path="transformers/attention-mechanism.md",
                summary="Attention relates tokens.",
                updated="2026-04-20",
            )
        ],
    )

    assert result["article_slug"] == "attention-mechanism"
    assert result["article_title"] == "Attention Mechanism"
    assert result["is_new"] is False


def test_compile_article_includes_raw_path_and_existing_article(monkeypatch):
    captured: dict[str, str] = {}
    client = OpenAICompatibleClient(model="gpt-5.4", api_key="sk-test")

    def fake_complete(prompt: str) -> str:
        captured["prompt"] = prompt
        return "# Attention Mechanism\n"

    monkeypatch.setattr(client, "complete", fake_complete)

    result = client.compile_article(
        prompt="Compile article",
        raw_text="# Notes\n\nAttention matters.",
        raw_path="raw/transformers/attention-notes.md",
        topic="transformers",
        article_slug="attention-mechanism",
        article_title="Attention Mechanism",
        existing_article="# Attention Mechanism\n\n## Overview\n\nOld summary.\n",
    )

    assert result == "# Attention Mechanism\n"
    assert "raw/transformers/attention-notes.md" in captured["prompt"]
    assert "Attention Mechanism" in captured["prompt"]
    assert "Old summary." in captured["prompt"]


def test_answer_query_includes_candidate_documents(monkeypatch):
    captured: dict[str, str] = {}
    client = OpenAICompatibleClient(model="gpt-5.4", api_key="sk-test")

    def fake_complete(prompt: str) -> str:
        captured["prompt"] = prompt
        return "Attention helps models relate tokens."

    monkeypatch.setattr(client, "complete", fake_complete)

    result = client.answer_query(
        question="what does attention do",
        documents=[
            ArticleDocument(
                title="Attention Mechanism",
                sources_line="Test Source",
                raw_line="[attention-notes](../../raw/transformers/attention-notes.md)",
                body="## Overview\n\nAttention relates tokens.\n",
            )
        ],
    )

    assert result == "Attention helps models relate tokens."
    assert "what does attention do" in captured["prompt"]
    assert "Attention Mechanism" in captured["prompt"]
    assert "Attention relates tokens." in captured["prompt"]
