import shutil
import uuid
from pathlib import Path

import pytest

from llm_wiki.config import load_config, normalize_base_url


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


def test_load_config_requires_model_and_api_key(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("USERPROFILE", str(home))
    config_path = home / ".llm-wiki" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '{"provider":{"protocol":"openai_compatible","model":"","api_key":""}}',
        encoding="utf-8",
    )
    errors = load_config().errors
    assert "model" in errors[0].lower()
