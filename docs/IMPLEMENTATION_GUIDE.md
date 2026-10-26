# ResearchPilot implementation guide

This document explains what was written, why it was written, and how the
feature branches were reviewed and integrated into `main`.

## 1. Product contract used for the implementation

The team blueprint defines ResearchPilot as a prototype research assistant.
The important integrity boundaries are:

1. A search result is a candidate, not proof that a paper is relevant or
   scientifically correct.
2. Bibliographic metadata checks do not prove the paper's findings are true.
3. A missing field is evidence that information was not available in the
   retrieved record; it is not evidence that the study did not perform the
   work.
4. Candidate research gaps are limited to the retrieved literature and do not
   prove novelty.
5. Results from different datasets, metrics, or protocols must not be ranked as
   though they were directly comparable.

Every implemented agent returns the shared agent-output shape:

```json
{
  "agent_name": "string",
  "status": "success/partial/error",
  "summary": "string",
  "items": [],
  "warnings": [],
  "sources": []
}
```

## 2. Paper Discovery Agent

File: [`app/services/paper_discovery.py`](../app/services/paper_discovery.py)

### Why it was written

The workflow needs a first stage that can find three to five candidate papers
without requiring a vector database, an agent framework, or an LLM. OpenAlex
was selected as the first source because it provides scholarly metadata and
does not require adding a runtime SDK for this prototype.

### Step-by-step code flow

1. `discover_papers(question, max_papers)` validates that the question is
   non-empty and that the paper limit is a positive integer.
2. The synchronous standard-library HTTP request is moved to a worker thread
   with `asyncio.to_thread`, keeping the public function asynchronous without
   blocking the event loop.
3. `_request_openalex` builds an encoded OpenAlex `/works?search=...` request,
   sends a ten-second timeout, and asks for JSON.
4. HTTP errors, timeouts, URL errors, operating-system errors, and malformed
   JSON become a structured error response instead of crashing the workflow.
5. `_normalize_paper` copies only values present in the OpenAlex response:
   title, authors, year, DOI, source URL, stable ID, and abstract.
6. `_reconstruct_abstract` converts OpenAlex's inverted abstract index back
   into source word order. If no index exists, the abstract stays empty.
7. `_keywords` tokenizes the question and paper title/abstract while removing
   common stop words.
8. `_rank_and_deduplicate` calculates transparent relevance as the number of
   unique question tokens shared with the title/abstract, with the source
   relevance score used only as a small tie-breaker.
9. `_deduplication_key` uses the DOI when available; otherwise it uses
   normalized title tokens plus publication year.
10. The function returns the requested number of candidates and warns when
    fewer usable records were available.

### Deliberate safety behavior

- Missing DOI, abstract, methods, datasets, metrics, results, limitations, and
  missing-information values remain `null` or empty arrays.
- Every returned URL comes from the OpenAlex response.
- Every discovered paper is marked `unverified`; discovery is not
  authenticity verification.
- An empty result is returned as `partial`, with a warning rather than a
  fabricated fallback paper.

## 3. Critic Agent

File: [`app/services/critic.py`](../app/services/critic.py)

### Why it was written

The critic stage must compare evidence without making invalid cross-study
claims. It therefore performs pairwise comparison of reported fields and
separates potentially comparable papers from papers that cannot be compared
directly.

### Step-by-step code flow

1. `compare_papers(papers)` validates that the input is a list.
2. Empty input returns a valid successful response with no comparison items.
3. Non-dictionary records are skipped and explicitly listed in warnings.
4. `_values` accepts the shared plural field names and a few singular aliases,
   then safely converts non-boolean strings and numbers to comparable text.
5. `_normalized` case-folds and whitespace-normalizes values before comparing
   them, so formatting differences do not create false mismatches.
6. `_urls` collects HTTP source URLs for traceability, while `_display`
   creates readable evidence text.
7. Each pair is checked for required dataset, metric, result, and protocol
   information.
8. Missing required information produces
   `insufficient_information`.
9. Different datasets, metrics, protocols, or explicitly different baselines
   produce `not_directly_comparable`.
10. Matching reported setup produces only
    `potentially_comparable`; it does not claim direct comparability.
11. Each item includes paper IDs, dimension, finding, reason, evidence, and an
    `inference` boolean so downstream reporting can distinguish source facts
    from cautious inference.
12. The aggregate status is `partial` whenever information is insufficient,
    records were malformed, baselines are missing, or any pair is not directly
    comparable.

### Review fix applied during merge

The first critic implementation correctly labelled individual pairs as
`not_directly_comparable`, but its aggregate status could still be `success`.
The merge review changed the `incomplete` calculation so any such pair makes
the overall output `partial`. This prevents the report from looking fully
successful when comparisons are unsafe.

## 4. Reasoning Agent

