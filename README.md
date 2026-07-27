# OpenSignal PH

OpenSignal PH is an open-source public-health safety surveillance platform for
reproducible adverse-event signal detection and evaluation.

For a nontechnical explanation of the problem, novelty, intended users,
benefits, workflow, AI/ML boundaries, and limitations, see
[OpenSignal PH: purpose, novelty, users, and workflow](docs/project-overview.md).
For the complete architecture, research workflow, automation model, safety
boundaries, current status, and prioritized remaining work, see the
[system design and research guide](docs/system-design-and-research-guide.md).

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

## Historical benchmark foundation

Phase 10 begins the transition from the synthetic portfolio demonstration to a
real historical FAERS evaluation. Official 2024–2025 quarterly archive URLs are
versioned in `manifests/faers-quarterly-2024-2025.json`; downloads are bounded,
ZIP-validated, and paired with immutable SHA-256 lock metadata.

Start with one quarter rather than downloading the full window:

```bash
opensignal download-quarterly \
  --manifest manifests/faers-quarterly-2024-2025.json \
  --quarter 2024Q1 \
  --max-bytes 100000000
```

The FDA potential-signal file is currently an unverified terminology-review
seed. Confirm that it remains excluded from performance scoring:

```bash
opensignal validate-benchmark-reference \
  --reference-set reference_sets/fda-potential-signals-2024-2025-seed.json \
  --analysis-quarter 2025-Q4
```

See [the historical benchmark protocol](docs/historical-benchmark-protocol.md)
for source provenance, independent-review requirements, temporal leakage
controls, limitations, and the expansion checklist.

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

## Phase 2 validation and curation

Process an ingested snapshot with:

```bash
opensignal process \
  --source openfda \
  --snapshot-id demo-serious-reports-2024
```

The processing layer:

- validates every source report against typed, permissive openFDA contracts;
- keeps the highest `safetyreportversion` for each report identifier;
- distinguishes older follow-ups from exact duplicate versions;
- prefers standardized generic or substance names and records name provenance;
- normalizes drug roles and reaction terms;
- preserves accepted reports and rejected-record reasons;
- produces flattened drug-event pairs for downstream signal analysis;
- emits a machine-readable quality report with checks and artifact lineage.

Artifacts are written under:

```text
data/validated/openfda/<snapshot-id>/
data/curated/openfda/<snapshot-id>/
data/quality/openfda/<snapshot-id>/
```

Snapshot storage now accepts a source identifier, so additional adapters can
reuse the same integrity, checkpoint, and directory contracts.

## CDC wastewater source

OpenSignal PH also supports the CDC National Wastewater Surveillance System
dataset through a reusable Socrata adapter:

```bash
opensignal ingest-socrata \
  --manifest manifests/cdc-wastewater-demo.json

opensignal process \
  --source cdc-wastewater \
  --snapshot-id cdc-wastewater-sarscov2-2026-demo
```

This second source reuses the platform's manifest digest, bounded pagination,
immutable snapshots, checkpoint integrity, accepted/rejected artifacts, source
registry, and quality-report conventions.

Its analytical contract remains dataset-specific. Wastewater processing
validates sampling identifiers and dates, keeps the latest source update for
each record, normalizes pathogen and geographic fields, and rejects negative
concentrations. Quality reports explicitly warn against directly comparing
concentrations across sites with different collection and laboratory methods.

The demonstration manifest is capped at 5,000 records and selects only fields
used by the current typed contract.

## Phase 3 statistical signal scoring

After processing an openFDA snapshot, calculate report-level ROR and PRR scores:

```bash
opensignal score \
  --source openfda \
  --snapshot-id demo-serious-reports-2024
```

Outputs are written to:

```text
data/analytics/openfda/<snapshot-id>/signals.jsonl
data/analytics/openfda/<snapshot-id>/metadata.json
```

Every score contains its complete two-by-two contingency counts, estimate,
95% confidence interval, named threshold results, stability status, analysis
date, and explanation. The metadata records the SHA-256 digest of the curated
input and the criteria version.

The API exposes the saved artifact without recalculating it:

```text
GET /signals/openfda/<snapshot-id>
GET /signals/openfda/<snapshot-id>?potential_only=true&stable_only=true
GET /signals/openfda/<snapshot-id>?detector=proportional_reporting_ratio
```

These are reporting-pattern signals for review, not causal conclusions or
estimates of adverse-event incidence.

## Phase 4 temporal ML

Build quarterly features and run the reproducible temporal detectors with:

```bash
opensignal temporal \
  --source openfda \
  --snapshot-id demo-serious-reports-2024
```

The feature table contains report volume, reporting share,
quarter-over-quarter growth, serious-report proportion, ROR, and PRR for every
observed drug-event pair and represented quarter. Zero-count quarters are
retained. A seeded Isolation Forest ranks unusual combinations, while a
median/MAD change score compares each quarter only with that pair's prior
history.

The run writes:

```text
data/analytics/openfda/<snapshot-id>/temporal/features.jsonl
data/analytics/openfda/<snapshot-id>/temporal/signals.jsonl
data/analytics/openfda/<snapshot-id>/temporal/model.pkl
data/analytics/openfda/<snapshot-id>/temporal/metadata.json
```

