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

The module is importable without starting a server. No new runtime dependency
was added; HTTP requests use Python's standard library.

## Run and test

Use Python 3.11 or 3.12 as specified by the team blueprint:

```bash
python3 -m compileall -q app tests
python3 -m pytest -q
```

Actual result: **pass** - 11 tests passed locally. Critic validation also
passed with a direct smoke test for incomparable datasets.

## Limitations and next step

Discovery and authenticity currently use OpenAlex and do not establish
scientific validity or comprehensive literature coverage. Authenticity lookup
failures preserve the paper as `unverified` and return a structured warning.
Network failures return a structured error and no fallback fixture has been
connected yet. Critic and reasoning outputs still need to be wired into the
shared schemas and orchestrator. The next step is the team lead integration,
followed by API and end-to-end tests.
