import shutil
import json
import uuid
from pathlib import Path

import pytest

from llm_wiki.config import load_config, normalize_base_url
from llm_wiki.llm import build_openai_compatible_client
from llm_wiki.models import ProviderConfig


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parent / f"_tmp_path_{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_normalize_base_url_trims_whitespace_and_trailing_slash():
    assert normalize_base_url(" https://example.com/v1/ ") == "https://example.com/v1"


def test_load_config_returns_valid_provider_and_normalized_base_url(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "provider": {
                    "protocol": "openai_compatible",
                    "model": "gpt-5.4",
                    "api_key": "sk-test",
                    "base_url": " https://example.com/v1/ ",
                }
            }
        ),
        encoding="utf-8",
    )
    result = load_config()

    assert result.errors == []
    assert result.provider is not None
    assert result.provider.base_url == "https://example.com/v1"


def test_load_config_accepts_openai_protocol(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '{"provider":{"protocol":"openai","model":"gpt-5.5","api_key":"sk-test"}}',
        encoding="utf-8",
    )

    result = load_config()

    assert result.errors == []
    assert result.provider is not None
    assert result.provider.protocol == "openai"


def test_load_config_defaults_to_openai_protocol(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '{"provider":{"model":"gpt-5.5","api_key":"sk-test"}}',
        encoding="utf-8",
    )

    result = load_config()

    assert result.errors == []
    assert result.provider is not None
    assert result.provider.protocol == "openai"


def test_load_config_rejects_non_string_provider_fields(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "provider": {
                    "protocol": None,
                    "model": 123,
                    "api_key": ["sk-test"],
                    "base_url": {"url": "https://example.com/v1"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = load_config()

    assert result.provider is not None
    assert any("protocol" in error.lower() for error in result.errors)
    assert any("model" in error.lower() for error in result.errors)
    assert any("api_key" in error.lower() for error in result.errors)
    assert any("base_url" in error.lower() for error in result.errors)


def test_load_config_reports_invalid_json(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("{not json}", encoding="utf-8")

    result = load_config()

    assert result.provider is None
    assert result.errors
    assert "invalid config json" in result.errors[0].lower()


def test_load_config_reports_missing_provider_object(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"not_provider":{}}', encoding="utf-8")

    result = load_config()

    assert result.provider is None
    assert result.errors == ["Config must contain a provider object"]


@pytest.mark.parametrize("error", [OSError("boom"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")])
def test_load_config_reports_file_read_errors(tmp_path: Path, monkeypatch, error):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", lambda self, encoding="utf-8": (_ for _ in ()).throw(error))

    result = load_config()

    assert result.provider is None
    assert result.errors
    assert "config" in result.errors[0].lower()


def test_load_config_requires_model_and_api_key(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '{"provider":{"protocol":"openai_compatible","model":"","api_key":""}}',
        encoding="utf-8",
    )
    result = load_config()

    assert result.provider is not None
    assert any("model" in error.lower() for error in result.errors)
    assert any("api_key" in error.lower() for error in result.errors)


def test_build_openai_compatible_client_omits_empty_or_whitespace_base_url():
    client = build_openai_compatible_client(
        ProviderConfig(
            protocol="openai_compatible",
            model="gpt-5.4",
            api_key="sk-test",
            base_url="   ",
        )
    )

    assert client.model == "gpt-5.4"
    assert client.api_key == "sk-test"
    assert client.base_url is None
