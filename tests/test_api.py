import asyncio
import json
from http.client import HTTPConnection
from threading import Thread

from app.api import ResearchPilotHandler
from http.server import ThreadingHTTPServer


def test_build_report_composes_service_outputs(monkeypatch):
    async def fake_discover(question, max_papers):
        return {"items": [{"paper_id": "paper-1"}], "warnings": ["discovery warning"]}

    async def fake_verify(papers):
        return {"items": papers, "warnings": []}

    async def fake_compare(papers):
        return {"items": [{"paper_ids": ["paper-1"]}], "warnings": []}

    async def fake_reason(papers, comparison, research_question):
        return {"items": [{"field": "metrics"}], "warnings": ["reasoning warning"]}

    monkeypatch.setattr("app.api.discover_papers", fake_discover)
    monkeypatch.setattr("app.api.verify_papers", fake_verify)
    monkeypatch.setattr("app.api.compare_papers", fake_compare)
    monkeypatch.setattr("app.api.analyze_missing_information", fake_reason)

    from app.api import build_report

    report = asyncio.run(build_report("test question", 3))

    assert report["research_question"] == "test question"
    assert report["papers"] == [{"paper_id": "paper-1"}]
    assert report["comparison"] == [{"paper_ids": ["paper-1"]}]
    assert report["missing_information"] == [{"field": "metrics"}]
    assert report["warnings"] == ["discovery warning", "reasoning warning"]
    assert len(report["agent_trace"]) == 5


def test_health_endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), ResearchPilotHandler)
    thread = Thread(target=server.handle_request)
    thread.start()
    connection = HTTPConnection(*server.server_address)
    connection.request("GET", "/api/health")
    response = connection.getresponse()
    payload = json.loads(response.read())
    thread.join(timeout=2)
    server.server_close()

    assert response.status == 200
    assert payload["status"] == "ok"
