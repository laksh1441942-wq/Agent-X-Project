# ResearchPilot AI — Presentation Brief

This document is a presentation-ready explanation of ResearchPilot. It is
written from the current source code, so it separates implemented behavior
from future product ideas.

## 1. One-line explanation

ResearchPilot is an evidence-grounded research assistant that turns a natural-
language research question into a traceable literature review: real paper
records, bibliographic verification, structured evidence extraction, cautious
cross-paper comparison, missing-information analysis, and a source-linked
report.

## 2. The real-world problem

Researchers, analysts, students, and technical teams spend a large amount of
time doing repetitive literature-review work:

- finding relevant papers across a large and constantly growing literature;
- checking whether a paper's title, DOI, authors, and source record are real;
- extracting methods, datasets, metrics, results, and limitations;
- comparing papers that may use incompatible datasets or evaluation protocols;
- identifying what the retrieved evidence does not tell us; and
- keeping a defensible trail from a conclusion back to its sources.

The dangerous failure mode is not only missing a paper. It is producing a
confident but unsupported synthesis: treating a search result as truth,
comparing incompatible scores, or presenting an LLM-generated citation that
does not exist.

ResearchPilot addresses the workflow and traceability problem. It does not
claim to replace expert judgment, prove scientific truth, or prove novelty.

## 3. Product value proposition

ResearchPilot aims to make early-stage research review faster and safer:

1. Ask a question in plain language.
2. Retrieve candidate papers from OpenAlex.
3. Normalize and deduplicate the records.
4. Enrich them with PDF/abstract extraction and structured fields.
5. Verify bibliographic metadata independently.
6. Compare evidence without ranking incompatible experiments.
7. Show missing information and uncertainty.
8. Produce an expandable evidence ledger with source links and provenance.

The central value is not simply “an AI summary.” It is a reviewable chain of
evidence around the summary.

## 4. Current architecture

```text
React/Vite frontend
        |
        | POST /api/research
        v
Python HTTP API (app/api.py)
        |
        v
Research pipeline
  1. Paper Discovery       -> OpenAlex
  2. Paper Extractor       -> PDF/abstract + pypdf + Groq
  3. Authenticity Checker  -> OpenAlex metadata lookup
  4. Critic                -> deterministic comparability checks
  5. Reasoning             -> missing-information analysis
  6. Synthesis             -> Groq structured report
        |
        v
Frontend report
  summary, findings, papers, comparisons, gaps,
  warnings, agent trace, evidence ledger
```

### Main implementation files

- `app/api.py`: API routes and orchestration in `build_report`.
- `app/services/paper_discovery.py`: OpenAlex search, normalization, ranking,
  deduplication, and abstract reconstruction.
- `app/services/paper_extractor.py`: PDF download, `pypdf` text extraction,
  and Groq structured-field extraction.
- `app/services/search_authenticity.py`: title/DOI metadata matching against
  OpenAlex.
- `app/services/critic.py`: deterministic pairwise comparison and
  comparability warnings.
- `app/services/reasoning.py`: missing structured information and follow-up
  actions.
- `app/services/synthesis.py`: Groq-backed summary, findings, and candidate
  gaps.
- `frontend/src/App.jsx`: research UI, loading animation, results, source
  drawer, and evidence ledger.
- `frontend/src/api/client.js`: request timeout, validation, and network error
  handling.

## 5. Agent pattern and design pattern

### Multi-agent pipeline

Each agent has one responsibility and returns a common shape:

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

This creates separation of concerns. Discovery does not decide authenticity;
authenticity does not judge scientific truth; the critic does not invent
missing values; and synthesis receives the evidence already collected by the
other stages.

### Important software patterns

**Contract-first orchestration.** The API freezes the report shape and passes
structured outputs between stages.

**Deterministic checks around probabilistic models.** OpenAlex normalization,
deduplication, metadata matching, comparability rules, and missing-field checks
are ordinary Python logic. Groq is used for extraction and language synthesis,
not as the only source of truth.

**Evidence-bound generation.** The synthesis prompt receives only normalized
papers, comparison results, missing-information items, and warnings. It is
explicitly instructed not to invent papers, quotes, metrics, citations, or
certainty.

