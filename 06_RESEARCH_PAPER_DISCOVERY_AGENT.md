# ResearchPilot AI — Research Paper Discovery Agent

**Role:** Find relevant academic papers from trusted scholarly sources and rank them by relevance.  
**Suggested branch:** `feat/paper-discovery`  
**Own:** `app/services/paper_discovery.py`, related tests, and optionally `docs/paper_discovery.md`.  
**Do not edit:** `app/main.py`, `app/schemas.py`, `app/orchestrator.py`, or frontend files unless the team lead asks.

## 1. Mission

Build the component that takes a research question, searches scholarly metadata sources, removes duplicates, ranks papers by relevance, and returns normalized paper records for the Authenticity Agent to check.

**Keep responsibilities separate:**
- Discovery Agent: finds and ranks papers.
- Authenticity Agent: checks whether bibliographic metadata can be independently matched against trusted sources.
- Critic Agent: compares research evidence and flags invalid comparisons.

A paper being found in a database does not prove its claims are scientifically correct.

## 2. Suggested interface

Coordinate the final function name with the team lead. Suggested interface:

```python
async def discover_papers(question: str, max_papers: int = 5) -> dict:
    ...
```

Return the shared `Agent output` shape from `00_TEAM_LEAD_BLUEPRINT.md`:

```json
{
  "agent_name": "paper_discovery",
  "status": "success",
  "summary": "Short explanation of search results",
  "items": [],
  "warnings": [],
  "sources": []
}
```

Each item should use the shared Paper record fields where possible:

```json
{
  "paper_id": "stable source ID",
  "title": "Actual title returned by source",
  "authors": ["Actual author names, if available"],
  "year": 2024,
  "abstract": "Actual abstract, if available",
  "doi": null,
  "url": "Actual source URL",
  "source": "OpenAlex",
  "authenticity_status": "unverified",
  "authenticity_reasons": [],
  "methods": [],
  "datasets": [],
  "metrics": [],
  "reported_results": [],
  "limitations": [],
  "missing_information": []
}
```

Use real values returned by the source. Leave unavailable values empty or null. Do not fabricate metadata.

## 3. Recommended sources

Start with **OpenAlex**. Add arXiv only after the first source works reliably.

- OpenAlex API docs: https://docs.openalex.org/
- arXiv API docs: https://info.arxiv.org/help/api/index.html

Use HTTP requests with timeouts and handle API errors. Do not make the demo depend on every source being available.

## 4. Minimum implementation

1. Accept a research question and maximum number of papers.
2. Convert the question into one or more focused search phrases. A simple keyword-based approach is acceptable for the first version; an LLM-generated query expansion is optional.
3. Search OpenAlex and retrieve real metadata.
4. Normalize title, authors, year, abstract, DOI, URL, source and stable ID.
5. Deduplicate by DOI when present, otherwise by normalized title plus year.
6. Rank results using a transparent simple method, such as title/abstract keyword overlap or source relevance score. Do not invent a relevance score if you cannot explain how it was calculated.
7. Return the top `max_papers` records and a short explanation of the ranking method.
8. Preserve the original source URL and search source for every result.
9. Handle no results, missing abstracts, rate limits, malformed responses, and timeouts.
10. Return a warning when only partial results are available.

## 5. Relevance and integrity rules

- Search results are candidates, not guaranteed relevant papers.
- Do not call a paper fake because it was not returned by a search API.
- Do not label a paper verified; pass it to the Authenticity Agent.
- Do not invent titles, authors, DOIs, URLs, abstracts, metrics, or results.
- Avoid claiming comprehensive coverage: report which source(s) were searched.
- If full text is unavailable, do not pretend you extracted its methods or results.
- If the source API fails, return a structured warning instead of crashing the entire workflow.

## 6. Coding-AI prompt — copy and paste

> You are implementing only ResearchPilot AI's Research Paper Discovery Agent. First inspect the existing repository, README, and `00_TEAM_LEAD_BLUEPRINT.md`. Do not assume files or dependencies exist. Implement `discover_papers(question, max_papers=5)` in `app/services/paper_discovery.py`, adapting only if the team lead has approved a different structure. Use OpenAlex as the first academic source and add arXiv only if the first integration is stable. Make real HTTP requests with timeouts and robust error handling. Normalize real source metadata into the shared Paper record, deduplicate results, and rank by a simple documented relevance method. Preserve source URLs and explain the ranking method. Never invent paper metadata or claim that discovery proves authenticity. Return the shared Agent output contract. Do not edit `main.py`, `schemas.py`, `orchestrator.py`, or frontend files. Add basic tests or manual test steps. Update a module README with actual changes, dependencies, run/test instructions, actual test results, limitations, and next step. Before finishing, list every changed file and any dependency changes. Do not claim tests passed unless you ran them.

## 7. Tests to perform

- A real query returns normalized records when network access is available.
- Empty results return a valid empty response.
- Timeout or HTTP error returns a warning instead of an unhandled exception.
- Missing DOI/abstract is handled without guessing.
- Duplicate papers are removed.
- `max_papers` is respected.
- Every URL comes from the API response.
- The output can be passed to the Authenticity Agent without renaming fields.

## 8. Definition of done

- The function imports without starting a server.
- The output matches the shared contract.
- At least one real search has been tested if network access is available.
- The README records what was actually implemented and tested.
- Limitations and next steps are explicit.

## 9. Important coordination note

This agent owns discovery and relevance ranking only. Do not duplicate the Authenticity Agent's metadata-verification logic. The team lead integrates this function into `app/orchestrator.py`.
