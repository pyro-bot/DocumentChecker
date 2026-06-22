import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote

import requests

from llm_pkg.comparator import _extract_response_text, _get_headers, _resolve_llm_settings
from llm_pkg.parser import parse_llm_response

logger = logging.getLogger(__name__)

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ISBN_RE = re.compile(
    r"\b(?:ISBN(?:-1[03])?:?\s*)?(97[89][-\s]?)?(?:\d[-\s]?){9}[\dX]\b",
    re.IGNORECASE,
)
URL_RE = re.compile(r'https?://[^\s<>\]\)"\']+', re.IGNORECASE)

FREE_SOURCES = ("crossref", "openalex", "semantic_scholar", "google_books", "open_library")
DEFAULT_TIMEOUT = (5, 14)

EXTRACTION_SYSTEM_PROMPT = """
You extract and normalize bibliography records from academic documents.
Return strict JSON only. Do not verify sources and do not invent facts.
""".strip()

EXTRACTION_USER_PROMPT = """
Find the bibliography/references section in the document and extract references.

Return this JSON shape:
{{
  "references": [
    {{
      "raw": "original reference text",
      "title": "work title, if visible",
      "authors": ["Author 1", "Author 2"],
      "year": 2024,
      "container": "journal, conference, collection or publisher",
      "publisher": "publisher, if visible",
      "reference_type": "article|book|chapter|thesis|web|unknown",
      "doi": "10....",
      "isbn": "978...",
      "url": "https://...",
      "search_queries": [
        "short exact title and first author query",
        "bibliographic query suitable for catalogs"
      ],
      "bibliographic_record": "normalized bibliography record in the style of the source text"
    }}
  ]
}}

Rules:
- Keep raw text exactly enough to identify the reference.
- For electronic resources, always preserve the URL if it is present.
- Fill title, authors, year, container, publisher, type, DOI, ISBN, URL, search queries,
  and normalized bibliographic record from the visible record text.
- Ignore LaTeX commands, LaTeX comments, document preamble, and converter formatting metadata.
- If a field is absent, use an empty string, empty list, null, or "unknown".
- Do not create DOI, ISBN, URLs, titles, years, authors, or publishers that are not present.
- Search queries may reorder visible parts but must not add new facts.
- Prefer references from sections named References, Bibliography, Works Cited,
  Список литературы, Литература, Источники, Библиографический список.
- Limit the result to {max_references} records.

Document:
{document}
""".strip()

LATEX_COMMAND_LINE_RE = re.compile(
    r"^\s*\\(?:documentclass|usepackage|geometry|setmainfont|begin|end|title|author|date|maketitle|tableofcontents)\b",
    re.IGNORECASE,
)
LATEX_SECTION_RE = re.compile(r"\\(?:part|chapter|section|subsection|subsubsection)\*?\{([^{}]*)\}")
LATEX_INLINE_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?")
NOISE_REFERENCE_RE = re.compile(
    r"(?:"
    r"\\usepackage|\\documentclass|\\begin\{|\\end\{|"
    r"формат\s+абзаца|источник\s+(?:шрифта|размера|жирного|курсива|подчеркивания|выравнивания)|"
    r"размер\s+шрифта|межстрочный\s+интервал|правило\s+межстрочного|"
    r"ручной\s+разрыв\s+страницы|разрыв\s+страницы\s+word"
    r")",
    re.IGNORECASE,
)


def _request_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": os.getenv("BIBLIOGRAPHY_USER_AGENT", "DocumentChecker/1.0"),
    }


