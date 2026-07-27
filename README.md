# OpenSignal PH

OpenSignal PH is an open-source public-health safety surveillance platform for
reproducible adverse-event signal detection and evaluation.

The project uses public FDA adverse-event data as its first use case. It is a
research and engineering tool—not a clinical decision system. A report or
statistical signal does not establish that a product caused an event, and the
data cannot be used to estimate incidence.

## Why this project exists

OpenSignal PH demonstrates how a trustworthy public-health analytics capability
can be built as a reusable platform:

- incremental, idempotent data ingestion;
- raw, validated, curated, and analytics data layers;
- observable data-quality checks and lineage;
- interchangeable statistical and machine-learning signal detectors;
- leakage-resistant historical backtesting;
- explainable results through a documented API and dashboard;
- reproducible local development, testing, and deployment.

## System boundaries

```text
FDA open data
    |
    v
ingestion -> raw snapshots -> validation -> curated records
                                            |
                                            v
                              statistical + ML detectors
                                            |
                                            v
                              signal registry + backtests
                                            |
                                      API / dashboard
```

The initial scaffold intentionally contains one working statistical detector
and a health API. Each subsequent phase adds functionality behind an explicit
interface rather than coupling the entire system together.

## Repository layout

```text
src/opensignal/
  api/          FastAPI delivery layer
  core/         configuration and shared domain models
  ingestion/    source adapters and checkpointed ingestion
  quality/      validation rules and quality reporting
  detection/    statistical and ML detector implementations
tests/          unit and integration tests
docs/           architecture, roadmap, and design decisions
```

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
uvicorn opensignal.api.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs`.

## First milestone

The first milestone is a reproducible vertical slice:

1. retrieve a bounded set of public FDA drug-event records;
2. preserve an immutable raw snapshot and retrieval metadata;
3. validate and normalize records into curated tables;
4. compute reporting odds ratios with confidence intervals;
5. expose results and data-quality metadata through the API;
6. verify the pipeline with unit and integration tests.

See [docs/roadmap.md](docs/roadmap.md) for the complete phased plan.

## Phase 1 ingestion

Ingestion is controlled by a versioned JSON manifest. A manifest fixes the
snapshot identifier, openFDA search expression, page size, and maximum record
count:

```bash
cp .env.example .env
opensignal ingest --manifest manifests/openfda-demo.json
```

The command writes:

- immutable page envelopes under `data/raw/openfda/<snapshot-id>/`;
- retrieval time, request parameters, and manifest digest with every page;
- an atomic checkpoint under `data/checkpoints/openfda/`;
- a JSON run summary to standard output.

Rerunning the same manifest verifies and reuses completed pages. It does not
call openFDA again or duplicate records. To intentionally retrieve a new
snapshot, create a new manifest with a new `snapshot_id`.

No API key is required for a small demonstration, but setting
`OPENSIGNAL_OPENFDA_API_KEY` increases the documented openFDA request allowance.

## Responsible-use statement

OpenSignal PH identifies reporting patterns that may warrant further review.
It does not determine causality, recommend treatment, estimate adverse-event
incidence, or replace review by pharmacovigilance and clinical experts.

## Project status

Early scaffold. Interfaces and schemas will evolve as the first vertical slice
is implemented.