**Graceful degradation.** If Groq, OpenAlex, a PDF, or a source link fails,
the system retains the evidence it does have and returns a structured warning
instead of fabricating a successful answer.

**Progressive disclosure.** The UI shows the concise report first, then lets a
user expand the evidence ledger or open a source drawer for details.

## 6. Models and external systems

### OpenAlex

Used for:

- literature search;
- title, DOI, author, year, abstract, and source metadata;
- bibliographic verification.

OpenAlex metadata matching does not prove that the paper's scientific claims
are true.

### Groq-hosted language model

The current code uses the model configured by `GROQ_MODEL`, defaulting to:

```text
openai/gpt-oss-120b
```

Groq is used for two bounded tasks:

1. extracting methods, datasets, metrics, reported results, and limitations
   from paper text;
2. synthesizing the already-collected evidence into a summary, findings, and
   candidate gaps.

The model is not used to search the web, make up paper records, or determine
whether a bibliographic record is authentic.

### pypdf

Used to extract text from downloaded PDFs. If a PDF cannot be downloaded or
parsed, the extractor falls back to the title and abstract when available.

### Frontend and API

- React with Vite for the interface.
- Python standard-library HTTP server for the local API.
- `certifi` CA bundle for TLS verification.

## 7. End-to-end request lifecycle

The request enters at `POST /api/research` with a question and optional paper
limit.

### Step 1: Discovery

The discovery agent validates the question, calls OpenAlex, reconstructs an
abstract when OpenAlex supplies an inverted index, removes duplicates by DOI or
normalized title/year, and ranks candidates using transparent token overlap
with the question plus OpenAlex relevance.

### Step 2: Extraction

For each paper, the extractor attempts to download a PDF, extracts text with
`pypdf`, and asks Groq for five structured fields. Missing fields remain empty;
the model is instructed not to infer values that are not explicitly present.

### Step 3: Authenticity

Each paper is checked by DOI or title against OpenAlex. The result is:

- `verified`: matching bibliographic metadata;
- `partially_verified`: a record was found but metadata differs or is limited;
- `unverified`: no match or lookup failure.

“Unverified” means “not verified by this check,” not “definitely fake.”

### Step 4: Critic

The critic compares paper pairs across dataset, metric, result, protocol, and
baseline fields. It returns:

- `potentially_comparable` when reported setup appears aligned;
- `not_directly_comparable` when datasets, metrics, protocols, or baselines
  differ;
- `insufficient_information` when required fields are missing.

It never ranks scores from incompatible experiments as if they were directly
comparable.

### Step 5: Reasoning

The reasoning agent identifies fields absent from the retrieved structured
records and gives a follow-up action. It describes an information gap in the
retrieved evidence; it does not claim that the original paper lacks the field.

### Step 6: Synthesis

Groq receives only the evidence returned by the pipeline and returns a bounded
JSON structure containing a summary, key findings, and candidate gaps.

### Step 7: Presentation

The frontend displays the report, warnings, agent trace, source records, paper
drawer, and evidence ledger. The loading view communicates the pipeline while
the request is running.

## 8. Evidence ledger and explainability

The evidence ledger is the main “wow factor.” Each returned conclusion can be
expanded to inspect:

- the conclusion itself;
- supporting paper IDs and titles;
- source and DOI links;
- extracted methods, datasets, metrics, results, and limitations;
- whether the item is source-reported, model-synthesized, or inferred;
- authenticity status and verification reasons;
- contradictions or incomparable paper pairs;
- missing information and uncertainty;
- page/table/figure references when the API provides them; and
- follow-up actions when the API provides them.

If the API does not provide a value, the UI says it is unavailable. The UI
does not fill evidence gaps with placeholder papers or invented citations.

## 9. Evaluation strategy — evals

Evaluation should cover both correctness and safety. A good demo should not
only show a fluent answer; it should show that unsafe conclusions are blocked
or labelled.

### Current automated coverage

The repository includes tests for:

- API report composition and health routing;
- OpenAlex normalization, ranking, deduplication, abstract reconstruction,
  invalid input, and network failures;
