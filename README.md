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

## Frontend workspace

The dependency-free frontend source lives in [`frontend/index.html`](frontend/index.html),
[`frontend/styles.css`](frontend/styles.css), and [`frontend/app.js`](frontend/app.js).
It provides the research input, staged agent pipeline, executive summary,
evidence ledger, comparison view, missing-information review, candidate gaps,
paper rows, and source drawer described by the product brief. It posts real
questions to `POST /api/research` using the shared blueprint contract. When the
API is unavailable, it shows a clearly labelled deterministic demo fixture so
the research workflow remains demonstrable without pretending the fixture is
live evidence.

Run the static frontend locally with:

```bash
python3 -m http.server 4173 --directory frontend
```

Then open `http://127.0.0.1:4173/`. The frontend has no separate package
installation or build step.

## Run and test

Use Python 3.11 or 3.12 as specified by the team blueprint:

```bash
python3 -m pip install -r requirements.txt
python3 -m compileall -q app tests
python3 -m pytest -q
```

Start the API and static frontend in separate terminals:

```bash
python3 run.py
python3 -m http.server 4173 --directory frontend
```

The API exposes `GET /api/health` and `POST /api/research`. The static preview
uses the clearly labelled demo fixture when it cannot reach the API; production
serving should place both under the same origin or configure a reverse proxy.

The test suite includes the API orchestration and health endpoint. Actual
result: **pass** - 15 Python tests passed locally. Critic validation
also passed with a direct smoke test for incomparable datasets.

## Limitations and next step

Discovery and authenticity currently use OpenAlex and do not establish
scientific validity or comprehensive literature coverage. Authenticity lookup
failures preserve the paper as `unverified` and return a structured warning.
Network failures return a structured error. The frontend demo fixture is only
for interface demonstration and is clearly labelled as non-live data. The
local API wires discovery, authenticity, critic, and reasoning outputs into
the frontend report contract; a production deployment would still need
authentication, persistence, and a production-grade server.
