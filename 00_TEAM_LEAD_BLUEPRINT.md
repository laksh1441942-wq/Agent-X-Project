# ResearchPilot AI — Team Blueprint (Read First)
**Deadline:** October 28. **Owner:** Team lead/integrator.

## Product
ResearchPilot is a multi-agent research assistant that discovers papers, checks bibliographic authenticity, compares evidence critically, identifies missing information, and presents a traceable report. This is a prototype: never claim that metadata checks prove scientific truth or that candidate gaps prove novelty.

## Team roles
1. Team lead: schemas, orchestrator, FastAPI app, integration and final demo.
2. Search & Authenticity Agent: paper search, metadata normalization and verification status.
3. Critic Agent: compare methods/results, flag contradictions and incomparable experiments.
4. Reasoning Agent: identify missing/uncertain information and follow-up questions.
5. Frontend: interactive dashboard showing papers, agent stages, evidence, warnings and report.

## Stack: minimize risk
Python 3.11/3.12, FastAPI, Pydantic, OpenAlex API, one existing LLM provider behind a small wrapper, pytest. React + Vite is fine if the frontend owner can manage it; otherwise use plain HTML/CSS/JS. Start without vector DB, Docker, authentication or complex agent frameworks. Agents may be Python functions with separate prompts and responsibilities; separate models are not required. Include a fallback demo fixture if network/API keys fail.

## Workflow
Question → Research Manager → Search & Authenticity → Critic Comparison → Reasoning/Missing Information → Synthesis → Frontend report. The first working version should handle only 3–5 papers end-to-end.

## Shared contract — coordinate before changing
Paper record:
```json
{
  "paper_id":"string",
  "title":"string",
  "authors":["string"],
  "year":2024,
  "abstract":"string",
  "doi":null,
  "url":"https://...",
  "source":"OpenAlex/arXiv/demo",
  "authenticity_status":"verified/partially_verified/unverified",
  "authenticity_reasons":["string"],
  "methods":["string"],
  "datasets":["string"],
  "metrics":["string"],
  "reported_results":["string"],
  "limitations":["string"],
  "missing_information":["string"]
}
```
Agent output:
```json
{"agent_name":"string","status":"success/partial/error","summary":"string","items":[],"warnings":[],"sources":[]}
```
Final report:
```json
{"research_question":"string","papers":[],"comparison":[],"missing_information":[],"candidate_gaps":[],"warnings":[],"agent_trace":[]}
```
Use empty arrays for absent lists; use null for unknown single values. Never invent paper titles, DOIs, citations, metrics, results or quotes.

## API contract
- `GET /api/health` → `{"status":"ok"}`
- `POST /api/research` with `{"question":"...","max_papers":5}` → final report
- Optional `GET /api/demo` → clearly labelled deterministic demo data.
Team lead owns `app/main.py`, `app/schemas.py`, `app/orchestrator.py`. Contributors should expose functions/modules and not create competing FastAPI apps.

## Suggested structure
```text
app/main.py
app/schemas.py
app/orchestrator.py
app/services/search_authenticity.py
app/services/critic.py
app/services/reasoning.py
app/prompts/
frontend/
tests/
README.md
requirements.txt
.env.example
```
Adapt to the existing repo; do not restructure without agreement.

## Git and merge rules
- Branch names: `feat/authenticity-agent`, `feat/critic-agent`, `feat/reasoning-agent`, `feat/frontend-dashboard`, `feat/orchestration`.
- Contributors must edit only their assigned files. Do not edit `main.py`, `schemas.py`, or `orchestrator.py` unless asked.
- Push small commits. Merge one branch at a time and test after each merge.
- Never commit `.env`, API keys, virtualenvs, generated build folders, or private data.
- If you need to change a field name or API endpoint, tell the team lead first.
- Keep every commit importable; incomplete work should return a valid stub response.

## Coding AI prompt for every teammate
> First inspect the existing repo and README. Follow this blueprint and shared contract. Implement only my assigned files; do not rewrite unrelated files or assume dependencies exist. Keep code simple, typed where practical, and error-handled. Never fabricate research data or citations. Add a basic test or manual test instructions. Update my module README with actual implementation, changed files, setup/run commands, actual test result, limitations and next step. Do not claim tests passed unless you ran them. Finish by listing every changed file.

## README rule
After each meaningful commit, update the root or module README with what changed, files touched, how to run/test, actual result (`pass`, `fail`, or `not run`), known limitations, and next step. Never fabricate a development history or test results.

## Four-day plan
**Oct 24:** skeleton, shared schemas, health endpoint, agree interfaces, first branch merged.
**Oct 25:** search/authenticity + critic + reasoning modules return structured outputs.
**Oct 26:** connect complete API and frontend; test missing fields and API failures.
**Oct 27:** freeze interfaces, fix bugs, rehearse demo.
**Oct 28:** demo only; avoid major refactors.

## Integrity boundaries
- `unverified` means not independently matched in sources checked, not “fake.”
- Metadata existence does not prove research findings are true.
- A research gap is a candidate in the retrieved/analyzed literature, not proof nobody studied it.
- Do not rank results across different datasets or metrics without warning.
- Show each agent’s responsibility, input/output and trace in the UI; multiple prompts alone do not prove useful multi-agent behavior.
