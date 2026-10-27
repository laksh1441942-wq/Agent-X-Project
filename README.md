# ResearchPilot AI

ResearchPilot is a multi-agent research assistant prototype. It is designed to
discover papers, check bibliographic metadata, compare evidence, identify
missing information, and present a traceable report. Metadata checks do not
prove scientific truth, and candidate gaps do not prove novelty.

## Current implementation

The implemented service slices are:

- Paper Discovery Agent in `app/services/paper_discovery.py`;
- Search & Authenticity Agent in `app/services/search_authenticity.py`;
- Critic Agent in `app/services/critic.py`; and
- Reasoning Agent in `app/services/reasoning.py`; and
- Ollama Synthesis Agent in `app/services/synthesis.py`.

The Paper Discovery Agent:

- searches OpenAlex with a timeout;
- normalizes source metadata into the shared paper-record shape;
- reconstructs abstracts when OpenAlex provides an inverted index;
- removes duplicates by DOI or normalized title and year;
- ranks candidates by unique non-stopword overlap with title/abstract, then
  OpenAlex relevance score; and
- returns structured warnings/errors without inventing missing metadata.

The Critic Agent compares reported datasets, metrics, protocols, baselines, and
results pairwise. It explicitly marks missing information and incomparable
experiments rather than ranking scores across incompatible studies. The
Reasoning Agent flags absent structured fields and treats candidate gaps as
limits of the retrieved literature, not proof of novelty.

The Search & Authenticity Agent checks each discovered paper's title or DOI
against OpenAlex and updates the paper record with `verified`,
`partially_verified`, or `unverified` status. This is bibliographic metadata
verification only; it does not establish that a paper's scientific claims are
true. Its public entry point is `verify_papers`, with `check_authenticity` kept
as a compatibility alias for orchestration code.

The module is importable without starting a server. HTTP requests use Python's
standard library with the `certifi` CA bundle for reliable TLS verification.

The Ollama Synthesis Agent receives only the normalized papers, comparison
results, missing-information items, and warnings produced by the other agents.
It uses a local Ollama chat endpoint to return a structured summary, key
findings, and candidate gaps. Its system prompt forbids invented sources,
quotes, metrics, and certainty. Configure the local runtime with the ignored
`.env` file using the tracked [`.env.example`](.env.example) template:

```env
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=120
```

Start Ollama and download the model once with `ollama serve` and
`ollama pull qwen2.5:7b`. Without Ollama, the API keeps the deterministic agent
outputs and reports local synthesis as unavailable; it does not fabricate an
LLM response.

## Frontend workspace

The React frontend source lives in [`frontend/src/App.jsx`](frontend/src/App.jsx),
[`frontend/src/main.jsx`](frontend/src/main.jsx), and [`frontend/styles.css`](frontend/styles.css).
It provides the research input, API-backed loading and error states, response-
driven paper evidence, comparison view, missing-information review, agent
trace, warnings, and source drawer. It posts real questions to
`POST /api/research` using the shared blueprint contract. Unsupported backend
capabilities are shown as unavailable rather than replaced with fixture data.

Run the frontend locally with:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://127.0.0.1:4173/`. Vite proxies `/api` requests to the local
API on port `8010`.

## Run and test

Use Python 3.11 or 3.12 as specified by the team blueprint:

```bash
python3 -m pip install -r requirements.txt
python3 -m compileall -q app tests
python3 -m pytest -q
```

Start the API and frontend in separate terminals:

```bash
python3 run.py
cd frontend
npm run dev
```

The API exposes `GET /api/health` and `POST /api/research`. The frontend reports
network, timeout, validation, and invalid-response errors when the API is
unavailable.

Build the frontend for production with `npm run build` from `frontend/`. The
test suite includes the API orchestration and health endpoint. Actual result:
**pass** - 17 Python tests passed locally. Critic validation also passed with a
direct smoke test for incomparable datasets.

## Limitations and next step

Discovery and authenticity currently use OpenAlex and do not establish
scientific validity or comprehensive literature coverage. Authenticity lookup
failures preserve the paper as `unverified` and return a structured warning.
Network failures return a structured error. Research history and saved
research are not implemented. Without Ollama, executive summary, key-finding,
and candidate-gap synthesis are unavailable. The local API wires discovery,
authenticity, critic, reasoning, and Ollama synthesis outputs into the
frontend report contract; a production deployment would still need
authentication, persistence, and a production-grade server.
