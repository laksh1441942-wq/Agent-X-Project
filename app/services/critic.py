async def compare_papers(papers: list[dict]) -> dict:
    if not papers:
        return {
            "agent_name": "Critic Agent",
            "status": "success",
            "summary": "No papers were provided to compare.",
            "items": [],
            "warnings": [],
            "sources": [],
        }

    return {
        "agent_name": "Critic Agent",
        "status": "partial",
        "summary": "Comparison logic is not implemented; no findings were generated.",
        "items": [],
        "warnings": ["Paper comparison has not been performed."],
        "sources": [],
    }
