# Critic Comparison Agent

The Critic Comparison Agent compares reported evidence across paper pairs, highlights differences and apparent result conflicts, and indicates when the available information does not support a comparison. It uses deterministic Python logic; it does not currently perform an LLM-based review.

## Interface and output

```python
async def compare_papers(papers: list[dict]) -> dict:
    ...
```

The result follows the shared agent contract:

```json
{
  "agent_name": "string",
  "status": "success | partial | error",
  "summary": "string",
  "items": [],
  "warnings": [],
  "sources": []
}
```

Each pairwise item includes `paper_ids`, `dimension`, `finding`, `comparability`, `reason`, `evidence`, and `inference`. The current implementation returns `success` or `partial` (not `error`).

## Comparison dimensions

For each pair, the agent considers:

- **Research objectives** (`research_objective` or `objective`)
- **Methods and architecture** (`methods`, `method`, `architectures`, or `architecture`)
- **Datasets** (`datasets` or `dataset`)
- **Metrics** (`metrics` or `metric`)
- **Reported results** (`reported_results`, `results`, or `result`)
- **Experimental protocols** (`experimental_protocols`, `experimental_protocol`, or `protocol`)
- **Baselines** (`baselines` or `baseline`)
- **Limitations** (`limitations` or `limitation`)

Objectives, methods/architecture, and limitations are described as reported matches, differences, or incomplete comparisons. They do not determine the comparability label. Dataset, metric, protocol, and baseline mismatches inform the label. Differing reported results are preserved and flagged as an *apparent* conflict, not proof of a contradiction.

## Comparability labels

- **`insufficient_information`** — Either paper lacks a reported dataset, metric, result, or experimental protocol. This takes precedence over mismatch labels; any detected mismatches are still included in the reason.
- **`not_directly_comparable`** — Required information is present, but reported datasets, metrics, experimental protocols, or baselines differ. Different metrics are explicitly not ranked against one another.
- **`potentially_comparable`** — Required information is present and those four setup fields match after case-folding, whitespace collapsing, and sorted-set comparison, so value order and duplicates do not affect matching. This is an inference, not proof that results are directly comparable. When required information is present and no mismatches are found, missing baseline information does not change `potentially_comparable`; it adds a warning that a fair performance comparison cannot be established.

## Warnings and traceability

Non-dictionary paper records are skipped with an indexed warning. For recognized comparison fields, nonempty values of unsupported types are ignored with a warning identifying the input index, field, and value type; supported values are strings and numbers other than booleans. Missing or ignored values may leave evidence incomplete.

Each pair includes available paper IDs (`paper_id`, falling back to `id`) and string values beginning with lowercase `http://` or `https://` from `url`, `source_url`, or `source` in its evidence. Unique links are also collected in the top-level `sources` list. Results and links are reported as supplied; the agent does not verify their scientific accuracy.

## Current limitations

- Comparisons rely on structured fields supplied in the paper records; the agent does not read or interpret paper text.
- The implementation is deterministic Python logic and does not currently perform an LLM-based review.
- Matching reported setup only suggests potential comparability; it does not establish equivalent experiments or validate claims.
- Result differences are textual apparent conflicts, not proof of contradiction, and scores are not numerically ranked.
- Missing baselines prevent establishing a fair performance comparison even when the label is `potentially_comparable`.
- Empty input returns success with no comparisons; malformed records, fewer than two valid papers, missing required evidence, or missing-baseline warnings can yield partial status.

## Test

Run the focused test module with:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest -q tests/test_critic.py
```

**Recorded result:** 26 tests passed (the supplied result; not rerun in this session).