Metadata captures the curated-input and feature-table digests, random seed,
hyperparameters, feature schema, and model digest. Explanations expose
robust-scaled feature deviations; these are prioritization aids, not causal
attributions. Model pickle files are internal artifacts and must not be loaded
from untrusted sources.

Saved results are available at:

```text
GET /temporal-signals/openfda/<snapshot-id>
GET /temporal-signals/openfda/<snapshot-id>?anomalies_only=true
GET /temporal-signals/openfda/<snapshot-id>?changes_only=true
```

## Phase 5 walk-forward backtesting

Evaluate all four ranking methods against a versioned reference set:

```bash
opensignal backtest \
  --source openfda \
  --snapshot-id demo-serious-reports-2024 \
  --reference-set reference_sets/fda-2025-q2-demo.json \
  --k 10
```

The evaluation compares report count, ROR, PRR, and Isolation Forest. For every
simulated quarter, the ML scaler and model are fitted using strictly earlier
rows and score only the current quarter. A minimum-history requirement makes
unavailable quarters explicit instead of silently using future information.

Outputs include full rankings, per-quarter metrics, a summary, and lineage:

```text
data/analytics/openfda/<snapshot-id>/backtests/<reference-set-id>/rankings.jsonl
data/analytics/openfda/<snapshot-id>/backtests/<reference-set-id>/quarter_metrics.jsonl
data/analytics/openfda/<snapshot-id>/backtests/<reference-set-id>/summary.json
data/analytics/openfda/<snapshot-id>/backtests/<reference-set-id>/metadata.json
```

The summary reports recall@K, precision@K, median lead time, alert burden,
detector availability, and reference-matching coverage. Reference records keep
the original FDA product/risk text and label each normalized mapping as exact,
manual, or unmatched.

The checked-in 2025 Q2 reference file is a small, sourced demonstration subset,
not a complete benchmark. Its source is the
[FDA April–June 2025 quarterly report](https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/april-june-2025-new-safety-information-or-potential-signals-serious-risks-identified-fda-adverse).
FDA explicitly cautions that inclusion in these reports does not establish a
causal relationship.

Read a saved result through:

```text
GET /backtests/openfda/<snapshot-id>/<reference-set-id>
```

## Phase 6 surveillance interface

The `dashboard/` application turns the saved analytical contracts into an
evidence-first review workspace. It includes:

- a searchable, status-filtered signal queue;
- quarterly trend and confidence-interval context;
- transparent statistical and ML prioritization reasons;
- source snapshot, method version, and digest provenance;
- data-quality gates and walk-forward detector comparisons;
- accessible responsible-use messaging;
- a downloadable, versioned JSON analysis bundle.

Run the interface locally with:

```bash
cd dashboard
npm install
npm run dev
```

The deployed portfolio interface uses clearly labeled realistic demonstration
records. It is not live FDA monitoring and does not present clinical findings.
The UI boundary is kept separate from analytics so an API adapter can replace
the fixture data without changing the review workflow.

## Responsible-use statement

OpenSignal PH identifies reporting patterns that may warrant further review.
It does not determine causality, recommend treatment, estimate adverse-event
incidence, or replace review by pharmacovigilance and clinical experts.

## Phase 7 evidence briefing

Generate a deterministic, cited evidence brief without an account or API key:

```bash
opensignal brief \
  --snapshot-id <snapshot-id> \
  --drug "DRUG A" \
  --event "EVENT X" \
  --evidence-set evidence_sets/fda-demo-v1.json
```

The optional `--provider openai` path requires `pip install -e '.[ai]'` and an
`OPENAI_API_KEY`; a ChatGPT subscription is neither required nor used. Both
providers write a separate artifact under `data/analytics/.../briefs/`.
Validation rejects unknown citations and causal, safety, or treatment claims,
then fails closed to an explicit abstention. The signal artifact is read-only
and its SHA-256 digest is recorded in every brief.

Saved briefs are available from:

```text
GET /briefs/openfda/<snapshot-id>?drug=<drug>&event=<event>
```

## Project status

Phases 0–8 are implemented as a portfolio release. The dashboard includes
cited evidence briefs and visible abstention, while the API provides health and
readiness probes, structured request logs, metrics, and role-aware review audit
events.

Run the complete synthetic, non-clinical demonstration with:

```bash
pip install -e '.[ml]'
opensignal demo
```

This produces statistical scores, temporal ML artifacts, and a grounded
evidence brief under `data/analytics/openfda/portfolio-demo`. It also writes
covariate-aware sensitivity results comparing crude, Mantel–Haenszel,
penalized, and hierarchical Bayesian reporting associations.

Run the adjusted analysis for an existing curated snapshot with:

```bash
opensignal adjust --source openfda --snapshot-id <snapshot-id>
```

Results are available from:

```text
GET /adjusted/openfda/<snapshot-id>?drug=<drug>&event=<event>
```

See `docs/adjusted-methods.md` for assumptions, missingness handling, and the
important boundary between adjusted FAERS reporting associations and causal
claims/EHR analyses. See
`docs/portfolio-walkthrough.md` for the interview demonstration and
`docs/operations.md` for scheduling, retention, audit, and recovery guidance.
