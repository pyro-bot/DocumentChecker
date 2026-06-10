import logging
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Optional
from urllib.parse import quote, urlparse, urlunparse

import requests

try:
    import tiktoken
except Exception:  # pragma: no cover - optional dependency fallback
    tiktoken = None


DEFAULT_CONTEXT_WINDOW_TOKENS = 128_000
CONTEXT_SAFETY_MARGIN_TOKENS = 1_024
DOCUMENT_TRUNCATION_MARKER = (
    "\n\n[Документ обрезан автоматически: исходный текст не помещался "
    "в контекстное окно выбранной модели.]"
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptFitResult:
    document: str
    truncated: bool
    original_document_tokens: int
    final_document_tokens: int
    max_context_tokens: int
    document_token_budget: int


def fit_document_to_context(
    *,
    system_prompt: str,
    build_user_prompt: Callable[[str, str, str], str],
    template: str,
    document: str,
    check_type: str,
    settings,
) -> PromptFitResult:
    max_context_tokens = resolve_context_window(settings)
    response_reserve = _response_token_reserve(max_context_tokens)
    empty_document_prompt = build_user_prompt(template, "", check_type)
    fixed_prompt_tokens = count_chat_tokens(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": empty_document_prompt},
        ],
        settings.model,
    )
    document_token_budget = (
        max_context_tokens
        - response_reserve
        - CONTEXT_SAFETY_MARGIN_TOKENS
        - fixed_prompt_tokens
    )
    marker_tokens = count_text_tokens(DOCUMENT_TRUNCATION_MARKER, settings.model)
    document_token_budget = max(document_token_budget, 0)

    original_document_tokens = count_text_tokens(document, settings.model)
    if original_document_tokens <= document_token_budget:
        return PromptFitResult(
            document=document,
            truncated=False,
            original_document_tokens=original_document_tokens,
            final_document_tokens=original_document_tokens,
            max_context_tokens=max_context_tokens,
            document_token_budget=document_token_budget,
        )

    if document_token_budget <= 0:
        truncated_document = ""
    elif document_token_budget <= marker_tokens:
        truncated_document = truncate_text_to_tokens(
            DOCUMENT_TRUNCATION_MARKER.strip(),
            document_token_budget,
            settings.model,
        )
    else:
        truncated_budget = document_token_budget - marker_tokens
        truncated_document = truncate_text_to_tokens(document, truncated_budget, settings.model)
        truncated_document = f"{truncated_document}{DOCUMENT_TRUNCATION_MARKER}"

    return PromptFitResult(
        document=truncated_document,
        truncated=True,
        original_document_tokens=original_document_tokens,
        final_document_tokens=count_text_tokens(truncated_document, settings.model),
        max_context_tokens=max_context_tokens,
        document_token_budget=document_token_budget,
    )


def resolve_context_window(settings) -> int:
    model_configured_limit = getattr(settings, "context_window_tokens", None)
    if model_configured_limit:
        return model_configured_limit

    configured_limit = _read_positive_int_env("LLM_CONTEXT_WINDOW_TOKENS")
    if configured_limit:
        return configured_limit

    api_limit = _fetch_context_window_from_api(
        api_format=settings.api_format,
        url=settings.url,
        model=settings.model,
        api_key_env=settings.api_key_env,
    )
    if api_limit:
        return api_limit

    return context_window_for_model(settings.model)


def context_window_for_model(model: str) -> int:
    normalized = _normalize_model_name(model)
    model_limits = [
        (r"\bgpt-5", 400_000),
        (r"\bgpt-4\.1", 1_047_576),
        (r"\bgpt-4o", 128_000),
        (r"\bo[34](?:-|$)", 200_000),
        (r"\bgpt-oss", 131_072),
        (r"\bdeepseek", 128_000),
        (r"\bqwen", 128_000),
        (r"\bminimax", 1_000_000),
    ]
    for pattern, limit in model_limits:
        if re.search(pattern, normalized):
            return limit
    return DEFAULT_CONTEXT_WINDOW_TOKENS


def count_chat_tokens(messages: list[dict], model: str) -> int:
    # OpenAI chat messages have a small protocol overhead per message.
    return 3 + sum(4 + count_text_tokens(str(message.get("content", "")), model) for message in messages)


def count_text_tokens(text: str, model: str) -> int:
    encoder = _token_encoder(model)
    if encoder is not None:
        return len(encoder.encode(text))

    if not text:
        return 0
    # Conservative fallback for Cyrillic-heavy text when tiktoken is unavailable.
    return max(1, math.ceil(len(text.encode("utf-8")) / 2))


