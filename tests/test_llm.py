import json
import shutil
import uuid

from pathlib import Path

import pytest

from llm_wiki.llm import OpenAICompatibleClient, OpenAIResponsesClient, build_llm_client
from llm_wiki.models import ArticleDocument, IndexEntry, ProviderConfig, RawInput


@pytest.fixture
def workspace_root() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_llm_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("Response", (), {"output_text": "hello back"})()


class FakeOpenAI:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_responses_client_sends_text_input():
    sdk = FakeOpenAI()
    client = OpenAIResponsesClient(model="gpt-5.5", api_key="sk-test", sdk_client=sdk)

    result = client.complete("hello")

    assert result == "hello back"
    assert sdk.responses.calls[0]["model"] == "gpt-5.5"
    assert sdk.responses.calls[0]["input"] == "hello"


def test_openai_responses_client_sends_image_raw_input(workspace_root: Path):
    sdk = FakeOpenAI()
    raw_path = workspace_root / "shot.png"
    raw_path.write_bytes(b"image-bytes")
    raw_input = RawInput(
        ok=True,
        root=workspace_root,
        path=raw_path,
        relative_path="raw/shot.png",
        mime_type="image/png",
        kind="image",
    )
    client = OpenAIResponsesClient(model="gpt-5.5", api_key="sk-test", sdk_client=sdk)

    result = client.complete_with_raw(prompt="describe", raw_input=raw_input)

    assert result == "hello back"
    content = sdk.responses.calls[0]["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "describe"}
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


def test_openai_responses_client_sends_pdf_raw_input(workspace_root: Path):
    sdk = FakeOpenAI()
    raw_path = workspace_root / "paper.pdf"
    raw_path.write_bytes(b"%PDF-1.4")
    raw_input = RawInput(
        ok=True,
        root=workspace_root,
        path=raw_path,
        relative_path="raw/paper.pdf",
        mime_type="application/pdf",
        kind="file",
    )
    client = OpenAIResponsesClient(model="gpt-5.5", api_key="sk-test", sdk_client=sdk)

    result = client.complete_with_raw(prompt="read", raw_input=raw_input)

    assert result == "hello back"
    content = sdk.responses.calls[0]["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "read"}
    assert content[1]["type"] == "input_file"
    assert content[1]["filename"] == "paper.pdf"
    assert content[1]["file_data"].startswith("data:application/pdf;base64,")


def test_openai_compatible_rejects_non_text_raw_input(workspace_root: Path):
    raw_path = workspace_root / "paper.pdf"
    raw_path.write_bytes(b"%PDF-1.4")
    raw_input = RawInput(
        ok=True,
        root=workspace_root,
        path=raw_path,
        relative_path="raw/paper.pdf",
        mime_type="application/pdf",
        kind="file",
    )
    client = OpenAICompatibleClient(model="gpt-5.4", api_key="sk-test")

    with pytest.raises(RuntimeError, match="cannot ingest image/pdf"):
        client.complete_with_raw("read", raw_input)


def test_build_llm_client_uses_openai_responses_for_openai_protocol():
    client = build_llm_client(
        ProviderConfig(protocol="openai", model="gpt-5.5", api_key="sk-test")
    )

    assert isinstance(client, OpenAIResponsesClient)


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
