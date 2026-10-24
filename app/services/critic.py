def _values(paper: dict, *keys: str) -> list[str]:
    for key in keys:
        value = paper.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            candidates = sorted(value, key=str) if isinstance(value, set) else value
        else:
            candidates = [value]
        values = [
            str(item).strip()
            for item in candidates
            if isinstance(item, (str, int, float))
            and not isinstance(item, bool)
            and str(item).strip()
        ]
        if values:
            return values
    return []


def _normalized(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted({" ".join(value.casefold().split()) for value in values}))


def _urls(paper: dict) -> list[str]:
    urls = []
    for key in ("url", "source_url", "source"):
        value = paper.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value.startswith(("https://", "http://")) and value not in urls:
                urls.append(value)
    return urls


def _display(values: list[str]) -> str:
    return "; ".join(values)


async def compare_papers(papers: list[dict]) -> dict:
    if not isinstance(papers, list):
        return {
            "agent_name": "Critic Agent",
            "status": "partial",
            "summary": "Paper input must be a list; no comparisons were performed.",
            "items": [],
            "warnings": ["Input was not a list of paper records."],
            "sources": [],
        }

    if not papers:
        return {
            "agent_name": "Critic Agent",
            "status": "success",
            "summary": "No papers were provided to compare.",
            "items": [],
            "warnings": [],
            "sources": [],
        }

    valid_papers = []
    warnings = []
    for index, paper in enumerate(papers):
        if isinstance(paper, dict):
            valid_papers.append(paper)
        else:
            warnings.append(
                f"Skipped malformed paper record at index {index}; expected a dictionary."
            )

    if not valid_papers:
        return {
            "agent_name": "Critic Agent",
            "status": "partial",
            "summary": "No valid papers were available for comparison.",
            "items": [],
            "warnings": warnings + [
                "No valid paper dictionaries were available for comparison."
            ],
            "sources": [],
        }

    items = []
    sources = []
    for paper in valid_papers:
        for url in _urls(paper):
            if url not in sources:
                sources.append(url)

    fields = {
        "dataset": ("datasets", "dataset"),
        "metric": ("metrics", "metric"),
        "result": ("reported_results", "results", "result"),
        "protocol": ("experimental_protocols", "experimental_protocol", "protocol"),
        "baseline": ("baselines", "baseline"),
        "method": ("methods", "method"),
        "limitation": ("limitations", "limitation"),
    }

    for index, left in enumerate(valid_papers):
        for right in valid_papers[index + 1:]:
            left_id = left.get("paper_id", left.get("id"))
            right_id = right.get("paper_id", right.get("id"))
            paper_ids = [
                str(value)
                for value in (left_id, right_id)
                if isinstance(value, (str, int, float))
                and not isinstance(value, bool)
                and str(value).strip()
            ]
            evidence = list(paper_ids)
            for paper in (left, right):
                for url in _urls(paper):
                    if url not in evidence:
                        evidence.append(url)

            left_data = {name: _values(left, *keys) for name, keys in fields.items()}
            right_data = {name: _values(right, *keys) for name, keys in fields.items()}
            missing = [
                name
                for name in ("dataset", "metric", "result", "protocol")
                if not left_data[name] or not right_data[name]
            ]
            baseline_missing = (
                not left_data["baseline"] or not right_data["baseline"]
            )

            if missing:
                comparability = "insufficient_information"
                reason = "Missing reported " + ", ".join(missing) + " for one or both papers."
                inference = False
            elif _normalized(left_data["dataset"]) != _normalized(right_data["dataset"]):
                comparability = "not_directly_comparable"
                reason = (
                    f"Reported datasets differ: {_display(left_data['dataset'])} vs "
                    f"{_display(right_data['dataset'])}."
                )
                inference = False
            elif _normalized(left_data["metric"]) != _normalized(right_data["metric"]):
                comparability = "not_directly_comparable"
                reason = (
                    f"Reported metrics differ: {_display(left_data['metric'])} vs "
                    f"{_display(right_data['metric'])}; scores are not ranked across metrics."
                )
                inference = False
            elif _normalized(left_data["protocol"]) != _normalized(right_data["protocol"]):
                comparability = "not_directly_comparable"
                reason = "Reported experimental protocols differ."
                inference = False
            elif (
                left_data["baseline"]
                and right_data["baseline"]
                and _normalized(left_data["baseline"]) != _normalized(right_data["baseline"])
            ):
                comparability = "not_directly_comparable"
                reason = "Reported baselines differ."
                inference = False
            else:
                comparability = "potentially_comparable"
                reason = (
                    "Inference: matching reported datasets, metrics, and experimental "
                    "protocols suggest these papers may be potentially comparable; "
                    "this does not establish that their results are directly comparable."
                )
                inference = True
                if baseline_missing:
                    reason += (
                        " Inference: because baseline information is missing for at "
                        "least one paper, a fair performance comparison cannot be established."
                    )

            details = []
            for name in ("method", "result", "limitation"):
                left_values = left_data[name]
                right_values = right_data[name]
                if left_values or right_values:
                    details.append(
                        f"Reported {name}s: {_display(left_values) or 'not reported'} vs "
                        f"{_display(right_values) or 'not reported'}"
                    )
            finding = reason
            if details:
                finding += " " + "; ".join(details) + "."

            items.append({
                "paper_ids": paper_ids,
                "dimension": "reported performance and experimental setup",
                "finding": finding,
                "comparability": comparability,
                "reason": reason,
                "evidence": evidence,
                "inference": inference,
            })
            pair = " and ".join(paper_ids) or "A paper pair"
            if comparability != "potentially_comparable":
                warnings.append(f"{pair}: {reason}")
            elif baseline_missing:
                warnings.append(
                    f"{pair}: potentially_comparable only; baseline information is "
                    "missing, so a fair performance comparison cannot be established."
                )

    insufficient = sum(
        item["comparability"] == "insufficient_information" for item in items
    )
    not_direct = sum(
        item["comparability"] == "not_directly_comparable" for item in items
    )
    incomplete = (
        insufficient > 0
        or len(valid_papers) != len(papers)
        or any(
            "baseline information is missing" in warning.casefold()
            for warning in warnings
        )
    )

    if len(valid_papers) < 2:
        status = "partial"
        summary = (
            "Fewer than two valid papers were provided; "
            "pairwise comparison is incomplete."
        )
        warnings.append("No pairwise comparisons could be generated.")
    else:
        status = "partial" if incomplete else "success"
        summary = (
            f"Compared {len(valid_papers)} valid papers across {len(items)} pairs: "
            f"{not_direct} not directly comparable and {insufficient} with "
            "insufficient information."
        )
        if len(valid_papers) != len(papers):
            summary += f" Skipped {len(papers) - len(valid_papers)} malformed record(s)."

    return {
        "agent_name": "Critic Agent",
        "status": status,
        "summary": summary,
        "items": items,
        "warnings": warnings,
        "sources": sources,
    }
