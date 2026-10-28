# Evidence Ledger Feature

## 1. Purpose

The Evidence Ledger is the traceability layer of ResearchPilot. It connects a
report conclusion to the paper records and structured evidence that support it.
Users can expand each ledger item to inspect:

- the claim or conclusion;
- its explanation;
- supporting paper IDs and titles;
- extracted methods, datasets, metrics, results, and limitations;
- source links and DOI links;
- provenance: source-reported, model-synthesized, or inferred;
- authenticity status and verification reasons;
- missing or conflicting information;
- uncertainty;
- page, table, or figure references when returned by the API; and
- follow-up actions when returned by the API.

The feature is intentionally evidence-bound. It renders fields supplied by the
API and displays unavailable values as unavailable. It does not create papers,
citations, claims, metrics, or page numbers.

## 2. Where it is implemented

### Main React implementation

File: `frontend/src/App.jsx`

- `EvidenceLedger`: builds and renders the ledger.
- `Results`: passes report data into `EvidenceLedger`.
- `PaperDrawer`: provides a related paper-level evidence view.
- `asList`: safely handles optional array fields.
- `text`: safely handles optional strings and fallback labels.

### Visual implementation

File: `frontend/styles.css`

The main style groups are:

- `.evidence-ledger-section`
- `.evidence-ledger-list`
- `.evidence-entry`
- `.evidence-entry-body`
- `.evidence-entry-grid`
- `.evidence-detail-block`
- `.evidence-sources`
- `.evidence-follow-up`

### Backend data providers

The ledger consumes the existing report returned by `app/api.py`. It does not
make a new network request.

- `app/services/paper_discovery.py` supplies paper IDs, titles, URLs, DOI,
  authors, year, abstract, and source metadata.
- `app/services/paper_extractor.py` supplies structured methods, datasets,
  metrics, reported results, and limitations.
- `app/services/search_authenticity.py` supplies `authenticity_status` and
  `authenticity_reasons`.
- `app/services/critic.py` supplies pairwise comparison conclusions,
  comparability labels, evidence IDs/URLs, and inference flags.
- `app/services/reasoning.py` supplies missing fields, explanations, and
  follow-up actions.
- `app/services/synthesis.py` supplies key findings and candidate gaps.

## 3. Libraries and browser features used

The Evidence Ledger does not use a dedicated table, graph, citation, or UI
library. It uses the project’s existing frontend stack:

- React for components and JSX rendering;
- Vite for frontend bundling and development;
- standard JavaScript array methods such as `reduce`, `filter`, `flatMap`, and
  `map` for transforming API data;
- the native HTML `<details>` and `<summary>` elements for expandable ledger
  rows;
- native `<a>` links for source and DOI navigation; and
- CSS from `frontend/styles.css` for layout, borders, states, and animation.

The native `<details>` element provides expansion without adding state or a
third-party accordion dependency. The browser handles open/close behavior and
keyboard accessibility for the summary control.

## 4. Report inputs

`Results` extracts the relevant arrays from the API report:

```javascript
const papers = asList(report.papers);
const comparisons = asList(report.comparison);
const missing = asList(report.missing_information);
const gaps = asList(report.candidate_gaps);
```

It also passes:

```javascript
<EvidenceLedger
  findings={asList(report.key_findings)}
  gaps={gaps}
  comparisons={comparisons}
  missing={missing}
  papers={papers}
/>
```

The ledger therefore uses only the current report response. If an agent returns
an empty array, that category produces no ledger entries.

## 5. Core functions and their work

### `EvidenceLedger({ findings, gaps, comparisons, missing, papers })`

This is the feature’s main component. It performs four jobs:

1. creates a lookup map from paper IDs to paper records;
2. normalizes different result types into one internal ledger-entry shape;
3. renders every entry as an expandable record; and
4. shows explicit unavailable states when evidence is not returned.

The component does not call OpenAlex, Groq, or the backend directly. Data
retrieval remains the responsibility of the research pipeline.

### `paperMap`

```javascript
const paperMap = papers.reduce((map, paper) => {
  const id = paper.paper_id || paper.id;
  if (id) map[id] = paper;
  return map;
}, {});
```

This creates O(1)-style lookup by paper ID while rendering. It lets a finding
such as `paper_ids: ["W123"]` resolve to the paper title, source URL, DOI,
structured fields, and authenticity information.

### `paperIdsFor(item)`

