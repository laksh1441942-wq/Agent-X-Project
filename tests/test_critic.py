import pytest

from app.services.critic import compare_papers


def _paper(**overrides):
    paper = {
        "paper_id": "paper-1",
        "datasets": ["Dataset A"],
        "metrics": ["Accuracy"],
        "reported_results": ["0.91"],
        "experimental_protocols": ["5-fold cross-validation"],
        "baselines": ["Baseline X"],
    }
    paper.update(overrides)
    return paper


@pytest.mark.asyncio
async def test_empty_input_returns_success_without_comparisons():
    result = await compare_papers([])

    assert result["status"] == "success"
    assert result["items"] == []
    assert result["warnings"] == []
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_non_list_input_returns_partial_result():
    result = await compare_papers("not a list")

    assert result["status"] == "partial"
    assert result["items"] == []
    assert result["warnings"] == ["Input was not a list of paper records."]


@pytest.mark.asyncio
async def test_malformed_records_are_skipped_with_warnings():
    result = await compare_papers([None, "not a paper"])

    assert result["status"] == "partial"
    assert result["items"] == []
    assert result["warnings"] == [
        "Skipped malformed paper record at index 0; expected a dictionary.",
        "Skipped malformed paper record at index 1; expected a dictionary.",
        "No valid paper dictionaries were available for comparison.",
    ]


@pytest.mark.asyncio
async def test_valid_paper_is_retained_when_another_record_is_malformed():
    result = await compare_papers([
        _paper(url="https://example.test/paper-1"),
        None,
    ])

    assert result["status"] == "partial"
    assert result["summary"].startswith("Fewer than two valid papers")
    assert result["sources"] == ["https://example.test/paper-1"]
    assert result["warnings"] == [
        "Skipped malformed paper record at index 1; expected a dictionary.",
        "No pairwise comparisons could be generated.",
    ]


@pytest.mark.asyncio
async def test_one_valid_paper_returns_partial_without_pairs():
    result = await compare_papers([_paper()])

    assert result["status"] == "partial"
    assert result["items"] == []
    assert result["warnings"] == ["No pairwise comparisons could be generated."]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "reason_fragment"),
    [
        ("datasets", ["Dataset B"], "Reported datasets differ"),
        ("metrics", ["F1"], "Reported metrics differ"),
    ],
)
async def test_different_datasets_or_metrics_are_not_comparable(
    field, value, reason_fragment
):
    left = _paper(paper_id="paper-1")
    right = _paper(paper_id="paper-2", **{field: value})

    result = await compare_papers([left, right])
    item = result["items"][0]

    assert result["status"] == "success"
    assert item["comparability"] == "not_directly_comparable"
    assert reason_fragment in item["reason"]
    assert item["paper_ids"] == ["paper-1", "paper-2"]
    assert result["warnings"] == [f"paper-1 and paper-2: {item['reason']}"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "expected_missing"),
    [
        ("reported_results", "result"),
        ("experimental_protocols", "protocol"),
    ],
)
async def test_missing_results_or_protocols_are_insufficient(
    field, expected_missing
):
    left = _paper(paper_id="paper-1", **{field: []})
    right = _paper(paper_id="paper-2")

    result = await compare_papers([left, right])
    item = result["items"][0]

    assert result["status"] == "partial"
    assert item["comparability"] == "insufficient_information"
    assert f"Missing reported {expected_missing}" in item["reason"]
    assert item["evidence"] == ["paper-1", "paper-2"]
    assert result["warnings"] == [f"paper-1 and paper-2: {item['reason']}"]


@pytest.mark.asyncio
async def test_matching_setup_and_baselines_are_potentially_comparable():
    left = _paper(paper_id="paper-1")
    right = _paper(paper_id="paper-2", reported_results=["0.87"])

    result = await compare_papers([left, right])
    item = result["items"][0]

    conflict_warning = (
        "paper-1 and paper-2: Apparent result conflict: reported results differ "
        "(0.91 vs 0.87); differing reported values alone do not prove a contradiction."
    )
    assert result["status"] == "success"
    assert item["comparability"] == "potentially_comparable"
    assert item["inference"] is True
    assert "differing reported values alone do not prove a contradiction" in item["finding"]
    assert result["warnings"] == [conflict_warning]