- TLS context usage and search-query sanitization;
- DOI and title authenticity matching;
- lookup failures and malformed authenticity records;
- critic handling of missing fields and incomparable datasets;
- reasoning detection of missing metadata;
- synthesis parsing and unavailable-model behavior.

### Recommended evaluation matrix

| Capability | Test case | Expected behavior |
|---|---|---|
| Retrieval | A narrow research question | Returns real OpenAlex records or a structured error |
| Deduplication | Same DOI in two records | Keeps one best-ranked record |
| Authenticity | Matching DOI | `verified` with reasons |
| Authenticity | No match or timeout | `unverified`, warning, no fake confidence |
| Comparison | Different datasets | `not_directly_comparable` |
| Comparison | Missing metrics | `insufficient_information` |
| Reasoning | Empty datasets field | Reports missing retrieved metadata plus follow-up |
| Synthesis | Malformed model JSON | Synthesis error; underlying evidence remains |
| Provenance | Finding with paper IDs | Ledger exposes source links and extracted fields |
| No fabrication | No abstract/DOI | Shows unavailable, never invents a value |
| Frontend resilience | API unavailable | User sees a clear error and can retry |

### Metrics to add for a production evaluation set

- retrieval precision@k and recall@k against a manually curated paper set;
- DOI/title verification precision;
- field extraction precision and recall for methods, datasets, metrics, and
  results;
- comparability classification accuracy against expert labels;
- citation/source-link validity rate;
- unsupported-claim rate in generated findings;
- percentage of conclusions with traceable paper IDs;
- structured-error coverage across external-service failures; and
- latency and cost per completed research question.

### Human evaluation

Experts should score each report for relevance, factual support, uncertainty
calibration, comparability safety, usefulness of follow-up actions, and ease of
source verification.

## 10. Failure and error handling

Research systems operate across unreliable networks, incomplete metadata,
unavailable PDFs, and imperfect model responses. ResearchPilot treats these as
normal states.

### Discovery failures

OpenAlex HTTP errors, timeouts, URL errors, operating-system errors, and
malformed JSON become structured agent errors. The system does not substitute
invented papers.

### PDF failures

An inaccessible or non-PDF source is skipped. The extractor falls back to the
abstract and reports when structured extraction is unavailable.

### Groq failures

Missing API keys, timeouts, malformed JSON, and API errors produce a synthesis
or extraction warning. The report still includes deterministic discovery,
verification, comparison, and reasoning outputs where available.

### Metadata failures

Missing DOI, abstract, authors, metrics, or results stay empty or unavailable.
The reasoning agent labels the gap as absent from retrieved metadata rather
than claiming that the source paper lacks the information.

### Comparability failures

Different datasets, metrics, protocols, or baselines produce warnings and
`not_directly_comparable` instead of a misleading ranking.

### Frontend failures

The client distinguishes validation, server, timeout, invalid-response, and
network errors. The user can return to the question and retry. The animated
loading view makes the long-running workflow visible without pretending that
the backend has completed.

## 11. Business potential

### Potential customers

- research and development teams evaluating a new technical area;
- universities and academic research groups;
- consulting and competitive-intelligence teams;
- pharmaceutical, medical-device, and biotech research teams;
- legal and policy teams performing evidence discovery; and
- enterprises creating internal knowledge and technology landscapes.

### Product opportunities

- saved research workspaces and history;
- team annotations and review workflows;
- organization-specific source connectors;
- citation export to BibTeX, Word, or reference managers;
- monitored research topics and alerts when new papers appear;
- private deployment for confidential research;
- expert review and approval before a report is shared; and
- audit logs showing exactly which sources and model version produced a report.

### Business model options

- usage-based API or report credits;
- per-seat team subscriptions;
- enterprise annual contracts with private data boundaries;
- premium connectors and monitoring;
- managed research-review workflows; or
- API licensing for existing knowledge platforms.

The strongest commercial differentiation is defensible traceability and safe
comparisons, not generic text generation.

## 12. Scalability plan

### Current prototype limits

- local Python threaded HTTP server;
- synchronous-style orchestration around asynchronous functions;
- OpenAlex as the primary discovery source;
- one request runs the full workflow;
- PDF and model work can be slow;
- no authentication, persistence, job queue, or rate-limit layer; and
- the current evidence is limited by source coverage and PDF access.

