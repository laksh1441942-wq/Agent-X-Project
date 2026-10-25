from typing import List, Dict, Any, Optional

def create_agent_output(status: str, summary: str, items: List[Dict[str, Any]] = None, warnings: List[str] = None) -> Dict[str, Any]:
    return {
        "agent_name": "Reasoning Agent",
        "status": status,
        "summary": summary,
        "items": items if items is not None else [],
        "warnings": warnings if warnings is not None else [],
        "sources": []
    }

async def analyze_missing_information(
    papers: List[Dict[str, Any]],
    comparison: Optional[Dict[str, Any]] = None,
    research_question: str = ""
) -> Dict[str, Any]:
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

    def has_extracted_content(value: Any) -> bool:
        """Return whether a structured field contains usable extracted content."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set)):
            return any(has_extracted_content(item) for item in value)
        if isinstance(value, dict):
            return any(has_extracted_content(item) for item in value.values())
        # Numeric and boolean values can be valid reported results (including 0/False).
        return True

    def abstract_is_unavailable(value: Any) -> bool:
        if not isinstance(value, str) or not value.strip():
            return True
        return value.strip().lower().startswith("abstract indexing summary restricted")

    for paper in papers:
        if not isinstance(paper, dict):
            warnings_list.append("Skipped a paper record that was not an object.")
            continue

        paper_id = paper.get("paper_id", "unknown-id")
        title = paper.get("title", "Untitled Source")
        abstract_missing = abstract_is_unavailable(paper.get("abstract", ""))

        for field in checked_fields:
            if has_extracted_content(paper.get(field)):
                continue

            status = "missing_from_extracted_data"
            reason = f"The field '{field}' is absent or contains no usable extracted content."
            follow_up = "Request upstream processing pipeline update or verify structured JSON generation parsers."

            if abstract_missing:
                status = "not_checked"
                reason = "The abstract is unavailable or restricted, so full-content extraction cannot be verified."
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
