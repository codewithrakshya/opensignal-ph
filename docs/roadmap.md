# Implementation roadmap

The roadmap favors small, validated vertical slices. A phase is complete only
when its outputs are reproducible, tested, and documented.

## Phase 0 — Foundation

**Goal:** establish architecture and developer contracts.

- package boundaries and configuration;
- health endpoint;
- detector protocol and ROR reference implementation;
- unit tests, linting, type checking, CI, and container definition;
- responsible-use language and architectural decision records.

**Exit criteria:** tests pass locally and in CI; API starts successfully.

## Phase 1 — Reproducible ingestion

**Goal:** acquire a bounded openFDA sample safely and repeatably.

- [x] asynchronous client with retry, timeout, and rate-limit handling;
- [x] query manifest and retrieval metadata;
- [x] page-level checkpoints and idempotent reruns;
- [x] immutable JSON snapshots;
- [x] API-key support through environment configuration;
- [x] deterministic fixtures for offline tests.

**Status:** Complete. The same manifest can be rerun without another source
request or duplicated pages; snapshot conflicts fail closed.

## Phase 2 — Data contracts and quality

**Goal:** make data fitness visible before modeling.

- typed source and curated schemas;
- follow-up report deduplication rules;
- drug-role and reaction normalization;
- accepted/rejected record outputs;
- completeness, validity, uniqueness, freshness, and volume checks;
- machine-readable quality report.

**Exit criteria:** every input record is accepted or rejected with a reason.

## Phase 3 — Statistical signal baseline

**Goal:** produce auditable drug-event signal scores.

- contingency-table construction;
- ROR and PRR with confidence intervals;
- minimum-case and stability rules;
- reproducible quarterly scoring;
- API endpoints for score details and explanations.

**Exit criteria:** reference examples and edge cases match independently
calculated expected values.

## Phase 4 — Temporal ML

**Goal:** test whether ML improves prioritization.

- quarterly feature table with reporting volume, growth, seriousness, and
  baseline statistics;
- Isolation Forest baseline;
- change-point detection;
- explainable feature contributions;
- saved model and feature metadata;
- no LLMs in core signal scoring.

**Exit criteria:** models run from versioned features and reproduce saved scores.

## Phase 5 — Leakage-resistant backtesting

**Goal:** evaluate practical early-warning value.

- versioned FDA quarterly signal reference set;
- walk-forward evaluation using only prior information;
- recall@K, precision@K, median lead time, and alert burden;
- comparisons between counts, ROR, PRR, and ML;
- documented matching uncertainty between FDA terms and normalized terms.

**Exit criteria:** a single command regenerates the evaluation report.

## Phase 6 — Surveillance interface

**Goal:** support transparent human review.

- signal queue and filters;
- trend and confidence-interval visualizations;
- data-quality indicators;
- detector explanations and evidence provenance;
- downloadable, versioned analysis bundle;
- accessible responsible-use messaging.

**Exit criteria:** every visible result links to its method, time window, and
source snapshot.

## Phase 7 — AI-assisted evidence briefing

**Goal:** reduce review effort without delegating safety decisions.

- retrieve relevant FDA notices and labels;
- structured, cited evidence summaries;
- constrained templates and abstention;
- evaluation of citation correctness and unsupported claims;
- clear separation from statistical and ML scoring.

**Exit criteria:** summaries pass a documented evaluation set and never alter
the underlying signal decision.

## Phase 8 — Platform hardening

**Goal:** demonstrate production operations.

- scheduled orchestration;
- structured logs, metrics, and readiness checks;
- database migrations and retention policy;
- role-aware review workflow and audit events;
- software bill of materials and dependency scanning;
- deployment documentation and recovery exercise.

**Exit criteria:** a documented release can be deployed, monitored, and restored.
