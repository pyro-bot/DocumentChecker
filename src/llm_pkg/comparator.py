import requests
import json
import os
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .parser import parse_llm_response, create_error_response

try:
    from app.services.model_config import ModelsConfigError, load_models_config
except Exception:  # pragma: no cover - keeps llm_pkg usable outside the FastAPI app
    ModelsConfigError = Exception
    load_models_config = None


DEFAULT_LLM_API_URL = "http://localhost:11434/api/chat"
OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMSettings:
    model: str
    url: str
    api_format: str
    api_key_env: str


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{OPENAI_CHAT_COMPLETIONS_PATH}"


def _get_legacy_llm_api_url() -> str:
    api_url = os.getenv("LLM_API_URL")
    if api_url:
        return api_url

    base_url = os.getenv("LLM_API_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if base_url:
        return _chat_completions_url(base_url)

    return DEFAULT_LLM_API_URL


def _get_llm_api_format(url: str, configured: str = "") -> str:
    configured = (configured or os.getenv("LLM_API_FORMAT", "auto")).strip().lower()
    if configured in {"openai", "ollama", "nanogpt"}:
        return configured
    return "openai" if url.rstrip("/").endswith(OPENAI_CHAT_COMPLETIONS_PATH) else "ollama"


def _get_headers(api_format: str, api_key_env: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv(api_key_env) if api_key_env else None
    if not api_key and api_format == "nanogpt":
        api_key = os.getenv("NANOGPT_API_KEY")
    if not api_key and api_format in {"openai", "nanogpt"}:
        api_key = os.getenv("AI_PROXY_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _default_api_key_env(api_format: str) -> str:
    if api_format == "nanogpt":
        return "NANOGPT_API_KEY"
    if api_format == "openai":
        return "AI_PROXY_KEY"
    return ""


def _resolve_llm_settings(model: str) -> LLMSettings:
    if load_models_config is not None:
        try:
            config = load_models_config()
            model_config = config.get(model)
            if model_config is not None:
                endpoint = config.get_endpoint(model_config.endpoint_id) if model_config.endpoint_id else None
                api_url = model_config.api_url or (endpoint.url if endpoint else "")
                api_base_url = model_config.api_base_url or (endpoint.base_url if endpoint else "")
                api_format = model_config.api_format or (endpoint.api_format if endpoint else "")
                api_key_env = model_config.api_key_env or (endpoint.api_key_env if endpoint else "")

                if api_url or api_base_url:
                    url = api_url or _chat_completions_url(api_base_url)
                    return LLMSettings(
                        model=model_config.request_model,
                        url=url,
                        api_format=_get_llm_api_format(url, api_format),
                        api_key_env=api_key_env,
                    )
        except ModelsConfigError:
            raise
        except Exception:
            logger.exception("Unable to resolve model-specific LLM settings for model=%s", model)

    url = _get_legacy_llm_api_url()
    api_format = _get_llm_api_format(url)
    return LLMSettings(
        model=model,
        url=url,
        api_format=api_format,
        api_key_env=_default_api_key_env(api_format),
    )


def _extract_response_text(response_data: dict, api_format: str) -> str:
    if api_format in {"openai", "nanogpt"}:
        choices = response_data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "").strip()

    return response_data.get("message", {}).get("content", "").strip()


def _run_single_check(
    template: str,
    document: str,
    check_type: str,
    settings: LLMSettings
) -> dict:
    user_prompt = build_user_prompt(template, document, check_type=check_type)
    
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    if settings.api_format != "nanogpt":
        payload["prompt_cache_retention"] = "24h"
    
    try:
        response = requests.post(
            settings.url,
            json=payload,
            headers=_get_headers(settings.api_format, settings.api_key_env),
            timeout=1800,
        )
        if not response.ok:
            return {
                "check_type": check_type,
                "error": f"HTTP {response.status_code}: {response.text[:500]}",
                "data": None
            }
        
        response_data = response.json()
        response_text = _extract_response_text(response_data, settings.api_format)
        
        if not response_text:
            return {"check_type": check_type, "error": "Пустой ответ", "data": None}
        
        parsed = parse_llm_response(response_text)
        return {"check_type": check_type, "error": None, "data": parsed}
        
    except Exception as e:
        logger.exception(
            "LLM check failed: check_type=%s model=%s api_format=%s url=%s",
            check_type,
            settings.model,
            settings.api_format,
            settings.url,
        )
        return {"check_type": check_type, "error": str(e), "data": None}


def _merge_results(structure: dict, content: dict, formatting: dict) -> dict:
    all_errors = []
    scores = {"structure": 100, "content": 100, "formatting": 100}
    summaries = []
    
    for result in [structure, content, formatting]:
        check_type = result["check_type"]
        
        if result["error"]:
            all_errors.append({
                "section": "Общий документ",
                "error_type": "structural" if check_type == "structure" else ("content" if check_type == "content" else "formatting"),
                "description": f"Ошибка проверки {check_type}: {result['error']}",
                "severity": "high"
            })
            scores[check_type] = 50
            summaries.append(f"{check_type}: ошибка запроса")
        elif result["data"]:
            data = result["data"]
            if isinstance(data, dict) and "errors" in data:
                all_errors.extend(data["errors"])
                scores[check_type] = data.get("compliance_score", 100)
                summaries.append(f"{check_type}: {data.get('summary', 'OK')}")
            else:
                scores[check_type] = 0
                summaries.append(f"{check_type}: некорректный формат ответа")
        else:
            scores[check_type] = 0
            summaries.append(f"{check_type}: нет данных")
    
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_errors.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))
    
    fmt_summary = next((s for s in summaries if "formatting:" in s.lower()), "")
    if "не проверено" in fmt_summary.lower() or "нет данных" in fmt_summary.lower():
        final_score = round(scores["structure"] * 0.5 + scores["content"] * 0.5)
    else:
        final_score = round(
            scores["structure"] * 0.4 + 
            scores["content"] * 0.4 + 
            scores["formatting"] * 0.2
        )
    
    return {
        "errors": all_errors,
        "compliance_score": final_score,
        "summary": " | ".join(summaries)
    }


def compare_documents(template_content, document_content, model="gpt-oss:120b-cloud", parallel: bool = True):
    settings = _resolve_llm_settings(model)
    check_types = ["structure", "content", "formatting"]
    
    if parallel:
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_check = {
                executor.submit(
                    _run_single_check,
                    template_content,
                    document_content,
                    ct,
                    settings
                ): ct
                for ct in check_types
            }
            for future in as_completed(future_to_check):
                result = future.result()
                results[result["check_type"]] = result
    else:
        results = {}
        for ct in check_types:
            results[ct] = _run_single_check(template_content, document_content, ct, settings)
    
    return _merge_results(
        structure=results.get("structure", {"check_type": "structure", "error": "Не выполнено", "data": None}),
        content=results.get("content", {"check_type": "content", "error": "Не выполнено", "data": None}),
        formatting=results.get("formatting", {"check_type": "formatting", "error": "Не выполнено", "data": None})
    )
