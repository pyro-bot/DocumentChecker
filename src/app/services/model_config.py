import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_MODELS_PATH = Path(__file__).resolve().parents[3] / "models.yaml"


@dataclass(frozen=True)
class EndpointDefinition:
    id: str
    url: str
    base_url: str
    api_format: str
    api_key_env: str


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    description: str
    usage_limit: Optional[int]
    endpoint_id: Optional[str]
    request_model: str
    api_url: str
    api_base_url: str
    api_format: str
    api_key_env: str


@dataclass(frozen=True)
class ModelsConfig:
    default_model: str
    models: tuple[ModelDefinition, ...]
    endpoints: tuple[EndpointDefinition, ...] = ()

    def get(self, model_id: str) -> Optional[ModelDefinition]:
        return next((model for model in self.models if model.id == model_id), None)

    def get_endpoint(self, endpoint_id: str) -> Optional[EndpointDefinition]:
        return next((endpoint for endpoint in self.endpoints if endpoint.id == endpoint_id), None)


class ModelsConfigError(Exception):
    pass


_cached_config: Optional[ModelsConfig] = None
_cached_mtime: Optional[float] = None


def models_config_path() -> Path:
    return Path(os.getenv("MODELS_CONFIG_PATH", str(DEFAULT_MODELS_PATH))).resolve()


def load_models_config() -> ModelsConfig:
    global _cached_config, _cached_mtime

    path = models_config_path()
    mtime = path.stat().st_mtime if path.exists() else None
    if _cached_config is not None and _cached_mtime == mtime:
        return _cached_config

    if not path.exists():
        raise ModelsConfigError(f"Models config not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    config = _parse_models_config(raw)
    _cached_config = config
    _cached_mtime = mtime
    return config


def _parse_models_config(raw: dict[str, Any]) -> ModelsConfig:
    endpoints = _parse_endpoints(raw.get("endpoints", []))
    endpoint_ids = {endpoint.id for endpoint in endpoints}

    items = raw.get("models")
    if not isinstance(items, list) or not items:
        raise ModelsConfigError("models.yaml must contain a non-empty 'models' list")

    models: list[ModelDefinition] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ModelsConfigError("Each model entry must be an object")

        model_id = str(item.get("id") or "").strip()
        if not model_id:
            raise ModelsConfigError("Each model entry must contain a non-empty 'id'")
        if model_id in seen:
            raise ModelsConfigError(f"Duplicate model id in models.yaml: {model_id}")
        seen.add(model_id)

        raw_limit = item.get("usage_limit")
        if raw_limit in (None, ""):
            usage_limit = None
        else:
            usage_limit = int(raw_limit)
            if usage_limit < 0:
                raise ModelsConfigError(f"usage_limit must be non-negative for model: {model_id}")

        endpoint_id = item.get("endpoint") or item.get("endpoint_id")
        if endpoint_id is not None:
            endpoint_id = str(endpoint_id).strip()
            if endpoint_id and endpoint_id not in endpoint_ids:
                raise ModelsConfigError(f"Unknown endpoint for model {model_id}: {endpoint_id}")
        if not endpoint_id:
            endpoint_id = None

        models.append(
            ModelDefinition(
                id=model_id,
                name=str(item.get("name") or model_id),
                description=str(item.get("description") or ""),
                usage_limit=usage_limit,
                endpoint_id=endpoint_id,
                request_model=str(item.get("request_model") or item.get("model") or model_id).strip(),
                api_url=str(item.get("api_url") or item.get("url") or "").strip(),
                api_base_url=str(item.get("api_base_url") or item.get("base_url") or "").strip(),
                api_format=str(item.get("api_format") or item.get("format") or "").strip().lower(),
                api_key_env=str(item.get("api_key_env") or "").strip(),
            )
        )

    default_model = str(raw.get("default_model") or models[0].id).strip()
    if default_model not in seen:
        raise ModelsConfigError("default_model must reference a model from the models list")

    return ModelsConfig(default_model=default_model, models=tuple(models), endpoints=endpoints)


def _parse_endpoints(raw_endpoints: Any) -> tuple[EndpointDefinition, ...]:
    if raw_endpoints in (None, ""):
        return ()

    if isinstance(raw_endpoints, dict):
        items = [{"id": endpoint_id, **(value or {})} for endpoint_id, value in raw_endpoints.items()]
    elif isinstance(raw_endpoints, list):
        items = raw_endpoints
    else:
        raise ModelsConfigError("endpoints must be a list or an object")

    endpoints: list[EndpointDefinition] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ModelsConfigError("Each endpoint entry must be an object")

        endpoint_id = str(item.get("id") or "").strip()
        if not endpoint_id:
            raise ModelsConfigError("Each endpoint entry must contain a non-empty 'id'")
        if endpoint_id in seen:
            raise ModelsConfigError(f"Duplicate endpoint id in models.yaml: {endpoint_id}")
        seen.add(endpoint_id)

        api_format = str(item.get("api_format") or item.get("format") or "auto").strip().lower()
        if api_format not in {"auto", "openai", "ollama", "nanogpt"}:
            raise ModelsConfigError(f"Unsupported api_format for endpoint {endpoint_id}: {api_format}")

        endpoints.append(
            EndpointDefinition(
                id=endpoint_id,
                url=str(item.get("api_url") or item.get("url") or "").strip(),
                base_url=str(item.get("api_base_url") or item.get("base_url") or "").strip(),
                api_format=api_format,
                api_key_env=str(item.get("api_key_env") or "").strip(),
            )
        )

    return tuple(endpoints)


def default_model_id() -> str:
    return load_models_config().default_model
