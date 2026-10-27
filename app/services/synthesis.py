"""Groq-backed synthesis over evidence already collected by the agents."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import ssl

import certifi

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 30
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ENV_LOADED = False


async def synthesize_report(
    question: str,
    papers: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    missing_information: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    """Use Groq to summarize supplied evidence without adding sources."""
    _load_env_file()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if not api_key:
        return _output(
            "error",
            "Groq API key not configured; synthesis unavailable.",
            warnings=["GROQ_API_KEY not set in .env file."],
        )
    try:
        payload = _request_groq(
            api_key,
            model,
            _build_messages(question, papers, comparison, missing_information, warnings),
        )
        content = payload["choices"][0]["message"]["content"]
        result = _parse_result(content)
    except (HTTPError, URLError, TimeoutError, OSError, KeyError, IndexError, TypeError, ValueError) as error:
        return _output(
            "error",
            "Groq synthesis failed; the retrieved evidence remains available.",
            warnings=[f"Groq synthesis failed: {_describe_error(error)}"],
        )

    return _output(
        "success",
        f"Groq ({model}) synthesized only the evidence returned by the research agents.",
        items=[result],
        sources=[f"Groq:{model}"],
    )


def _request_groq(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    timeout = float(os.getenv("GROQ_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1500,
    }
    request = Request(
        GROQ_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "python-groq/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout, context=TLS_CONTEXT) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("Groq returned a non-object response.")
    return result


def _build_messages(
    question: str,
    papers: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    missing_information: list[dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, str]]:
    evidence = {
        "research_question": question,
        "papers": [_paper_evidence(paper) for paper in papers],
        "comparison": comparison,
        "missing_information": missing_information,
        "warnings": warnings,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are the synthesis agent for an academic research assistant. "
                "Use only the supplied JSON evidence. Never invent papers, quotes, "
                "numbers, confidence, citations, or conclusions. If evidence is "
                "insufficient, return an empty array or say it is uncertain. "
                "Candidate gaps describe only underexplored areas in this retrieved "
                "set and do not establish novelty. "
                "Return valid JSON with exactly these keys: "
                "summary (string, 2-4 sentences), "
                "key_findings (array of objects, each with: finding, explanation, paper_ids), "
                "candidate_gaps (array of objects, each with: title, explanation, uncertainty). "
                "Keep key_findings to 3-5 items and candidate_gaps to 2-4 items."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(evidence, ensure_ascii=True),
        },
    ]


def _paper_evidence(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        key: paper.get(key)
        for key in (
            "paper_id",
            "title",
            "authors",
            "year",
            "abstract",
            "doi",
            "authenticity_status",
            "methods",
            "datasets",
            "metrics",
            "reported_results",
            "limitations",
        )
    }


def _parse_result(content: Any) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ValueError("Groq returned no text content.")
    cleaned = content.strip()
    # Strip markdown code fences if the model adds them
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Groq synthesis was not a JSON object.")
    return {
        "summary": parsed.get("summary") if isinstance(parsed.get("summary"), str) else "",
        "key_findings": _list_of_dicts(parsed.get("key_findings")),
        "candidate_gaps": _list_of_dicts(parsed.get("candidate_gaps")),
    }


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _output(
    status: str,
    summary: str,
    *,
    items: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": "Groq Synthesis Agent",
        "status": status,
        "summary": summary,
        "items": items or [],
        "warnings": warnings or [],
        "sources": sources or [],
    }


def _load_env_file() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    _ENV_LOADED = True


def _describe_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    if isinstance(error, URLError):
        return str(error.reason)
    return str(error) or error.__class__.__name__