def truncate_text_to_tokens(text: str, max_tokens: int, model: str) -> str:
    if max_tokens <= 0 or not text:
        return ""

    encoder = _token_encoder(model)
    if encoder is not None:
        tokens = encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return encoder.decode(tokens[:max_tokens]).rstrip()

    if count_text_tokens(text, model) <= max_tokens:
        return text

    left, right = 0, len(text)
    while left < right:
        mid = (left + right + 1) // 2
        if count_text_tokens(text[:mid], model) <= max_tokens:
            left = mid
        else:
            right = mid - 1
    return text[:left].rstrip()


def _response_token_reserve(max_context_tokens: int) -> int:
    return min(8_192, max(1_024, max_context_tokens // 16))


def _read_positive_int_env(name: str) -> Optional[int]:
    raw_value = os.getenv(name)
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Ignoring invalid %s=%r", name, raw_value)
        return None
    return value if value > 0 else None


@lru_cache(maxsize=128)
def _fetch_context_window_from_api(
    *,
    api_format: str,
    url: str,
    model: str,
    api_key_env: str,
) -> Optional[int]:
    try:
        if api_format in {"openai", "nanogpt"}:
            return _fetch_openai_compatible_context_window(url, model, api_format, api_key_env)
        if api_format == "ollama":
            return _fetch_ollama_context_window(url, model, api_key_env)
    except Exception:
        logger.debug("Unable to fetch model context window from API", exc_info=True)
    return None


def _fetch_openai_compatible_context_window(
    chat_url: str,
    model: str,
    api_format: str,
    api_key_env: str,
) -> Optional[int]:
    base_url = _openai_compatible_base_url(chat_url)
    headers = _api_headers(api_format, api_key_env)

    direct_url = f"{base_url}/models/{quote(model, safe='')}"
    response = requests.get(direct_url, headers=headers, timeout=10)
    if response.ok:
        limit = _extract_context_window(response.json())
        if limit:
            return limit

    response = requests.get(f"{base_url}/models", headers=headers, timeout=10)
    if not response.ok:
        return None

    data = response.json()
    models = data.get("data") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return _extract_context_window(data)

    for item in models:
        if not isinstance(item, dict):
            continue
        if item.get("id") == model or item.get("model") == model or item.get("name") == model:
            return _extract_context_window(item)
    return None


def _fetch_ollama_context_window(chat_url: str, model: str, api_key_env: str) -> Optional[int]:
    show_url = _ollama_show_url(chat_url)
    response = requests.post(
        show_url,
        json={"model": model},
        headers=_api_headers("ollama", api_key_env),
        timeout=10,
    )
    if not response.ok:
        return None
    return _extract_context_window(response.json())


def _extract_context_window(data) -> Optional[int]:
    candidates: list[int] = []
    context_key_patterns = (
        "context_length",
        "context_window",
        "context_size",
        "context_tokens",
        "max_context_length",
        "max_context_tokens",
        "max_input_tokens",
        "max_position_embeddings",
        "max_sequence_length",
        "input_token_limit",
        "num_ctx",
        "n_ctx",
    )

    def visit(value) -> None:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                normalized_key = str(key).lower().replace("-", "_")
                if any(pattern in normalized_key for pattern in context_key_patterns):
                    parsed = _positive_int(nested_value)
                    if parsed:
                        candidates.append(parsed)
                visit(nested_value)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            for match in re.finditer(r"\b(?:num_ctx|n_ctx|context_length)\s+(\d+)\b", value):
                parsed = _positive_int(match.group(1))
                if parsed:
                    candidates.append(parsed)

    visit(data)
    plausible = [value for value in candidates if 1_024 <= value <= 10_000_000]
    return max(plausible) if plausible else None


def _positive_int(value) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _openai_compatible_base_url(chat_url: str) -> str:
    parsed = urlparse(chat_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[: -len("/chat/completions")]
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", "")).rstrip("/")


def _ollama_show_url(chat_url: str) -> str:
    parsed = urlparse(chat_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/api/chat"):
        path = path[: -len("/api/chat")] + "/api/show"
    else:
        path = "/api/show"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _api_headers(api_format: str, api_key_env: str) -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv(api_key_env) if api_key_env else None
    if not api_key and api_format == "nanogpt":
        api_key = os.getenv("NANOGPT_API_KEY")
    if not api_key and api_format in {"openai", "nanogpt"}:
        api_key = os.getenv("AI_PROXY_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


@lru_cache(maxsize=64)
def _token_encoder(model: str):
    if tiktoken is None:
        return None

    model_candidates = [model, _normalize_model_name(model), _strip_provider_prefix(model)]
    for candidate in model_candidates:
        if not candidate:
            continue
        try:
            return tiktoken.encoding_for_model(candidate)
        except KeyError:
            continue

    for encoding_name in ("o200k_base", "cl100k_base"):
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception:
            continue
    return None


def _strip_provider_prefix(model: str) -> str:
    if "/" not in model:
        return model
    return model.rsplit("/", 1)[-1]


def _normalize_model_name(model: str) -> str:
    return _strip_provider_prefix(model).strip().lower().replace(":", "-").replace("_", "-")
