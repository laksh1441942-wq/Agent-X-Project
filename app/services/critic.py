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
        "objective": ("research_objective", "objective"),
        "dataset": ("datasets", "dataset"),
        "metric": ("metrics", "metric"),
        "result": ("reported_results", "results", "result"),
        "protocol": ("experimental_protocols", "experimental_protocol", "protocol"),
        "baseline": ("baselines", "baseline"),
        "method": ("methods", "method", "architectures", "architecture"),
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

            mismatches = []
            if (
                left_data["dataset"]
                and right_data["dataset"]
                and _normalized(left_data["dataset"]) != _normalized(right_data["dataset"])
            ):
                mismatches.append(
                    f"Reported datasets differ: {_display(left_data['dataset'])} vs "
                    f"{_display(right_data['dataset'])}."
                )
            if (
                left_data["metric"]
                and right_data["metric"]
                and _normalized(left_data["metric"]) != _normalized(right_data["metric"])
            ):
                mismatches.append(
                    f"Reported metrics differ: {_display(left_data['metric'])} vs "
                    f"{_display(right_data['metric'])}; scores are not ranked across metrics."
                )
            if (
                left_data["protocol"]
                and right_data["protocol"]
                and _normalized(left_data["protocol"]) != _normalized(right_data["protocol"])
            ):
                mismatches.append("Reported experimental protocols differ.")
            if (
                left_data["baseline"]
                and right_data["baseline"]
                and _normalized(left_data["baseline"]) != _normalized(right_data["baseline"])
            ):
                mismatches.append("Reported baselines differ.")

            if missing:
                comparability = "insufficient_information"
                reason = "Missing reported " + ", ".join(missing) + " for one or both papers."
                if mismatches:
                    reason += " " + " ".join(mismatches)
                inference = False
            elif mismatches:
                comparability = "not_directly_comparable"
                reason = " ".join(mismatches)
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
            for name, label in (
                ("objective", "research objectives"),
                ("method", "methods/architecture"),
                ("limitation", "limitations"),
            ):
                left_values = left_data[name]
                right_values = right_data[name]
                left_reported = _display(left_values) or "not reported"
                right_reported = _display(right_values) or "not reported"
                if left_values and right_values:
                    relation = (
                        "match"
                        if _normalized(left_values) == _normalized(right_values)
                        else "differ"
                    )
                    details.append(
                        f"Inference: reported {label} {relation}: paper 1 reported "
                        f"{left_reported} vs paper 2 reported {right_reported}"
                    )
                else:
                    details.append(
                        f"Inference: comparison of reported {label} is incomplete: "
                        f"paper 1 reported {left_reported} vs "
                        f"paper 2 reported {right_reported}"
                    )
            if left_data["result"] or right_data["result"]:
                details.append(
                    f"Reported results: {_display(left_data['result']) or 'not reported'} vs "
                    f"{_display(right_data['result']) or 'not reported'}"
                )
            result_conflict = (
                bool(left_data["result"])
                and bool(right_data["result"])
                and _normalized(left_data["result"]) != _normalized(right_data["result"])
            )
            conflict_reason = (
                "Apparent result conflict: reported results differ "
                f"({_display(left_data['result'])} vs {_display(right_data['result'])}); "
                "differing reported values alone do not prove a contradiction."
            )
            finding = reason
            if details:
                finding += " " + "; ".join(details) + "."
            if result_conflict:
                finding += " " + conflict_reason

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
            if result_conflict:
                warnings.append(f"{pair}: {conflict_reason}")

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
