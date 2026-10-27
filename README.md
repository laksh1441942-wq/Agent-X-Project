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
- Reasoning Agent in `app/services/reasoning.py`.

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

## Run and test

Use Python 3.11 or 3.12 as specified by the team blueprint:

```bash
python3 -m pip install -r requirements.txt
python3 -m compileall -q app tests
python3 -m pytest -q
```

Start the integrated API and frontend in separate terminals:

```bash
python3 run.py
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).
The Vite development server proxies `/api` requests to the Python API on
`http://127.0.0.1:8010`. Set `RESEARCHPILOT_PORT` to use another available
port, and set `RESEARCHPILOT_API_URL` before starting Vite when the API uses a
non-default port. The API exposes `GET /api/health` and
`POST /api/research`.

The test suite includes the API orchestration and health endpoint. Frontend
assets can be validated with:

```bash
cd frontend
npm run build
npm run lint
```

Actual result: **pass** - 13 Python tests passed locally. Critic validation
also passed with a direct smoke test for incomparable datasets.

## Limitations and next step

Discovery and authenticity currently use OpenAlex and do not establish
scientific validity or comprehensive literature coverage. Authenticity lookup
failures preserve the paper as `unverified` and return a structured warning.
Network failures return a structured error and no fallback fixture has been
connected yet. The local API now wires discovery, authenticity, critic, and
reasoning outputs into the frontend report contract; a production deployment
would still need authentication, persistence, and a production-grade server.