@pytest.mark.asyncio
async def test_different_baselines_are_not_directly_comparable():
    left = _paper(paper_id="paper-1")
    right = _paper(paper_id="paper-2", baselines=["Baseline Y"])

    result = await compare_papers([left, right])
    item = result["items"][0]

    assert result["status"] == "success"
    assert item["comparability"] == "not_directly_comparable"
    assert item["reason"] == "Reported baselines differ."
    assert result["warnings"] == ["paper-1 and paper-2: Reported baselines differ."]


@pytest.mark.asyncio
async def test_paper_ids_and_source_urls_are_preserved_as_evidence():
    left = _paper(
        paper_id="paper-1",
        url="https://example.test/paper-1",
    )
    right = _paper(
        paper_id="paper-2",
        source_url="https://example.test/paper-2",
    )

    result = await compare_papers([left, right])
    item = result["items"][0]

    assert item["paper_ids"] == ["paper-1", "paper-2"]
    assert item["evidence"] == [
        "paper-1",
        "paper-2",
        "https://example.test/paper-1",
        "https://example.test/paper-2",
    ]
    assert result["sources"] == [
        "https://example.test/paper-1",
        "https://example.test/paper-2",
    ]


@pytest.mark.asyncio
async def test_conflicting_reported_results_are_returned_deterministically():
    papers = [
        _paper(
            paper_id="paper-1",
            url="https://example.test/paper-1",
            reported_results=["0.91"],
        ),
        _paper(
            paper_id="paper-2",
            source_url="https://example.test/paper-2",
            reported_results=["0.72"],
        ),
    ]

    first = await compare_papers(papers)
    second = await compare_papers(papers)
    item = first["items"][0]
    conflict = (
        "Apparent result conflict: reported results differ (0.91 vs 0.72); "
        "differing reported values alone do not prove a contradiction."
    )

    assert first == second
    assert first["status"] == "success"
    assert item["comparability"] == "potentially_comparable"
    assert "Reported results: 0.91 vs 0.72" in item["finding"]
    assert conflict in item["finding"]
    assert item["paper_ids"] == ["paper-1", "paper-2"]
    assert item["evidence"] == [
        "paper-1",
        "paper-2",
        "https://example.test/paper-1",
        "https://example.test/paper-2",
    ]
    assert first["sources"] == [
        "https://example.test/paper-1",
        "https://example.test/paper-2",
    ]
    assert first["warnings"] == [f"paper-1 and paper-2: {conflict}"]


@pytest.mark.asyncio
async def test_result_conflict_is_flagged_even_when_datasets_differ():
    papers = [
        _paper(
            paper_id="paper-1",
            url="https://example.test/paper-1",
            reported_results=["0.91"],
        ),
        _paper(
            paper_id="paper-2",
            source_url="https://example.test/paper-2",
            datasets=["Dataset B"],
            reported_results=["0.72"],
        ),
    ]

    result = await compare_papers(papers)
    item = result["items"][0]
    conflict = (
        "Apparent result conflict: reported results differ (0.91 vs 0.72); "
        "differing reported values alone do not prove a contradiction."
    )

    assert item["comparability"] == "not_directly_comparable"
    assert "Reported datasets differ" in item["reason"]
    assert conflict in item["finding"]
    assert item["paper_ids"] == ["paper-1", "paper-2"]
    assert item["evidence"] == [
        "paper-1",
        "paper-2",
        "https://example.test/paper-1",
        "https://example.test/paper-2",
    ]
    assert result["warnings"] == [
        f"paper-1 and paper-2: {item['reason']}",
        f"paper-1 and paper-2: {conflict}",
    ]