This helper reads `item.paper_ids` and keeps only IDs that exist in
`paperMap`.

Why this matters:

- malformed or stale IDs do not create broken source rows;
- the ledger does not display a paper title it cannot resolve; and
- supporting evidence remains tied to actual records returned in the report.

### `sourceLinksFor(paperIds)`

For each resolved paper, this helper builds links from returned fields:

- `paper.url` becomes an OpenAlex/source link;
- `paper.doi` becomes a DOI link;
- a plain DOI is normalized to `https://doi.org/<doi>`;
- an already-qualified DOI URL is preserved.

The function returns link objects such as:

```javascript
{ label: "DOI", url: "https://doi.org/..." }
```

No URL is invented when neither `url` nor `doi` is present.

### `structuredEvidenceFor(paperIds)`

This helper converts structured paper fields into displayable evidence facts.
It reads:

- `methods`;
- `datasets`;
- `metrics`;
- `reported_results`; and
- `limitations`.

Each returned fact contains:

```javascript
{
  paperId,
  label,
  value
}
```

For example, a returned extractor value may become:

```text
Metrics: F1 score
```

Empty fields produce no fact. The UI then says that no structured extracted
evidence was returned instead of guessing from the title.

### `pageReferenceFor(item)`

This helper checks optional fields:

- `page_reference`;
- `page`;
- `table_reference`; and
- `figure_reference`.

These fields are displayed only when an upstream service supplies them. The
current extractor does not reliably produce page/table/figure references, so
the normal current state is an explicit message that no such reference was
returned.

### `asList(value)`

Defined near the top of `App.jsx`, `asList` returns an array only when the API
value is an array. Otherwise it returns `[]`.

This prevents errors such as calling `.map()` on `null`, a missing field, or a
malformed model response.

### `text(value, fallback)`

`text` returns a trimmed string or a supplied fallback. It also supports numeric
values. This keeps missing titles, explanations, IDs, and status values from
rendering as blank or throwing an exception.

## 6. Ledger entry types

The component converts four API categories into a common internal entry shape.

### A. Key finding

Source: `report.key_findings`

Displayed fields:

- `finding` or `title` as the claim;
- `explanation` or `reason`;
- `paper_ids` as supporting papers;
- structured evidence from those papers;
- `conflicting_paper_ids` as contradictions;
- `uncertainty` or `confidence`; and
- `inference` to choose the provenance label.

If no explicit inference flag exists, the UI labels the item as model synthesis
from retrieved records rather than claiming it is a direct quotation from a
paper.

### B. Comparison conclusion

Source: `report.comparison`

Displayed fields:

- `finding` or `reason` as the conclusion;
- `paper_ids` as the compared papers;
- extracted evidence from each paper;
- `comparability` and `inference` context;
- paper IDs as conflicts when the item is
  `not_directly_comparable`; and
- uncertainty explaining that potential comparability is not direct proof.

This is important because a comparison warning is itself an evidence-bearing
conclusion. The ledger makes the warning traceable to the pair of papers.

### C. Candidate gap

Source: `report.candidate_gaps`

Displayed fields:

- `title` or `description` as the candidate gap;
- `description` or `explanation`;
- any returned supporting paper IDs;
- `uncertainty` or `confidence`; and
- candidate-inference provenance.

The label “Candidate inference” is deliberate. A gap in the retrieved set is
not proof that nobody has studied the topic.

### D. Missing-information signal

Source: `report.missing_information`

Displayed fields:

- missing field name;
- `reason`;
- the associated paper ID and title;
- missing field list;
- `follow_up_action` or `follow_up_search`; and
- source/authenticity data when the paper can be resolved.

This entry means the field was not available in the retrieved structured data.
It does not mean that the source paper itself lacks that information.

## 7. Internal normalized entry shape

Every category is converted into an object with the same presentation shape:

```javascript
{
  kind,
  claim,
  explanation,
  paperIds,
  evidence,
  references,
  sourceLinks,
  provenance,
  contradictions,
  uncertainty,
  missing,
  followUp
}
```

This normalization allows one renderer to display findings, comparisons, gaps,
and missing-information signals consistently.

## 8. Complete workflow

```text
User asks a question
        |
        v
POST /api/research
        |
        v
Discovery returns paper records
        |
        v
Extractor adds structured fields
        |
        v
Authenticity agent adds status/reasons
        |
        v
Critic, reasoning, and synthesis return report arrays
        |
        v
Results receives report
        |
        v
EvidenceLedger builds paperMap
        |
        v
Each conclusion is normalized into a ledger entry
        |
        v
User expands <details> row
        |
        v
UI shows claim, sources, evidence, provenance,
uncertainty, conflicts, missing fields, and follow-up
```

