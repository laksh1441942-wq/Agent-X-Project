# ResearchPilot AI

ResearchPilot is a multi-agent research assistant prototype. It is designed to
discover papers, check bibliographic metadata, compare evidence, identify
missing information, and present a traceable report. Metadata checks do not
prove scientific truth, and candidate gaps do not prove novelty.

## Current implementation

The first implemented slice is the isolated Paper Discovery Agent in
`app/services/paper_discovery.py`. It:

- searches OpenAlex with a timeout;
- normalizes source metadata into the shared paper-record shape;
- reconstructs abstracts when OpenAlex provides an inverted index;
- removes duplicates by DOI or normalized title and year;
- ranks candidates by unique non-stopword overlap with title/abstract, then
  OpenAlex relevance score; and
- returns structured warnings/errors without inventing missing metadata.

The module is importable without starting a server. No new runtime dependency
was added; HTTP requests use Python's standard library.

## Run and test

Use Python 3.11 or 3.12 as specified by the team blueprint:

```bash
python3 -m compileall -q app tests
python3 -m pytest -q tests/test_paper_discovery.py
```

Actual result: **pass** - 5 tests passed locally.

## Limitations and next step

Discovery currently searches only OpenAlex and does not establish
authenticity, scientific validity, or comprehensive literature coverage.
Network failures return a structured error and no fallback fixture has been
connected yet. The next step is for the team lead to connect this function to
the shared schemas and orchestrator, followed by the authenticity, critic, and
reasoning stages.