@pytest.mark.asyncio
async def test_multiple_mismatches_are_all_reported_for_a_pair():
    left = _paper(paper_id="paper-1")
    right = _paper(
        paper_id="paper-2",
        datasets=["Dataset B"],
        metrics=["F1"],
        experimental_protocols=["held-out test set"],
        baselines=["Baseline Y"],
    )

    result = await compare_papers([left, right])
    item = result["items"][0]

    assert result["status"] == "success"
    assert item["comparability"] == "not_directly_comparable"
    assert "Reported datasets differ" in item["reason"]
    assert "Reported metrics differ" in item["reason"]
    assert "Reported experimental protocols differ" in item["reason"]
    assert "Reported baselines differ" in item["reason"]
    assert result["warnings"] == [f"paper-1 and paper-2: {item['reason']}"]


def _papers_with_matching_required_evidence(left_fields, right_fields):
    required_evidence = {
        "datasets": ["Dataset A"],
        "metrics": ["Accuracy"],
        "reported_results": ["0.91"],
        "experimental_protocols": ["5-fold cross-validation"],
        "baselines": ["Baseline X"],
    }
    left = {**required_evidence, **left_fields, "paper_id": "paper-1"}
    right = {**required_evidence, **right_fields, "paper_id": "paper-2"}
    return [_paper(**left), _paper(**right)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("left_fields", "right_fields", "label", "left_value", "right_value"),
    [
        (
            {"research_objective": ["Classify images"]},
            {"objective": ["Classify images"]},
            "research objectives",
            "Classify images",
            "Classify images",
        ),
        (
            {"methods": ["Transformer"]},
            {"architecture": ["Transformer"]},
            "methods/architecture",
            "Transformer",
            "Transformer",
        ),
        (
            {"limitations": ["Small sample size"]},
            {"limitations": ["Small sample size"]},
            "limitations",
            "Small sample size",
            "Small sample size",
        ),
    ],
)
async def test_matching_reported_objectives_methods_and_limitations(
    left_fields, right_fields, label, left_value, right_value
):
    result = await compare_papers(
        _papers_with_matching_required_evidence(left_fields, right_fields)
    )
    item = result["items"][0]

    assert item["comparability"] == "potentially_comparable"
    assert f"Inference: reported {label} match:" in item["finding"]
    assert left_value in item["finding"]
    assert right_value in item["finding"]
    assert "paper-1" in item["evidence"]
    assert "paper-2" in item["evidence"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("left_fields", "right_fields", "label", "left_value", "right_value"),
    [
        (
            {"research_objective": ["Classify images"]},
            {"objective": ["Detect objects"]},
            "research objectives",
            "Classify images",
            "Detect objects",
        ),
        (
            {"methods": ["Transformer"]},
            {"architecture": ["Convolutional network"]},
            "methods/architecture",
            "Transformer",
            "Convolutional network",
        ),
        (
            {"limitations": ["Small sample size"]},
            {"limitations": ["Limited compute"]},
            "limitations",
            "Small sample size",
            "Limited compute",
        ),
    ],
)
async def test_differing_reported_objectives_methods_and_limitations(
    left_fields, right_fields, label, left_value, right_value
):
    result = await compare_papers(
        _papers_with_matching_required_evidence(left_fields, right_fields)
    )
    item = result["items"][0]

    assert item["comparability"] == "potentially_comparable"
    assert f"Inference: reported {label} differ:" in item["finding"]
    assert left_value in item["finding"]
    assert right_value in item["finding"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("left_fields", "right_fields", "label", "reported_value", "missing_value"),
    [
        (
            {},
            {"research_objective": ["Classify images"]},
            "research objectives",
            "Classify images",
            "paper 1 reported not reported",
        ),
        (
            {"methods": ["Transformer"]},
            {},
            "methods/architecture",
            "Transformer",
            "paper 2 reported not reported",
        ),
        (
            {},
            {"limitations": ["Small sample size"]},
            "limitations",
            "Small sample size",
            "paper 1 reported not reported",
        ),
    ],
)
async def test_missing_reported_objectives_methods_and_limitations_are_not_inferred(
    left_fields, right_fields, label, reported_value, missing_value
):
    result = await compare_papers(
        _papers_with_matching_required_evidence(left_fields, right_fields)
    )
    item = result["items"][0]

    assert item["comparability"] == "potentially_comparable"
    assert f"Inference: comparison of reported {label} is incomplete:" in item["finding"]
    assert reported_value in item["finding"]
    assert missing_value in item["finding"]