### Recommended production architecture

```text
API gateway + authentication
          |
          v
Research job service -> queue (Redis/SQS/Kafka)
          |
          +-> discovery workers
          +-> PDF extraction workers
          +-> model workers
          +-> verification/comparison workers
          |
          v
Postgres: reports, papers, provenance, job state
Object storage: PDFs and extracted artifacts
Vector/search index: reusable paper chunks and semantic retrieval
          |
          v
Frontend/report API + observability
```

### Scaling techniques

- queue long-running research jobs instead of holding an HTTP request open;
- run paper extraction concurrently with bounded worker pools;
- cache OpenAlex records, PDFs, extracted text, and model results;
- deduplicate papers globally by DOI and stable source ID;
- add provider fallbacks and retries with exponential backoff;
- use streaming job status updates through polling or WebSockets;
- enforce per-user quotas and external API rate limits;
- separate tenant data and encrypt stored documents;
- version prompts, models, and extraction schemas;
- log provenance and latency for every pipeline stage; and
- add human approval for high-impact or regulated use cases.

### Cost controls

- use cheap deterministic filtering before sending text to a model;
- summarize or chunk long papers selectively;
- cache extraction by paper hash and model version;
- use smaller models for classification and larger models only for synthesis;
- cap PDF size and extracted text length; and
- expose estimated cost and latency to enterprise users.

## 13. Security, privacy, and responsible use

The prototype should not be presented as a fully secured production system.
Production work must add authentication, authorization, tenant isolation,
secret management, encrypted storage, retention controls, prompt-injection
defenses for retrieved documents, and audit logs.

Users should understand that:

- metadata verification is not scientific validation;
- OpenAlex coverage is not comprehensive;
- PDF extraction can misread tables and figures;
- language models can still make extraction or synthesis mistakes; and
- candidate research gaps are not proof of novelty.

## 14. Suggested live demo

Use one narrow question such as:

> Compare deepfake detection methods, datasets, metrics, and limitations.

Show the following sequence:

1. Enter the question.
2. Show the animated discovery and processing pipeline.
3. Show three to five live paper records.
4. Open a paper and show authenticity status and reasons.
5. Open the evidence ledger for a finding.
6. Show a comparison warning for incompatible datasets or metrics.
7. Show missing information and its follow-up action.
8. Open a real source link.
9. Show the agent trace and warnings.

If external APIs are unavailable, the application should show its structured
error state. Any future demo fallback must be explicitly labelled as demo data
and must never appear to be live retrieval.

## 15. Judge Q&A answers

### How do you detect fake papers?

We match a paper's DOI or title against OpenAlex. A match produces a verified
bibliographic status; no match produces unverified. Unverified does not mean
the paper is definitely fake, and metadata matching does not prove scientific
truth.

### How do you reduce hallucinations?

We use structured outputs, deterministic checks, source-linked evidence,
explicit unknown values, bounded prompts, and critic warnings. These reduce risk
but do not eliminate model error.

### Why multiple agents?

Each stage has a narrow responsibility and a testable output contract. This
makes failures inspectable and prevents one model call from silently performing
retrieval, verification, comparison, and synthesis all at once.

### Can all results be compared fairly?

No. Different datasets, metrics, protocols, and baselines may make direct
comparison invalid. The critic explicitly flags those cases.

### What are the limitations?

Coverage depends on OpenAlex and accessible full text. Metadata is not
scientific validation. PDF extraction may miss tables or figures. LLM
extraction may be wrong. Candidate gaps need human verification.

## 16. Current implementation truth

- The API endpoint is `POST /api/research`.
- Health check is `GET /api/health`.
- The active model integration in code is Groq, configured by `GROQ_API_KEY`
  and `GROQ_MODEL`.
- The frontend uses live API responses and does not include fixture paper data.
- The frontend build currently passes with `npm run build`.
- The Python test suite contains older expectations around the previous Ollama
  integration and currently requires test maintenance before it can be called
  fully green. This should be fixed before presenting a final test result.

## 17. Strong closing statement

ResearchPilot is a research copilot designed around a simple principle:
use AI to accelerate evidence work, but make every important conclusion
inspectable, qualified, and connected to the records that support it.
