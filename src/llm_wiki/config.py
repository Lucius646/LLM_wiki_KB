import json
from pathlib import Path

from llm_wiki.models import ConfigLoadResult, ProviderConfig


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/") if url else ""


def get_default_config_path() -> Path:
    home = Path.home()
    return home / ".llm-wiki" / "config.json"


def load_config() -> ConfigLoadResult:
    path = get_default_config_path()
    if not path.is_file():
        return ConfigLoadResult(provider=None, errors=[f"Config not found: {path}"], path=path)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ConfigLoadResult(provider=None, errors=[f"Invalid config JSON: {exc.msg}"], path=path)

    provider_data = raw.get("provider") if isinstance(raw, dict) else None
    if not isinstance(provider_data, dict):
        return ConfigLoadResult(
            provider=None,
            errors=["Config must contain a provider object"],
            path=path,
        )

    provider = ProviderConfig(
        protocol=str(provider_data.get("protocol", "openai_compatible")).strip() or "openai_compatible",
        model=str(provider_data.get("model", "")).strip(),
        api_key=str(provider_data.get("api_key", "")).strip(),
        base_url=normalize_base_url(str(provider_data.get("base_url", ""))),
    )

    errors: list[str] = []
    if provider.protocol != "openai_compatible":
        errors.append("provider.protocol must be openai_compatible")
    if not provider.model:
        errors.append("provider.model is required")
    if not provider.api_key:
        errors.append("provider.api_key is required")

    return ConfigLoadResult(provider=provider, errors=errors, path=path)