Final file: [`app/services/reasoning.py`](../app/services/reasoning.py)

Original feature-branch file:
`Ishu_Goyal_submission/reasoning.py`

### Why it was written

The reasoning stage identifies what cannot be confirmed from the structured
paper records. It does not claim that empty fields are proof of missing
research; it reports missing extracted information and suggests follow-up
checks.

### Step-by-step code flow

1. `analyze_missing_information` accepts paper records and optional comparison
   and research-question inputs for future orchestration.
2. Empty paper input returns a valid success-shaped agent response with a
   warning that analysis was bypassed.
3. For each paper, the function records the paper ID and title for traceable
   findings.
4. It checks the structured `methods`, `datasets`, `metrics`,
   `reported_results`, and `limitations` fields.
5. A populated list is treated as available extracted information.
6. An empty or absent field becomes an item with
   `missing_from_extracted_data` and a follow-up action.
7. If the abstract is empty or begins with the known restricted-summary
   marker, the field is instead marked `not_checked`, because the source text
   was not sufficient to support the stronger missing-data conclusion.
8. Every result includes the paper ID, field, status, reason, and suggested
   follow-up action.
9. The warning states that candidate gaps are limited to the retrieved
   literature and do not establish novelty.

### Integration cleanup

The original branch included unused imports, Python bytecode files, and a
submission-specific package directory. During merge:

- the implementation moved to the agreed `app/services` package;
- its test moved to the shared `tests` directory;
- generated `__pycache__` files were removed;
- the test was changed from `pytest-asyncio` markers to
  `asyncio.run`, avoiding an unnecessary plugin dependency; and
- type annotations were modernized to match the Python 3.11/3.12 target.

## 5. Search & Authenticity Agent

File: [`app/services/search_authenticity.py`](../app/services/search_authenticity.py)

The authenticity implementation lives in the canonical `app/services`
package. The previous empty `MANAS/app` placeholders were removed so the
project has one import path and one implementation.

`verify_papers` accepts the discovery agent's paper records and checks each
title or DOI against OpenAlex using a timeout and structured error handling. A
matching record produces `verified` metadata status; a metadata mismatch or a
record with insufficient identifiers produces `partially_verified`; no match
or a failed lookup remains `unverified`. Original paper fields are preserved,
and each record receives `authenticity_reasons` for traceability.

This stage verifies bibliographic metadata only. It does not verify scientific
claims, results, or the truth of a paper. `check_authenticity` is provided as a
compatibility alias for orchestration code.

Tests are in
[`tests/test_search_authenticity.py`](../tests/test_search_authenticity.py).
They cover DOI matching, title lookup, lookup failures, and malformed input.

## 6. Tests and validation

Discovery tests are in
[`tests/test_paper_discovery.py`](../tests/test_paper_discovery.py). They cover:

- normalization and ranking;
- DOI deduplication;
- missing DOI and abstract handling;
- structured network failure handling; and
- invalid input.

Reasoning tests are in
[`tests/test_reasoning.py`](../tests/test_reasoning.py). They cover:

- empty input contract behavior; and
- missing dataset detection.

The critic was validated with a direct smoke test using two papers with
different datasets. The expected result was `partial` with
`not_directly_comparable`.

The final full test command was:

```bash
python3 -m pytest -q
```

Result: **7 passed**.

The merged diff also passed:

```bash
git diff --check origin/main...main
```

## 7. Feature branch and merge history

### `feat/critic-agent`

This branch started with a critic skeleton and then added the full comparison
logic in `app/services/critic.py`. It was merged with a dedicated merge
commit. The aggregate-status issue found during review was fixed on `main`
before continuing.

### `feat/reasoning-agent`

This branch added the reasoning implementation and tests under
`Ishu_Goyal_submission/`. It was merged, reviewed, and then integrated into
the project layout as described above. Generated bytecode was removed rather
than carried forward.

### Discovery work on `main`

The discovery implementation, its tests, and its README documentation were
committed before the feature branches were merged. This established the
OpenAlex contract that the critic and reasoning stages consume.

### Commit sequence

The meaningful implementation commits are:

1. `4b36874` - add OpenAlex paper discovery agent
2. `72e4820` - add discovery contract tests
3. `843250a` - document discovery implementation
4. `874f96b` - merge critic agent
5. `316144b` - surface incomparable critic results
6. `eec663d` - merge reasoning agent
7. `8e1763d` - integrate reasoning agent into `app`
8. `e410516` - normalize merged file whitespace

## 8. Current limitations and next implementation step

There is not yet a FastAPI application, shared Pydantic schema module, or
orchestrator connecting all three services. OpenAlex is the only discovery
source, and network failure currently returns an error rather than a demo
fixture. The next step is to add the team-lead-owned API and orchestrator,
then test the complete question-to-report workflow.
