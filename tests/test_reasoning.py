import asyncio
from app.services.reasoning import analyze_missing_information


def test_empty_input_returns_valid_contract():
    result = asyncio.run(analyze_missing_information(papers=[]))
    assert result["agent_name"] == "Reasoning Agent"
    assert result["status"] == "success"
    assert isinstance(result["items"], list)

def test_missing_dataset_is_flagged():
    mock_papers = [{
        "paper_id": "test-doc-1",
        "title": "Sample Analysis Paper",
        "abstract": "A complete description of training logic.",
        "methods": ["Neural net"],
        "datasets": [],
        "metrics": ["Accuracy"]
    }]
    result = asyncio.run(analyze_missing_information(papers=mock_papers))
    flagged_fields = [item["field"] for item in result["items"]]
    assert "datasets" in flagged_fields
