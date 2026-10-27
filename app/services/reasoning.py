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
        "sources": [],
    }


# Human-readable labels for each structured field
_FIELD_LABELS: dict[str, str] = {
    "methods": "Research methods",
    "datasets": "Datasets used",
    "metrics": "Evaluation metrics",
    "reported_results": "Reported results",
    "limitations": "Stated limitations",
}

# Recommended follow-up actions per field
_FOLLOW_UP: dict[str, str] = {
    "methods": "Check the paper's methodology section or supplementary materials.",
    "datasets": "Consult the paper's experiments section for dataset names.",
    "metrics": "Review the evaluation section for performance metrics.",
    "reported_results": "Refer to the results tables or conclusion for quantitative outcomes.",
    "limitations": "Check the discussion or future work section for stated limitations.",
}


async def analyze_missing_information(
    papers: list[dict[str, Any]],
    comparison: dict[str, Any] | None = None,
    research_question: str = "",
) -> dict[str, Any]:
    if not papers:
        return create_agent_output(
            status="success",
            summary="No papers provided; missing-information analysis skipped.",
            items=[],
            warnings=[],
        )

    checked_fields = ["methods", "datasets", "metrics", "reported_results", "limitations"]
    analysis_items: list[dict[str, Any]] = []
    papers_with_gaps: list[str] = []

    for paper in papers:
        paper_id = paper.get("paper_id", "")
        title = paper.get("title", "Untitled paper")
        short_title = title[:80] + ("…" if len(title) > 80 else "")
        abstract = paper.get("abstract", "") or ""
        has_abstract = bool(abstract.strip()) and len(abstract.strip()) > 50

        paper_has_gap = False
        for field in checked_fields:
            field_value = paper.get(field)
            is_populated = (
                isinstance(field_value, list)
                and len(field_value) > 0
                and any(str(v).strip() for v in field_value)
            )
            if is_populated:
                continue  # Field is present — no gap

            paper_has_gap = True
            label = _FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
            follow_up = _FOLLOW_UP.get(field, "Consult the full paper text.")

            if has_abstract:
                reason = (
                    f'Not reported in the retrieved OpenAlex metadata for "{short_title}". '
                    f"The paper abstract was available but structured {label.lower()} "
                    "could not be automatically extracted."
                )
            else:
                reason = (
                    f'Not reported in the retrieved metadata for "{short_title}". '
                    "No abstract was available to attempt extraction from."
                )

            analysis_items.append({
                "paper_id": paper_id,
                "paper_title": title,
                "field": label,
                "status": "not_in_retrieved_metadata",
                "reason": reason,
                "follow_up_action": follow_up,
            })

        if paper_has_gap:
            papers_with_gaps.append(short_title)

    # Deduplicate gap paper list
    unique_gap_papers = list(dict.fromkeys(papers_with_gaps))

    if not analysis_items:
        summary = (
            f"All {len(papers)} papers have complete structured metadata. "
            "No missing-information gaps were identified."
        )
        warnings: list[str] = []
    else:
        summary = (
            f"Identified missing structured fields in {len(unique_gap_papers)} of "
            f"{len(papers)} paper(s). These gaps reflect what OpenAlex metadata "
            "provides, not the actual content of the papers."
        )
        warnings = [
            "Candidate gaps reflect limits of retrieved metadata only and do not "
            "imply the papers lack this information — the full texts were not read."
        ]

    return create_agent_output(
        status="success",
        summary=summary,
        items=analysis_items,
        warnings=warnings,
    )