### Step-by-step behavior

1. The user submits a question from the React frontend.
2. The API runs discovery, extraction, verification, comparison, reasoning,
   and synthesis.
3. The API returns one report object containing papers and agent outputs.
4. `Results` safely converts optional arrays with `asList`.
5. `EvidenceLedger` creates `paperMap` from returned paper IDs.
6. Findings, comparisons, gaps, and missing-information items are transformed
   into normalized entries.
7. The component filters entries without a claim.
8. Each valid entry renders as a native expandable `<details>` element.
9. When the user expands a row, the UI resolves source links and evidence from
   the corresponding paper records.
10. Missing data is shown with an explicit unavailable message.
11. External source links open in a new tab with `rel="noreferrer"`.

## 9. What is source-reported versus inferred

The ledger distinguishes provenance instead of presenting every sentence as a
direct paper fact.

| Item | Ledger provenance |
|---|---|
| Key finding with `inference: true` | Inferred |
| Key finding without explicit inference metadata | Model synthesis from retrieved records |
| Comparison with `inference: true` | Inferred |
| Comparison without inference | Source-reported comparison |
| Candidate research gap | Candidate inference |
| Missing metadata record | Source-reported metadata limitation |

The distinction is a UI explanation of the returned fields. It is not a claim
that the model is perfectly reliable.

## 10. Authenticity handling

The ledger does not perform authenticity verification itself. It displays the
result produced by `verify_papers`:

- `verified`;
- `partially_verified`; or
- `unverified`.

It also displays `authenticity_reasons` when available. A failure to match a
paper is shown as unverified, not as proof that the paper is fake.

## 11. Styling and interaction behavior

The CSS provides:

- bordered cards for each entry;
- a numbered entry index;
- kind labels such as “Key finding” and “Candidate gap”;
- a plus/minus indicator through `summary::after`;
- two-column evidence sections on wide screens;
- responsive wrapping for source links;
- visual emphasis for uncertainty and unavailable values; and
- a short open animation using the existing `loading-enter` keyframe.

The actual expand/collapse behavior comes from native HTML, not JavaScript
state.

## 12. Why this design was chosen

### No extra UI dependency

The feature is a read-only disclosure view. Native `<details>` gives keyboard-
friendly expansion with very little code and no dependency or state-sync cost.

### Derived data instead of hardcoded content

All paper titles, claims, evidence values, links, statuses, and warnings come
from the report response. This allows the same component to work for different
questions and different API results.

### Graceful missing-data behavior

Research metadata is incomplete by nature. Showing “not returned” is more
trustworthy than hiding the gap or inferring a value.

### One normalized renderer

Findings, comparisons, candidate gaps, and missing-information items have
different API shapes. Normalizing them first keeps the UI consistent and makes
future report categories easier to add.

## 13. Current limitations

- The evidence ledger can only show fields present in the API response.
- The current extraction pipeline does not guarantee page/table/figure
  references.
- The synthesis model may return findings without `paper_ids`; those entries
  explicitly show that no supporting paper IDs were returned.
- The ledger displays authenticity status, but it does not independently
  validate the scientific claims in a paper.
- The evidence facts are structured summaries, not full quoted passages.
- There is currently no backend persistence for manually annotated evidence.

## 14. Future improvements

Possible next steps, without changing the evidence-first principle:

1. Add page-aware extraction so every fact can point to a PDF page.
2. Store short source excerpts with offsets and document hashes.
3. Ask synthesis to return a strict evidence-reference schema for every finding.
4. Add paper-level filters for dataset, metric, authenticity, and comparability.
5. Add export to Markdown, JSON, BibTeX, or a review checklist.
6. Add user annotations and reviewer approval without overwriting source data.
7. Add automated citation-link and unsupported-claim evaluations.

## 15. Short presentation explanation

> The Evidence Ledger is our explainability layer. Every important conclusion
> can be expanded to show which retrieved papers support it, what structured
> evidence was extracted, whether the statement is reported or inferred, what
> verification status the papers have, and what remains uncertain. It is built
> with React and native HTML disclosure elements, so it stays lightweight and
> all displayed content comes from the live research report rather than
> hardcoded demo data.