def _normalize_text(value: str) -> str:
    value = re.sub(r"https?://\S+", " ", value or "", flags=re.IGNORECASE)
    value = re.sub(r"doi\s*:?\s*10\.\S+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"[^\w\s]+", " ", value.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _strip_latex_noise(document_content: str) -> str:
    cleaned_lines: list[str] = []
    for line in (document_content or "").splitlines():
        if LATEX_COMMAND_LINE_RE.search(line):
            continue

        line = re.sub(r"(?<!\\)%.*$", "", line)
        line = LATEX_SECTION_RE.sub(r"\1", line)
        line = LATEX_INLINE_COMMAND_RE.sub(lambda match: match.group(1) or " ", line)
        line = line.replace(r"\&", "&").replace(r"\%", "%")
        line = re.sub(r"[{}]", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def _is_noise_reference(reference: dict[str, Any]) -> bool:
    raw = str(reference.get("raw") or reference.get("title") or "").strip()
    if not raw:
        return True

    if raw.startswith(("\\", "%")):
        return True

    if NOISE_REFERENCE_RE.search(raw):
        return True

    normalized = _normalize_text(raw)
    meaningful_tokens = [token for token in normalized.split() if len(token) > 2]
    return len(meaningful_tokens) < 3


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^0-9A-Z]+", "", value or "", flags=re.IGNORECASE).upper()


def _normalize_doi(value: str) -> str:
    value = (value or "").strip().rstrip(".,;")
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


def _first(value: Any, default: str = "") -> str:
    if isinstance(value, list) and value:
        return str(value[0] or "")
    if value is None:
        return default
    return str(value)


def _as_year(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 3000 else None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def _title_score(left: str, right: str) -> float:
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    containment = len(left_tokens & right_tokens) / max(min(len(left_tokens), len(right_tokens)), 1)
    return max(ratio, overlap, containment)


def _author_score(expected: list[str], candidate: list[str]) -> float:
    if not expected or not candidate:
        return 0.0
    expected_norm = {_normalize_text(item).split()[-1] for item in expected if _normalize_text(item)}
    candidate_norm = {_normalize_text(item).split()[-1] for item in candidate if _normalize_text(item)}
    if not expected_norm or not candidate_norm:
        return 0.0
    return len(expected_norm & candidate_norm) / max(len(expected_norm), 1)


def _confidence(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    ref_ids = reference.get("identifiers", {})
    cand_ids = candidate.get("identifiers", {})
    if ref_ids.get("doi") and cand_ids.get("doi") and _normalize_doi(ref_ids["doi"]) == _normalize_doi(cand_ids["doi"]):
        return 1.0
    if ref_ids.get("isbn") and cand_ids.get("isbn"):
        if _normalize_identifier(ref_ids["isbn"]) == _normalize_identifier(cand_ids["isbn"]):
            return 1.0

    score = _title_score(reference.get("title") or reference.get("raw", ""), candidate.get("title", "")) * 0.68
    score += _author_score(reference.get("authors", []), candidate.get("authors", [])) * 0.18
    if reference.get("year") and candidate.get("year"):
        score += (0.14 if abs(reference["year"] - candidate["year"]) <= 1 else -0.08)
    return max(0.0, min(1.0, score))


def _extract_identifiers(raw: str) -> dict[str, str]:
    identifiers: dict[str, str] = {}
    doi = DOI_RE.search(raw or "")
    if doi:
        identifiers["doi"] = _normalize_doi(doi.group(0))

    isbn = ISBN_RE.search(raw or "")
    if isbn:
        raw_isbn = re.sub(r"^ISBN(?:-1[03])?:?\s*", "", isbn.group(0), flags=re.IGNORECASE)
        normalized = _normalize_identifier(raw_isbn)
        if len(normalized) in {10, 13}:
            identifiers["isbn"] = normalized
    return identifiers


def _clean_url(value: str) -> str:
    return (value or "").strip().rstrip(".,;:)]}>")


def _extract_url(raw: str) -> str:
    match = URL_RE.search(raw or "")
    return _clean_url(match.group(0)) if match else ""


def _as_queries(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []

    queries: list[str] = []
    seen: set[str] = set()
    for item in value:
        query = re.sub(r"\s+", " ", str(item or "")).strip()
        key = query.lower()
        if query and key not in seen:
            seen.add(key)
            queries.append(query[:450])
    return queries[:4]


def _reference_queries(reference: dict[str, Any]) -> list[str]:
    queries = _as_queries(reference.get("search_queries"))
    parts = [
        reference.get("title", ""),
        " ".join(reference.get("authors", [])[:2]),
        str(reference.get("year") or ""),
        reference.get("container", ""),
        reference.get("publisher", ""),
    ]
    structured = " ".join(part for part in parts if part).strip()
    raw = reference.get("bibliographic_record") or reference.get("raw", "")
    queries.extend(_as_queries([structured, raw]))

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = _normalize_text(query)
        if key and key not in seen:
            seen.add(key)
            deduped.append(query[:450])
    return deduped[:4]


def _reference_query(reference: dict[str, Any]) -> str:
    parts = [
        reference.get("title", ""),
        " ".join(reference.get("authors", [])[:2]),
        str(reference.get("year") or ""),
        reference.get("container", ""),
        reference.get("publisher", ""),
        reference.get("bibliographic_record", ""),
        reference.get("raw", ""),
    ]
    return " ".join(part for part in parts if part).strip()[:450]


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for candidate in candidates:
        ids = candidate.get("identifiers", {})
        key = (
            candidate.get("source", ""),
            _normalize_doi(ids.get("doi", "")),
            _normalize_identifier(ids.get("isbn", "")),
            _normalize_text(candidate.get("title", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _candidate(
    source: str,
    title: str = "",
    authors: list[str] | None = None,
    year: int | None = None,
    container: str = "",
    identifiers: dict[str, str] | None = None,
    url: str = "",
) -> dict[str, Any]:
    return {
        "source": source,
        "title": title or "",
        "authors": authors or [],
        "year": year,
        "container": container or "",
        "identifiers": {key: value for key, value in (identifiers or {}).items() if value},
        "url": url or "",
        "confidence": 0.0,
    }


class BibliographyCheckerService:
    @staticmethod
    def check(document_content: str, model: str = "openai/gpt-5-nano", max_references: int = 30) -> dict:
        try:
            warnings: list[str] = []
            searchable_content = _strip_latex_noise(document_content)
            references = BibliographyCheckerService._extract_references(
                searchable_content,
                model,
                max_references,
                warnings,
            )
            if not references:
                return {
                    "success": True,
                    "data": {
                        "model": model,
                        "checked_count": 0,
                        "summary": "Библиографические записи не найдены.",
                        "warnings": warnings,
                        "references": [],
                    },
                    "error": None,
                }

            checked = [
                BibliographyCheckerService._check_reference(index, reference)
                for index, reference in enumerate(references[:max_references], start=1)
            ]
            status_counts = {status: 0 for status in ("confirmed", "probable", "suspicious", "not_found", "unparsed")}
            for item in checked:
                status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

            warnings.append(
                "Статусы «не найдено» и «сомнительно» означают, что открытые каталоги не подтвердили запись; "
                "это повод для ручной проверки, а не доказательство выдуманного источника."
            )
            summary = (
                f"Проверено записей: {len(checked)}. "
                f"Подтверждено: {status_counts['confirmed']}, похоже найдено: {status_counts['probable']}, "
                f"сомнительно: {status_counts['suspicious']}, не найдено: {status_counts['not_found']}, "
                f"не разобрано: {status_counts['unparsed']}."
            )
            return {
                "success": True,
                "data": {
                    "model": model,
                    "checked_count": len(checked),
                    "summary": summary,
                    "warnings": warnings,
                    "references": checked,
                },
                "error": None,
            }
        except Exception as exc:
            logger.exception("Bibliography check failed")
            return {"success": False, "data": None, "error": str(exc)}

    @staticmethod
    def _extract_references(
        document_content: str,
        model: str,
        max_references: int,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        try:
            settings = _resolve_llm_settings(model)
            payload = {
                "model": settings.model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": EXTRACTION_USER_PROMPT.format(
                            document=document_content[:120000],
                            max_references=max_references,
                        ),
                    },
                ],
                "stream": False,
                "temperature": 0,
            }
            response = requests.post(
                settings.url,
                json=payload,
                headers=_get_headers(settings.api_format, settings.api_key_env),
                timeout=300,
            )
            if response.ok:
                response_text = _extract_response_text(response.json(), settings.api_format)
                parsed = parse_llm_response(response_text)
                references = parsed.get("references", []) if isinstance(parsed, dict) else []
                normalized = BibliographyCheckerService._normalize_references(references)
                if normalized:
                    return normalized[:max_references]

            warnings.append("AI-разбор не вернул записей, использован резервный парсер.")
            if not response.ok:
                logger.warning("Bibliography extraction HTTP %s: %s", response.status_code, response.text[:500])
        except Exception:
            logger.exception("Bibliography LLM extraction failed; falling back to regex parser")
            warnings.append("AI-разбор завершился ошибкой, использован резервный парсер.")

        return BibliographyCheckerService._fallback_extract(document_content)[:max_references]

    @staticmethod
    def _normalize_references(items: list[Any]) -> list[dict[str, Any]]:
        references: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            raw = str(item.get("raw") or "").strip()
            title = str(item.get("title") or "").strip()
            if not raw and not title:
                continue

            identifiers = _extract_identifiers(raw)
            if item.get("doi"):
                identifiers["doi"] = _normalize_doi(str(item["doi"]))
            if item.get("isbn"):
                isbn = _normalize_identifier(str(item["isbn"]))
                if isbn:
                    identifiers["isbn"] = isbn

            url = _extract_url(" ".join(str(part or "") for part in (raw, item.get("url"), item.get("link"))))
            authors = item.get("authors") or []
            if not isinstance(authors, list):
                authors = [str(authors)]
            publisher = str(item.get("publisher") or "").strip()
            container = str(item.get("container") or item.get("journal") or item.get("book_title") or publisher).strip()

            references.append(
                {
                    "raw": raw or title,
                    "title": title,
                    "authors": [str(author).strip() for author in authors if str(author).strip()],
                    "year": _as_year(item.get("year")),
                    "container": container,
                    "publisher": publisher,
                    "url": url,
                    "search_queries": _as_queries(item.get("search_queries") or item.get("queries")),
                    "bibliographic_record": str(item.get("bibliographic_record") or item.get("formatted") or raw or title).strip(),
                    "reference_type": str(item.get("reference_type") or item.get("type") or "unknown").strip() or "unknown",
                    "identifiers": identifiers,
                }
            )
        return [reference for reference in references if not _is_noise_reference(reference)]

    @staticmethod
    def _fallback_extract(document_content: str) -> list[dict[str, Any]]:
        pattern = re.compile(
            r"(?:список\s+литературы|библиографический\s+список|литература|источники|references|bibliography)",
            re.IGNORECASE,
        )
        match = pattern.search(document_content or "")
        section = document_content[match.start() :] if match else document_content
        section = section[:50000]
        chunks = re.split(r"\n\s*(?:\[\d+\]|\d+[.)])\s+", "\n" + section)
        if len(chunks) <= 2:
            chunks = [line for line in section.splitlines() if len(line.strip()) > 25]

        references = []
        for chunk in chunks:
            raw = re.sub(r"\s+", " ", chunk).strip(" -\t")
            if len(raw) < 25:
                continue
            year = _as_year(raw)
            references.append(
                {
                    "raw": raw,
                    "title": "",
                    "authors": [],
                    "year": year,
                    "container": "",
                    "publisher": "",
                    "url": _extract_url(raw),
                    "search_queries": [],
                    "bibliographic_record": raw,
                    "reference_type": "unknown",
                    "identifiers": _extract_identifiers(raw),
                }
            )
        return [reference for reference in references if not _is_noise_reference(reference)]

    @staticmethod
    def _check_reference(index: int, reference: dict[str, Any]) -> dict[str, Any]:
        if not reference.get("raw") and not reference.get("title"):
            return BibliographyCheckerService._result(index, reference, "unparsed", 0.0, 0.75, "Запись не удалось разобрать.", [])

        candidates: list[dict[str, Any]] = []
        if reference.get("url"):
            candidates.append(
                _candidate(
                    "url_in_record",
                    title=reference.get("title") or reference.get("bibliographic_record") or reference.get("raw", ""),
                    authors=reference.get("authors", []),
                    year=reference.get("year"),
                    container=reference.get("container", ""),
                    url=reference.get("url", ""),
                )
            )

        fetchers = (
            BibliographyCheckerService._crossref_candidates,
            BibliographyCheckerService._openalex_candidates,
            BibliographyCheckerService._semantic_scholar_candidates,
            BibliographyCheckerService._google_books_candidates,
            BibliographyCheckerService._open_library_candidates,
        )
        with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
            future_to_fetcher = {executor.submit(fetcher, reference): fetcher for fetcher in fetchers}
            for future in as_completed(future_to_fetcher):
                fetcher = future_to_fetcher[future]
                try:
                    candidates.extend(future.result())
                except Exception:
                    logger.exception("Bibliography source lookup failed: %s", fetcher.__name__)

        candidates = _dedupe_candidates(candidates)
        for candidate in candidates:
            confidence = _confidence(reference, candidate)
            if candidate.get("source") == "url_in_record":
                confidence = max(confidence, 0.64)
            candidate["confidence"] = round(confidence, 3)
        candidates.sort(key=lambda item: item["confidence"], reverse=True)
        candidates = candidates[:8]

        best = candidates[0]["confidence"] if candidates else 0.0
        strong_sources = len({candidate["source"] for candidate in candidates if candidate["confidence"] >= 0.62})

        if not candidates:
            status, suspicion, reason = "not_found", 0.88, "В открытых каталогах не найдено похожей записи."
        elif best >= 0.92 or BibliographyCheckerService._has_identifier_match(reference, candidates):
            status, suspicion, reason = "confirmed", 0.05, "Найдено совпадение по идентификатору или очень близким метаданным."
        elif best >= 0.62 or strong_sources >= 2:
            status, suspicion, reason = "probable", 0.22, "Найдено похожее совпадение по метаданным; идентификаторы отсутствуют или не дают точного подтверждения."
        else:
            status, suspicion, reason = "suspicious", 0.66, "Найдены только слабые или противоречивые совпадения."

        return BibliographyCheckerService._result(index, reference, status, best, suspicion, reason, candidates)

    @staticmethod
    def _result(
        index: int,
        reference: dict[str, Any],
        status: str,
        confidence: float,
        suspicion_score: float,
        reason: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "index": index,
            "raw": reference.get("raw", ""),
            "title": reference.get("title", ""),
            "authors": reference.get("authors", []),
            "year": reference.get("year"),
            "container": reference.get("container", ""),
            "publisher": reference.get("publisher", ""),
            "url": reference.get("url", ""),
            "search_queries": reference.get("search_queries", []),
            "bibliographic_record": reference.get("bibliographic_record", ""),
            "reference_type": reference.get("reference_type", "unknown"),
            "identifiers": reference.get("identifiers", {}),
            "status": status,
            "confidence": round(confidence, 3),
            "suspicion_score": round(suspicion_score, 3),
            "reason": reason,
            "candidates": candidates,
        }

    @staticmethod
    def _has_identifier_match(reference: dict[str, Any], candidates: list[dict[str, Any]]) -> bool:
        ref_ids = reference.get("identifiers", {})
        for candidate in candidates:
            cand_ids = candidate.get("identifiers", {})
            if ref_ids.get("doi") and cand_ids.get("doi") and _normalize_doi(ref_ids["doi"]) == _normalize_doi(cand_ids["doi"]):
                return True
            if ref_ids.get("isbn") and cand_ids.get("isbn"):
                if _normalize_identifier(ref_ids["isbn"]) == _normalize_identifier(cand_ids["isbn"]):
                    return True
        return False

    @staticmethod
    def _crossref_candidates(reference: dict[str, Any]) -> list[dict[str, Any]]:
        doi = reference.get("identifiers", {}).get("doi")
        if doi:
            url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
            data = requests.get(url, headers=_request_headers(), timeout=DEFAULT_TIMEOUT).json()
            item = data.get("message", {})
            return [BibliographyCheckerService._crossref_candidate(item)] if item else []

        for query in _reference_queries(reference):
            data = requests.get(
                "https://api.crossref.org/works",
                params={"query.bibliographic": query, "rows": 3},
                headers=_request_headers(),
                timeout=DEFAULT_TIMEOUT,
            ).json()
            items = data.get("message", {}).get("items", [])
            if items:
                return [BibliographyCheckerService._crossref_candidate(item) for item in items]
        return []

    @staticmethod
    def _crossref_candidate(item: dict[str, Any]) -> dict[str, Any]:
        authors = [
            " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
            for author in item.get("author", [])
        ]
        issued = item.get("issued", {}).get("date-parts", [[]])
        year = issued[0][0] if issued and issued[0] else None
        return _candidate(
            "crossref",
            title=_first(item.get("title")),
            authors=[author for author in authors if author],
            year=_as_year(year),
            container=_first(item.get("container-title")) or _first(item.get("publisher")),
            identifiers={"doi": _normalize_doi(item.get("DOI", ""))},
            url=item.get("URL", ""),
        )

    @staticmethod
    def _openalex_candidates(reference: dict[str, Any]) -> list[dict[str, Any]]:
        doi = reference.get("identifiers", {}).get("doi")
        params = {"per-page": 3}
        if doi:
            params["filter"] = f"doi:{doi}"
        else:
            queries = _reference_queries(reference)
            if not queries:
                return []
            params["search"] = queries[0]
        mailto = os.getenv("OPENALEX_MAILTO")
        if mailto:
            params["mailto"] = mailto
        data = requests.get(
            "https://api.openalex.org/works",
            params=params,
            headers=_request_headers(),
            timeout=DEFAULT_TIMEOUT,
        ).json()
        return [BibliographyCheckerService._openalex_candidate(item) for item in data.get("results", [])]

    @staticmethod
    def _openalex_candidate(item: dict[str, Any]) -> dict[str, Any]:
        authorships = item.get("authorships", [])
        authors = [
            author.get("author", {}).get("display_name", "")
            for author in authorships
            if author.get("author", {}).get("display_name")
        ]
        source = item.get("primary_location", {}).get("source") or {}
        return _candidate(
            "openalex",
            title=item.get("title", ""),
            authors=authors,
            year=_as_year(item.get("publication_year")),
            container=source.get("display_name", ""),
            identifiers={"doi": _normalize_doi(item.get("doi", ""))},
            url=item.get("doi") or item.get("id", ""),
        )

    @staticmethod
    def _semantic_scholar_candidates(reference: dict[str, Any]) -> list[dict[str, Any]]:
        fields = "title,year,authors,venue,externalIds,url"
        doi = reference.get("identifiers", {}).get("doi")
        if doi:
            response = requests.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi, safe='')}",
                params={"fields": fields},
                headers=_request_headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            if response.status_code == 404:
                return []
            item = response.json()
            return [BibliographyCheckerService._semantic_scholar_candidate(item)] if item else []

        for query in _reference_queries(reference):
            data = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": 3, "fields": fields},
                headers=_request_headers(),
                timeout=DEFAULT_TIMEOUT,
            ).json()
            items = data.get("data", [])
            if items:
                return [BibliographyCheckerService._semantic_scholar_candidate(item) for item in items]
        return []

    @staticmethod
    def _semantic_scholar_candidate(item: dict[str, Any]) -> dict[str, Any]:
        external_ids = item.get("externalIds") or {}
        return _candidate(
            "semantic_scholar",
            title=item.get("title", ""),
            authors=[author.get("name", "") for author in item.get("authors", []) if author.get("name")],
            year=_as_year(item.get("year")),
            container=item.get("venue", ""),
            identifiers={"doi": _normalize_doi(external_ids.get("DOI", ""))},
            url=item.get("url", ""),
        )

    @staticmethod
    def _google_books_candidates(reference: dict[str, Any]) -> list[dict[str, Any]]:
        isbn = reference.get("identifiers", {}).get("isbn")
        if isbn:
            queries = [f"isbn:{isbn}"]
        else:
            title = reference.get("title") or reference.get("raw", "")
            authors = " ".join(reference.get("authors", [])[:1])
            queries = [" ".join(part for part in (f'intitle:"{title[:120]}"', authors) if part)]
            queries.extend(_reference_queries(reference))
        queries = [query for query in queries if query]
        if not queries:
            return []
        for query in queries[:4]:
            data = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": query, "maxResults": 3},
                headers=_request_headers(),
                timeout=DEFAULT_TIMEOUT,
            ).json()
            items = data.get("items", [])
            if items:
                return [BibliographyCheckerService._google_books_candidate(item) for item in items]
        return []

    @staticmethod
    def _google_books_candidate(item: dict[str, Any]) -> dict[str, Any]:
        volume = item.get("volumeInfo", {})
        identifiers = {}
        for ident in volume.get("industryIdentifiers", []):
            if ident.get("type") in {"ISBN_10", "ISBN_13"} and ident.get("identifier"):
                identifiers["isbn"] = _normalize_identifier(ident["identifier"])
                break
        return _candidate(
            "google_books",
            title=volume.get("title", ""),
            authors=volume.get("authors", []) or [],
            year=_as_year(volume.get("publishedDate")),
            container=volume.get("publisher", ""),
            identifiers=identifiers,
            url=volume.get("infoLink", ""),
        )

    @staticmethod
    def _open_library_candidates(reference: dict[str, Any]) -> list[dict[str, Any]]:
        isbn = reference.get("identifiers", {}).get("isbn")
        if isbn:
            response = requests.get(
                f"https://openlibrary.org/isbn/{quote(isbn, safe='')}.json",
                headers=_request_headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            if response.status_code == 404:
                return []
            item = response.json()
            return [BibliographyCheckerService._open_library_candidate(item, isbn=isbn)]

        queries = _reference_queries(reference)
        title = reference.get("title") or (queries[0] if queries else reference.get("raw", ""))
        if not title:
            return []
        data = requests.get(
            "https://openlibrary.org/search.json",
            params={
                "q": title[:220],
                "title": (reference.get("title") or "")[:180],
                "author": " ".join(reference.get("authors", [])[:1]),
                "limit": 3,
            },
            headers=_request_headers(),
            timeout=DEFAULT_TIMEOUT,
        ).json()
        return [BibliographyCheckerService._open_library_candidate(item) for item in data.get("docs", [])]

    @staticmethod
    def _open_library_candidate(item: dict[str, Any], isbn: str = "") -> dict[str, Any]:
        identifiers = {"isbn": isbn}
        if not isbn:
            isbn_values = item.get("isbn") or []
            if isbn_values:
                identifiers["isbn"] = _normalize_identifier(isbn_values[0])
        title = item.get("title", "")
        authors = item.get("author_name") or []
        year = item.get("first_publish_year") or item.get("publish_date")
        publishers = item.get("publisher") or []
        return _candidate(
            "open_library",
            title=title,
            authors=authors,
            year=_as_year(year),
            container=_first(publishers),
            identifiers=identifiers,
            url=f"https://openlibrary.org{item.get('key', '')}" if item.get("key") else "",
        )
