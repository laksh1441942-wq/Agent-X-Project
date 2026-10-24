from typing import Any


def create_agent_output(
    status: str,
    summary: str,
    items: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "agent_name": "Reasoning Agent",
        "status": status,
        "summary": summary,
        "items": items if items is not None else [],
        "warnings": warnings if warnings is not None else [],
        "sources": []
    }

async def analyze_missing_information(
    papers: list[dict[str, Any]],
    comparison: dict[str, Any] | None = None,
    research_question: str = ""
) -> dict[str, Any]:
    if not papers:
        return create_agent_output(
            status="success",
            summary="No papers provided to reason over. Analysis bypassed cleanly.",
            items=[],
            warnings=["Input paper array was empty."]
        )

    checked_fields = ["methods", "datasets", "metrics", "reported_results", "limitations"]
    analysis_items = []
    warnings_list = ["Candidate gaps reflect limits of retrieved literature only. They do not prove absolute novelty."]

    for paper in papers:
        paper_id = paper.get("paper_id", "unknown-id")
        title = paper.get("title", "Untitled Source")

        abstract = paper.get("abstract", "")
        abstract_missing = not abstract or abstract.strip().lower().startswith("abstract indexing summary restricted")

        for field in checked_fields:
            field_value = paper.get(field)

            if field_value and isinstance(field_value, list) and len(field_value) > 0:
                continue

            status = "missing_from_extracted_data"
            reason = f"The field '{field}' contains an empty array payload in the input object data."
            follow_up = "Request upstream processing pipeline update or verify structured JSON generation parsers."

            if abstract_missing:
                status = "not_checked"
                reason = f"The pipeline only extracted a truncated summary/abstract preview. Full content parsing unverified."
                follow_up = "Inspect full text documentation or supplementary materials to verify structural footprint."

            analysis_items.append({
                "paper_id": paper_id,
                "field": field,
                "status": status,
                "reason": f"[{title}] {reason}",
                "follow_up_action": follow_up
            })

    summary_text = f"Evaluated structural completeness across {len(papers)} paper records."
    return create_agent_output(status="success", summary=summary_text, items=analysis_items, warnings=warnings_list)
