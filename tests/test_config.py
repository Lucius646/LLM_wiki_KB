import shutil
from pathlib import Path

from llm_wiki.config import load_config, normalize_base_url
from llm_wiki.llm import build_openai_compatible_client
from llm_wiki.models import ProviderConfig


def test_normalize_base_url_trims_whitespace_and_trailing_slash():
    assert normalize_base_url(" https://example.com/v1/ ") == "https://example.com/v1"


def test_load_config_requires_model_and_api_key(monkeypatch):
    home = Path(__file__).resolve().parent / "_config_home"
    shutil.rmtree(home, ignore_errors=True)
    try:
        home.mkdir(parents=True)
        monkeypatch.setenv("USERPROFILE", str(home))
        config_path = home / ".llm-wiki" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            '{"provider":{"protocol":"openai_compatible","model":"","api_key":""}}',
            encoding="utf-8",
        )
        errors = load_config().errors
        assert "model" in errors[0].lower()
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_build_openai_compatible_client_omits_empty_base_url():
    client = build_openai_compatible_client(
        ProviderConfig(
            protocol="openai_compatible",
            model="gpt-5.4",
            api_key="sk-test",
            base_url="",
        )
    )

    assert client.model == "gpt-5.4"
    assert client.api_key == "sk-test"
    assert client.base_url is None
