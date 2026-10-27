"""Verify discovered paper metadata against OpenAlex records."""

from __future__ import annotations

import asyncio
import json
import re
import ssl
from collections.abc import Mapping
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import certifi

OPENALEX_API_URL = "https://api.openalex.org/works"
DEFAULT_TIMEOUT_SECONDS = 10
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


async def verify_papers(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Check each paper's bibliographic metadata against OpenAlex.

    This verifies metadata availability and agreement only. It does not verify
    the paper's scientific claims or results.
    """
    if not isinstance(papers, list):
        return _agent_output(
            "partial",
            "Paper input must be a list; no authenticity checks were performed.",
            warnings=["Input was not a list of paper records."],
        )

    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    sources: list[str] = []
    for index, paper in enumerate(papers):
        if not isinstance(paper, dict):
            warnings.append(
                f"Skipped malformed paper record at index {index}; expected a dictionary."
            )
            continue

        checked = dict(paper)
        try:
            match = await asyncio.to_thread(_lookup_openalex, checked)
        except (HTTPError, HTTPException, TimeoutError, URLError, OSError, json.JSONDecodeError) as exc:
            warning = f"Authenticity lookup failed for {_paper_label(checked)}: {_describe_error(exc)}"
            checked["authenticity_status"] = "unverified"
            checked["authenticity_reasons"] = [warning]
            warnings.append(warning)
        else:
            status, reasons = _assess_match(checked, match)
            checked["authenticity_status"] = status
            checked["authenticity_reasons"] = reasons

        items.append(checked)
        if "OpenAlex" not in sources:
            sources.append("OpenAlex")

    status = "success" if items and not warnings else "partial"
    if not papers:
        status = "success"
    return _agent_output(
        status,
        f"Checked bibliographic metadata for {len(items)} paper record(s) against OpenAlex.",
        items=items,
        warnings=warnings,
        sources=sources,
    )


async def check_authenticity(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Compatibility name for orchestration code using the agent's role name."""
    return await verify_papers(papers)


def _lookup_openalex(paper: Mapping[str, Any]) -> Mapping[str, Any] | None:
    doi = _text(paper.get("doi"))
    title = _text(paper.get("title"))
    if doi:
        query = f"{OPENALEX_API_URL}/https://doi.org/{quote(doi.removeprefix('https://doi.org/'))}"
    elif title:
        search_title = re.sub(r"[*?]+", " ", title).strip()
        query = f"{OPENALEX_API_URL}?{urlencode({'search': search_title, 'per-page': 5})}"
    else:
        return None

    request = Request(
        query,
        headers={"Accept": "application/json", "User-Agent": "ResearchPilot/0.1"},
    )
    with urlopen(
        request,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        context=TLS_CONTEXT,
    ) as response:
        payload = json.load(response)
    if doi:
        return payload if isinstance(payload, Mapping) else None
    results = payload.get("results", []) if isinstance(payload, Mapping) else []
    return results[0] if results and isinstance(results[0], Mapping) else None


def _assess_match(
    paper: Mapping[str, Any], match: Mapping[str, Any] | None
) -> tuple[str, list[str]]:
    if match is None:
        return "unverified", ["No matching bibliographic record was found in OpenAlex."]

    reasons = ["A matching bibliographic record was found in OpenAlex."]
    title = _text(paper.get("title"))
    matched_title = _text(match.get("title"))
    if title and matched_title and _normalize(title) != _normalize(matched_title):
        return "partially_verified", reasons + ["The matched title differs from the submitted title."]

    doi = _text(paper.get("doi"))
    matched_doi = _text(match.get("doi"))
    if doi and matched_doi and _normalize_doi(doi) != _normalize_doi(matched_doi):
        return "partially_verified", reasons + ["The matched DOI differs from the submitted DOI."]
    if not title and not doi:
        return "partially_verified", ["The submitted record has no title or DOI to verify."]
    return "verified", reasons


def _agent_output(
    status: str,
    summary: str,
    *,
    items: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": "search_authenticity",
        "status": status,
        "summary": summary,
        "items": items or [],
        "warnings": warnings or [],
        "sources": sources or [],
    }


def _paper_label(paper: Mapping[str, Any]) -> str:
    return _text(paper.get("paper_id")) or _text(paper.get("title")) or "paper"


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _normalize_doi(value: str) -> str:
    return _normalize(value).removeprefix("https://doi.org/").removeprefix("doi:")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _describe_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, TimeoutError):
        return "request timed out"
    if isinstance(error, URLError):
        return str(error.reason)
    return str(error) or error.__class__.__name__