import json
from pathlib import Path

from llm_wiki.models import ConfigLoadResult, ProviderConfig


SUPPORTED_PROTOCOLS = {"openai", "openai_compatible"}
DEFAULT_PROTOCOL = "openai"


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
    except (OSError, UnicodeDecodeError) as exc:
        return ConfigLoadResult(provider=None, errors=[f"Config read failed: {exc}"], path=path)
    except json.JSONDecodeError as exc:
        return ConfigLoadResult(provider=None, errors=[f"Invalid config JSON: {exc.msg}"], path=path)

    provider_data = raw.get("provider") if isinstance(raw, dict) else None
    if not isinstance(provider_data, dict):
        return ConfigLoadResult(
            provider=None,
            errors=["Config must contain a provider object"],
            path=path,
        )

    errors: list[str] = []
    protocol = _read_protocol(provider_data, errors)
    model = _read_required_string(provider_data, "model", errors)
    api_key = _read_required_string(provider_data, "api_key", errors)
    base_url = _read_optional_string(provider_data, "base_url", errors)

    if protocol is not None and protocol not in SUPPORTED_PROTOCOLS:
        errors.append("provider.protocol must be openai or openai_compatible")

    provider = ProviderConfig(
        protocol=protocol or DEFAULT_PROTOCOL,
        model=model or "",
        api_key=api_key or "",
        base_url=normalize_base_url(base_url),
    )

    return ConfigLoadResult(provider=provider, errors=errors, path=path)


def _read_protocol(provider_data: dict, errors: list[str]) -> str:
    value = provider_data.get("protocol", DEFAULT_PROTOCOL)
    if not isinstance(value, str):
        errors.append("provider.protocol must be a string")
        return DEFAULT_PROTOCOL
    normalized = value.strip()
    if not normalized:
        errors.append("provider.protocol must be openai or openai_compatible")
        return DEFAULT_PROTOCOL
    return normalized


def _read_required_string(provider_data: dict, field_name: str, errors: list[str]) -> str | None:
    value = provider_data.get(field_name)
    if not isinstance(value, str):
        errors.append(f"provider.{field_name} must be a string")
        return None
    normalized = value.strip()
    if not normalized:
        errors.append(f"provider.{field_name} is required")
        return None
    return normalized


def _read_optional_string(provider_data: dict, field_name: str, errors: list[str]) -> str:
    if field_name not in provider_data:
        return ""
    value = provider_data[field_name]
    if not isinstance(value, str):
        errors.append(f"provider.{field_name} must be a string")
        return ""
    return value
