"""Download papers, extract text with pypdf, and populate structured fields via Groq."""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import ssl
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

try:
    from pypdf import PdfReader
    _PYPDF_OK = True
except ImportError:
    _PYPDF_OK = False

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT = 30
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ENV_LOADED = False

_EXTRACTION_PROMPT = """\
You are an academic paper analysis agent. Given the text extracted from a research paper, \
identify and extract the following fields. Return ONLY a valid JSON object with exactly these keys:

- methods: list of strings describing research methods, techniques, architectures used
- datasets: list of strings naming datasets used for experiments
- metrics: list of strings naming evaluation metrics (e.g., accuracy, F1, AUC-ROC)
- reported_results: list of strings describing key quantitative results
- limitations: list of strings describing stated limitations of the work

Rules:
- Extract only what is explicitly stated in the paper text.
- If a field is not mentioned, return an empty list [].
- Each string should be concise (under 120 characters).
- Do NOT invent or infer values not present in the text.
- Output ONLY the raw JSON object. No markdown, no code fences, no explanation.

Example:
{"methods": ["Transformer encoder"], "datasets": ["MIMIC-III"], "metrics": ["AUC-ROC"], "reported_results": ["0.91 AUC"], "limitations": ["English only"]}
"""


def _load_env() -> None:
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


def _groq_config() -> tuple[str, str, float]:
    _load_env()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout = float(os.getenv("GROQ_TIMEOUT_SECONDS", DEFAULT_TIMEOUT))
    return api_key, model, timeout


def _fetch_pdf_bytes(url: str, timeout: float = 15.0) -> bytes | None:
    """Attempt to download a PDF from the given URL. Returns raw bytes or None."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    # Try to get a direct PDF link (some DOI URLs redirect to HTML landing pages)
    pdf_url = url
    if "doi.org" in url:
        # Try to guess an OA PDF location via Unpaywall-style pattern
        doi_part = re.sub(r"https?://doi\.org/", "", url)
        pdf_url = f"https://arxiv.org/pdf/{doi_part}" if "arxiv" in url.lower() else url
    try:
        req = Request(
            pdf_url,
            headers={
                "User-Agent": "ResearchPilot/0.1 (PDF fetcher; contact research@example.com)",
                "Accept": "application/pdf,*/*",
            },
        )
        with urlopen(req, timeout=timeout, context=TLS_CONTEXT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not pdf_url.endswith(".pdf"):
                return None
            data = resp.read(8 * 1024 * 1024)  # max 8 MB
        return data if data else None
    except Exception:
        return None


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Use pypdf to extract text from PDF bytes. Returns up to ~8000 chars."""
    if not _PYPDF_OK or not pdf_bytes:
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        char_count = 0
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
            char_count += len(page_text)
            if char_count >= 20_000:
                break
        full_text = "\n".join(pages_text)
        return full_text[:20_000]
    except Exception:
        return ""


def _extract_text_from_abstract(paper: dict[str, Any]) -> str:
    """Fall back to using the abstract + title when no PDF is available."""
    title = paper.get("title", "") or ""
    abstract = paper.get("abstract", "") or ""
    return f"Title: {title}\n\nAbstract: {abstract}"


def _call_groq(text: str, api_key: str, model: str, timeout: float) -> dict[str, Any] | None:
    """Call Groq chat API to extract structured fields from paper text."""
    if not api_key:
        return None
    # Truncate text to avoid token limits (roughly 12k chars ~ 3k tokens)
    truncated = text[:12_000]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": f"Paper text:\n\n{truncated}"},
        ],
        "temperature": 0.1,
        "max_tokens": 600,
    }
    req = Request(
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
    try:
        with urlopen(req, timeout=timeout, context=TLS_CONTEXT) as resp:
            result = json.load(resp)
        content = result["choices"][0]["message"]["content"]
        # Strip any markdown code fences the model may add
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return None


def _merge_extracted(paper: dict[str, Any], extracted: dict[str, Any] | None) -> dict[str, Any]:
    """Merge Groq-extracted fields into the paper record, keeping existing non-empty values."""
    if not extracted:
        return paper
    updated = dict(paper)
    for field in ("methods", "datasets", "metrics", "reported_results", "limitations"):
        existing = paper.get(field)
        # Only overwrite if the existing list is empty
        if not existing or not isinstance(existing, list):
            raw = extracted.get(field)
            if isinstance(raw, list):
                values = [str(v).strip() for v in raw if isinstance(v, str) and str(v).strip()]
                updated[field] = values
    return updated


async def enrich_paper(paper: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Download PDF, extract text, and use Groq to populate structured fields.

    Returns (enriched_paper, optional_warning).
    """
    api_key, model, timeout = _groq_config()
    if not api_key:
        return paper, "Groq API key not configured; structured field extraction skipped."

    # Step 1: Try to get PDF text
    pdf_bytes: bytes | None = None
    paper_url = paper.get("url", "") or ""
    paper_doi = paper.get("doi", "") or ""
    pdf_source_url = paper_doi if paper_doi else paper_url

    pdf_bytes = await asyncio.to_thread(_fetch_pdf_bytes, pdf_source_url)

    if pdf_bytes:
        text = await asyncio.to_thread(_extract_text_from_pdf, pdf_bytes)
    else:
        text = ""

    # Fall back to abstract if PDF extraction failed or yielded too little
    if len(text.strip()) < 200:
        text = _extract_text_from_abstract(paper)
        source = "abstract"
    else:
        source = "pdf"

    # Step 2: Extract structured fields via Groq
    extracted = await asyncio.to_thread(_call_groq, text, api_key, model, timeout)
    enriched = _merge_extracted(paper, extracted)

    warning: str | None = None
    if not extracted:
        warning = (
            f"Groq field extraction failed for '{paper.get('title', 'unknown')}'; "
            f"structured metadata unavailable."
        )
    elif source == "abstract":
        # Note but not a hard warning
        pass

    return enriched, warning


async def enrich_papers(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Enrich all papers concurrently with PDF extraction + Groq structured field extraction."""
    if not isinstance(papers, list) or not papers:
        return {
            "agent_name": "Paper Extractor",
            "status": "success",
            "summary": "No papers to enrich.",
            "items": papers or [],
            "warnings": [],
            "sources": [],
        }

    results = await asyncio.gather(*(enrich_paper(p) for p in papers))
    enriched_papers: list[dict[str, Any]] = []
    warnings: list[str] = []
    for enriched, warning in results:
        enriched_papers.append(enriched)
        if warning:
            warnings.append(warning)

    filled = sum(
        1 for p in enriched_papers
        if any(p.get(f) for f in ("methods", "datasets", "metrics", "reported_results"))
    )

    return {
        "agent_name": "Paper Extractor",
        "status": "success" if filled > 0 else "partial",
        "summary": (
            f"Extracted structured fields from {filled}/{len(enriched_papers)} papers "
            f"using Groq ({os.getenv('GROQ_MODEL', DEFAULT_MODEL)}) and pypdf."
        ),
        "items": enriched_papers,
        "warnings": warnings,
        "sources": ["Groq", "pypdf"],
    }
