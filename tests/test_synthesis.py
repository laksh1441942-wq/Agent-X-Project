import asyncio
import json
from unittest.mock import patch

from app.services.synthesis import synthesize_report


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_synthesis_reports_unavailable_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:1/api/chat")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "0.1")

    result = asyncio.run(synthesize_report("question", [], [], [], []))

    assert result["status"] == "error"
    assert result["items"] == []
    assert "Ollama synthesis failed" in result["warnings"][0]


def test_synthesis_parses_structured_ollama_response(monkeypatch):
    payload = {
        "message": {
            "content": json.dumps({
                "summary": "Evidence summary",
                "key_findings": [{"finding": "A supported finding"}],
                "candidate_gaps": [{"title": "A candidate gap"}],
            }),
        },
    }

    with patch("app.services.synthesis.urlopen", return_value=FakeResponse(payload)):
        result = asyncio.run(
            synthesize_report(
                "question",
                [{"paper_id": "paper-1", "title": "Paper"}],
                [],
                [],
                [],
            )
        )

    assert result["status"] == "success"
    assert result["items"][0]["summary"] == "Evidence summary"
    assert result["items"][0]["candidate_gaps"] == [{"title": "A candidate gap"}]