import asyncio
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch
from urllib.error import URLError

from app.services.paper_discovery import discover_papers


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def run_discovery(question, max_papers=5):
    return asyncio.run(discover_papers(question, max_papers))


def openalex_paper(
    title,
    *,
    paper_id="https://openalex.org/W1",
    doi=None,
    year=2024,
    abstract=None,
    relevance_score=1.0,
):
    paper = {
        "id": paper_id,
        "title": title,
        "publication_year": year,
        "doi": doi,
        "openalex_url": paper_id,
        "relevance_score": relevance_score,
        "authorships": [
            {"author": {"display_name": "Ada Lovelace"}},
        ],
    }
    if abstract is not None:
        paper["abstract_inverted_index"] = abstract
    return paper


def test_normalizes_and_ranks_openalex_results():
    payload = {
        "results": [
            openalex_paper(
                "Graph Neural Networks for Climate Forecasting",
                abstract={"climate": [0], "forecasting": [1]},
                doi="https://doi.org/10.1234/example",
            ),
            openalex_paper("An Unrelated Topic", paper_id="https://openalex.org/W2"),
        ]
    }

    with patch(
        "app.services.paper_discovery.urlopen",
        return_value=FakeResponse(payload),
    ):
        result = run_discovery("climate forecasting", 1)

    assert result["status"] == "success"
    assert len(result["items"]) == 1
    paper = result["items"][0]
    assert paper["title"] == "Graph Neural Networks for Climate Forecasting"
    assert paper["authors"] == ["Ada Lovelace"]
    assert paper["abstract"] == "climate forecasting"
    assert paper["doi"] == "https://doi.org/10.1234/example"
    assert paper["authenticity_status"] == "unverified"


def test_deduplicates_by_doi_and_keeps_best_ranked_record():
    payload = {
        "results": [
            openalex_paper(
                "First title",
                paper_id="https://openalex.org/W1",
                doi="https://doi.org/10.1234/same",
                abstract={"research": [0]},
            ),
            openalex_paper(
                "Research methods title",
                paper_id="https://openalex.org/W2",
                doi="https://doi.org/10.1234/same",
                abstract={"research": [0], "methods": [1]},
            ),
        ]
    }

    with patch(
        "app.services.paper_discovery.urlopen",
        return_value=FakeResponse(payload),
    ):
        result = run_discovery("research methods", 5)

    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == "Research methods title"


def test_missing_metadata_is_not_invented():
    payload = {"results": [openalex_paper("Paper without abstract")]}

    with patch(
        "app.services.paper_discovery.urlopen",
        return_value=FakeResponse(payload),
    ):
        result = run_discovery("missing metadata")

    paper = result["items"][0]
    assert paper["abstract"] == ""
    assert paper["doi"] is None
    assert paper["methods"] == []


def test_request_failure_returns_structured_warning():
    with patch(
        "app.services.paper_discovery.urlopen",
        side_effect=URLError("offline"),
    ):
        result = run_discovery("quantum computing")

    assert result["status"] == "error"
    assert result["items"] == []
    assert "OpenAlex search failed" in result["warnings"][0]


def test_openalex_request_uses_verified_tls_context():
    payload = {"results": [openalex_paper("TLS verified paper")]}

    with patch(
        "app.services.paper_discovery.urlopen",
        return_value=FakeResponse(payload),
    ) as request:
        run_discovery("tls verification")

    assert request.call_args.kwargs["context"] is not None


def test_openalex_question_wildcards_are_not_sent_to_search():
    payload = {"results": [openalex_paper("Question punctuation")]}

    with patch(
        "app.services.paper_discovery.urlopen",
        return_value=FakeResponse(payload),
    ) as request:
        run_discovery("How do models compare?")

    url = request.call_args.args[0].full_url
    assert parse_qs(urlparse(url).query)["search"] == ["How do models compare"]


def test_invalid_input_returns_structured_error():
    result = run_discovery(" ", 0)

    assert result["status"] == "error"
    assert result["items"] == []
    assert result["warnings"] == ["A non-empty research question is required."]
