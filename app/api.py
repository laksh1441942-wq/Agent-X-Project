"""Small standard-library HTTP API for the ResearchPilot prototype."""

from __future__ import annotations

import asyncio
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from app.services.critic import compare_papers
from app.services.paper_discovery import discover_papers
from app.services.paper_extractor import enrich_papers
from app.services.reasoning import analyze_missing_information
from app.services.search_authenticity import verify_papers
from app.services.synthesis import synthesize_report

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8010


def _cors_origin() -> str:
    """Return the configured browser origin for local or hosted deployments."""
    return os.environ.get("RESEARCHPILOT_CORS_ORIGIN", "http://localhost:5173")


async def build_report(question: str, max_papers: int = 5) -> dict[str, Any]:
    """Run the service pipeline and return the frontend report contract."""
    discovery = await discover_papers(question, max_papers)
    papers = discovery["items"]

    # Enrich papers: download PDFs, extract text with pypdf, populate structured
    # fields (methods, datasets, metrics, reported_results, limitations) via Groq.
    extraction = await enrich_papers(papers)
    papers = extraction["items"]

    authenticity = await verify_papers(papers)
    papers = authenticity["items"]
    comparison = await compare_papers(papers)
    reasoning = await analyze_missing_information(
        papers,
        comparison=comparison,
        research_question=question,
    )

    pipeline_warnings = (
        discovery["warnings"]
        + extraction["warnings"]
        + authenticity["warnings"]
        + comparison["warnings"]
        + reasoning["warnings"]
    )
    synthesis = await synthesize_report(
        question,
        papers,
        comparison["items"],
        reasoning["items"],
        pipeline_warnings,
    )
    synthesis_result = synthesis["items"][0] if synthesis["items"] else {}
    warnings = pipeline_warnings + synthesis["warnings"]
    trace = [
        _trace_entry("Research Manager", discovery),
        _trace_entry("Paper Extractor", extraction),
        _trace_entry("Search & Authenticity", authenticity),
        _trace_entry("Critic", comparison),
        _trace_entry("Reasoning", reasoning),
        _trace_entry("Synthesis", synthesis),
    ]
    return {
        "research_question": question,
        "papers": papers,
        "comparison": comparison["items"],
        "missing_information": reasoning["items"],
        "summary": synthesis_result.get("summary", ""),
        "key_findings": synthesis_result.get("key_findings", []),
        "candidate_gaps": synthesis_result.get("candidate_gaps", []),
        "warnings": warnings,
        "agent_trace": trace,
    }


def _trace_entry(agent_name: str, output: dict[str, Any]) -> dict[str, str]:
    return {
        "agent_name": agent_name,
        "status": str(output.get("status", "unknown")),
        "summary": str(output.get("summary", "")),
    }


class ResearchPilotHandler(BaseHTTPRequestHandler):
    """Handle health checks and research requests for local development."""

    server_version = "ResearchPilot/0.1"

    def do_OPTIONS(self) -> None:
        self._send_json(HTTPStatus.NO_CONTENT, None)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "service": "researchpilot-api"},
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Route not found."})

    def do_POST(self) -> None:
        if self.path != "/api/research":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Route not found."})
            return

        try:
            payload = self._read_json()
            question = payload.get("question")
            max_papers = payload.get("max_papers", 5)
            if not isinstance(question, str) or not question.strip():
                raise ValueError("A non-empty research question is required.")
            if isinstance(max_papers, bool) or not isinstance(max_papers, int):
                raise ValueError("max_papers must be an integer.")
            if not 1 <= max_papers <= 100:
                raise ValueError("max_papers must be between 1 and 100.")
            report = asyncio.run(build_report(question.strip(), max_papers))
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": str(exc)})
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"detail": "Request body must be valid JSON."})
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"detail": "The research pipeline failed unexpectedly."},
            )
            return
        self._send_json(HTTPStatus.OK, report)

    def _read_json(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("Request body is required.")
        try:
            length = int(content_length)
        except ValueError as exc:
            raise ValueError("Content-Length must be an integer.") from exc
        if length > 1_000_000:
            raise ValueError("Request body is too large.")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", _cors_origin())
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            if body:
                self.wfile.write(body)
        except BrokenPipeError:
            # The browser cancelled a long-running local-model request.
            return

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str = DEFAULT_HOST, port: int | None = None) -> None:
    """Start the local development API server."""
    if port is None:
        port = int(os.environ.get("RESEARCHPILOT_PORT", DEFAULT_PORT))
    server = ThreadingHTTPServer((host, port), ResearchPilotHandler)
    print(f"ResearchPilot API listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
