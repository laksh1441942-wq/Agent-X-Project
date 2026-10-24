"""OpenAlex paper discovery and transparent relevance ranking."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPENALEX_API_URL = "https://api.openalex.org/works"
DEFAULT_TIMEOUT_SECONDS = 10
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
}


async def discover_papers(question: str, max_papers: int = 5) -> dict[str, Any]:
    """Search OpenAlex and return normalized, ranked candidate paper records."""
    validation_error = _validate_inputs(question, max_papers)
    if validation_error:
        return {
            "agent_name": "paper_discovery",
            "status": "error",
            "summary": validation_error,
            "items": [],
            "warnings": [validation_error],
            "sources": [],
        }

    try:
        response = await asyncio.to_thread(
            _request_openalex,
            question.strip(),
            min(max_papers, 100),
        )
    except (HTTPError, HTTPException, TimeoutError, URLError, OSError, json.JSONDecodeError) as exc:
        warning = f"OpenAlex search failed: {_describe_error(exc)}"
        return {
            "agent_name": "paper_discovery",
            "status": "error",
            "summary": "No papers were discovered because the OpenAlex request failed.",
            "items": [],
            "warnings": [warning],
            "sources": ["OpenAlex"],
        }

    raw_results = response.get("results", [])
    if not isinstance(raw_results, list):
        warning = "OpenAlex returned an invalid results payload."
        return {
            "agent_name": "paper_discovery",
            "status": "error",
            "summary": warning,
            "items": [],
            "warnings": [warning],
            "sources": ["OpenAlex"],
        }

    ranked = _rank_and_deduplicate(raw_results, question)
    warnings = []
    if len(ranked) < max_papers:
        warnings.append(
            f"OpenAlex returned {len(ranked)} usable paper(s); requested {max_papers}."
        )
    return {
        "agent_name": "paper_discovery",
        "status": "success" if ranked else "partial",
        "summary": (
            f"Found {len(ranked)} candidate paper(s) in OpenAlex. "
            "Ranking uses unique non-stopword overlap with title and abstract, "
            "then OpenAlex relevance score."
        ),
        "items": ranked[:max_papers],
        "warnings": warnings,
        "sources": ["OpenAlex"],
    }


def _validate_inputs(question: str, max_papers: int) -> str | None:
    if not isinstance(question, str) or not question.strip():
        return "A non-empty research question is required."
    if isinstance(max_papers, bool) or not isinstance(max_papers, int):
        return "max_papers must be an integer."
    if max_papers < 1:
        return "max_papers must be at least 1."
    return None


def _request_openalex(question: str, max_papers: int) -> dict[str, Any]:
    query = urlencode({"search": question, "per-page": max_papers})
    request = Request(
        f"{OPENALEX_API_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "ResearchPilot/0.1"},
    )
    with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _rank_and_deduplicate(
    raw_results: list[Any], question: str
) -> list[dict[str, Any]]:
    question_tokens = _keywords(question)
    candidates: dict[str, tuple[float, dict[str, Any]]] = {}
    for raw in raw_results:
        if not isinstance(raw, Mapping):
            continue
        paper = _normalize_paper(raw)
        if paper is None:
            continue
        searchable_text = f"{paper['title']} {paper['abstract']}"
        overlap = len(question_tokens & _keywords(searchable_text))
        relevance_score = _numeric_value(raw.get("relevance_score"))
        rank = overlap + relevance_score / 1000
        key = _deduplication_key(paper)
        existing = candidates.get(key)
        if existing is None or rank > existing[0]:
            candidates[key] = (rank, paper)
    return [
        paper
        for _, paper in sorted(
            candidates.values(),
            key=lambda item: (-item[0], item[1]["title"].lower()),
        )
    ]


def _normalize_paper(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    title = _text(raw.get("title"))
    if not title:
        return None
    authors = []
    for authorship in raw.get("authorships", []):
        if not isinstance(authorship, Mapping):
            continue
        author = authorship.get("author")
        if isinstance(author, Mapping) and _text(author.get("display_name")):
            authors.append(_text(author["display_name"]))

    primary_location = raw.get("primary_location")
    if not isinstance(primary_location, Mapping):
        primary_location = {}
    url = _first_text(
        primary_location.get("landing_page_url"),
        raw.get("doi"),
        raw.get("openalex_url"),
        raw.get("id"),
    )
    if not url:
        return None

    abstract = _reconstruct_abstract(raw.get("abstract_inverted_index"))
    return {
        "paper_id": _text(raw.get("id")) or url,
        "title": title,
        "authors": authors,
        "year": raw.get("publication_year") if isinstance(raw.get("publication_year"), int) else None,
        "abstract": abstract,
        "doi": _text(raw.get("doi")) or None,
        "url": url,
        "source": "OpenAlex",
        "authenticity_status": "unverified",
        "authenticity_reasons": [],
        "methods": [],
        "datasets": [],
        "metrics": [],
        "reported_results": [],
        "limitations": [],
        "missing_information": [],
    }


def _reconstruct_abstract(index: Any) -> str:
    if not isinstance(index, Mapping):
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        words.extend((position, word) for position in positions if isinstance(position, int))
    return " ".join(word for _, word in sorted(words))


def _deduplication_key(paper: Mapping[str, Any]) -> str:
    doi = _text(paper.get("doi"))
    if doi:
        return f"doi:{doi.lower().removeprefix('https://doi.org/')}"
    title = " ".join(_keywords(_text(paper.get("title"))))
    return f"title:{title}|year:{paper.get('year')}"


def _keywords(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(value.lower())
        if token not in _STOP_WORDS
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _numeric_value(value: Any) -> float:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _describe_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, (TimeoutError, TimeoutError)):
        return "request timed out"
    if isinstance(error, URLError):
        return str(error.reason)
    return str(error) or error.__class__.__name__
