import asyncio
import json
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

from app.services.search_authenticity import verify_papers


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def run_verification(papers):
    return asyncio.run(verify_papers(papers))


def test_matching_doi_marks_paper_verified():
    paper = {"paper_id": "W1", "title": "Reliable Results", "doi": "10.1234/example"}
    payload = {"title": "Reliable Results", "doi": "https://doi.org/10.1234/example"}

    with patch("app.services.search_authenticity.urlopen", return_value=FakeResponse(payload)):
        result = run_verification([paper])

    assert result["status"] == "success"
    assert result["items"][0]["authenticity_status"] == "verified"
    assert result["items"][0]["title"] == paper["title"]


def test_title_search_marks_match_verified_and_preserves_query():
    paper = {"paper_id": "W1", "title": "Reliable Results"}
    payload = {"results": [{"title": "Reliable Results", "id": "W1"}]}

    def openalex(request: Request, timeout: int, context):
        assert parse_qs(urlparse(request.full_url).query)["search"] == [paper["title"]]
        return FakeResponse(payload)

    with patch("app.services.search_authenticity.urlopen", side_effect=openalex):
        result = run_verification([paper])

    assert result["items"][0]["authenticity_status"] == "verified"


def test_lookup_failure_returns_partial_output():
    with patch(
        "app.services.search_authenticity.urlopen",
        side_effect=URLError("offline"),
    ):
        result = run_verification([{"paper_id": "W1", "title": "Paper"}])

    assert result["status"] == "partial"
    assert result["items"][0]["authenticity_status"] == "unverified"
    assert "lookup failed" in result["warnings"][0]


def test_malformed_records_are_skipped_with_warning():
    result = run_verification(["not a paper"])

    assert result["status"] == "partial"
    assert result["items"] == []
    assert "malformed" in result["warnings"][0]