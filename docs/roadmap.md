# Implementation roadmap

The roadmap favors small, validated vertical slices. A phase is complete only
when its outputs are reproducible, tested, and documented.

The [system design and research guide](system-design-and-research-guide.md)
explains how these phases fit together and groups the remaining ideas by
scientific, researcher-experience, validation, and production priority.

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

- [x] typed source and curated schemas;
- [x] follow-up report deduplication rules;
- [x] drug-role and reaction normalization;
- [x] accepted/rejected record outputs;
- [x] completeness, validity, uniqueness, freshness, and volume checks;
- [x] machine-readable quality report;
- [x] source-neutral raw snapshot storage contract.

**Status:** Complete. Every input record is accepted, superseded by a later
follow-up, classified as an exact duplicate, or rejected with a reason.

## Multi-source progression — CDC Socrata adapter

**Goal:** demonstrate that the platform is reusable beyond adverse-event data.

- [x] generic, bounded Socrata manifest and paging adapter;
- [x] retry and optional application-token support;
- [x] CDC wastewater demonstration manifest;
- [x] typed wastewater sampling contract;
- [x] latest-update and exact-duplicate handling;
- [x] accepted, rejected, curated, and quality-report artifacts;
- [x] shared source processor registry;
- [x] explicit dataset interpretation cautions.

**Status:** Complete. openFDA and CDC wastewater data now reuse platform
infrastructure while retaining distinct scientifically appropriate schemas.

## Phase 3 — Statistical signal baseline

**Goal:** produce auditable drug-event signal scores.

- [x] report-level contingency-table construction;
- [x] ROR and PRR with confidence intervals;
- [x] explicit minimum-case and conservative stability rules;
- [x] versioned scoring artifacts with curated-input digest;
- [x] API endpoint for score details, criteria, and explanations.

**Status:** Complete. Reference calculations, sparse-table edge cases, artifact
lineage, and API filtering are covered by automated tests.

## Phase 4 — Temporal ML

**Goal:** test whether ML improves prioritization.

- [x] quarterly feature table with reporting volume, growth, seriousness, and
  baseline statistics;
- [x] seeded Isolation Forest baseline;
- [x] prior-history robust change-point detection;
- [x] explainable feature deviations;
- [x] saved model, feature table, hashes, and feature metadata;
- [x] API and CLI delivery with no LLMs in core signal scoring.

**Status:** Complete. Models run from versioned features, preserve zero-count
quarters, save their full configuration and fitted artifact, and reproduce
saved scores under automated tests.

## Phase 5 — Leakage-resistant backtesting

**Goal:** evaluate practical early-warning value.

- [x] versioned FDA quarterly signal reference contract and audited demo subset;
- [x] walk-forward evaluation using only prior information;
- [x] recall@K, precision@K, median lead time, and alert burden;
- [x] comparisons between counts, ROR, PRR, and ML;
- [x] documented matching uncertainty between FDA terms and normalized terms.

**Status:** Complete. A single command regenerates rankings, quarterly metrics,
summary measures, and lineage metadata. The checked-in FDA subset demonstrates
the contract; expanding and independently reviewing reference coverage remains
required before interpreting benchmark values.

## Phase 6 — Surveillance interface

**Goal:** support transparent human review.

- [x] signal queue and filters;
- [x] trend and confidence-interval visualizations;
- [x] data-quality indicators;
- [x] detector explanations and evidence provenance;
- [x] downloadable, versioned analysis bundle;
- [x] accessible responsible-use messaging.

**Status:** Complete. Every visible result links to its method, analysis
quarter, source snapshot, criteria version, and uncertainty. The responsive
portfolio deployment is explicitly labeled as a demonstration.

## Phase 7 — AI-assisted evidence briefing

**Goal:** reduce review effort without delegating safety decisions.

- [x] retrieve relevant FDA notices and labels;
- [x] structured, cited evidence summaries;
- [x] constrained templates and abstention;
- [x] evaluation of citation correctness and unsupported claims;
- [x] clear separation from statistical and ML scoring.

**Exit criteria:** summaries pass a documented evaluation set and never alter
the underlying signal decision.

Completed with automated citation, abstention, unsafe-language, and artifact
immutability tests. See ADR 0010.

## Phase 8 — Platform hardening

**Goal:** demonstrate production operations.

- [x] scheduled orchestration;
- [x] structured logs, metrics, and readiness checks;
- [x] versioned artifact schemas and retention policy;
- [x] role-aware review workflow and chained audit events;
- [x] software bill of materials and dependency scanning;
- [x] deployment documentation and recovery exercise.

**Exit criteria:** a documented release can be deployed, monitored, and restored.

**Status:** Portfolio release complete. Trusted role headers and filesystem
artifacts are explicit demonstration implementations; production deployment
must replace them with identity-provider claims and managed durable storage.

## Phase 9 — Covariate-aware sensitivity analysis

**Goal:** show whether crude reporting associations are sensitive to measured
demographics, time, subgroup heterogeneity, or sparse-data shrinkage.

- [x] normalize age group and sex with explicit unknown categories;
- [x] stratified ROR/PRR and approximate heterogeneity assessment;
- [x] Mantel–Haenszel adjusted reporting odds ratio;
- [x] L2-penalized report-level logistic adjustment;
- [x] empirical hierarchical Beta-Binomial shrinkage;
- [x] crude-versus-adjusted sensitivity artifact, API, CLI, and dashboard;
- [x] governed claims/EHR longitudinal validation contract;
- [x] interpretation and missingness documentation.

**Status:** Complete for FAERS reporting-association sensitivity analysis.
Claims/EHR causal estimation remains intentionally inactive until a real,
governed longitudinal dataset and study protocol are supplied.

## Phase 10 — Historical FAERS benchmark

**Goal:** replace the illustrative demo evaluation with a reproducible,
independently reviewed historical benchmark.

- [x] versioned official 2024–2025 quarterly ASCII archive manifest;
- [x] bounded, resumable download with ZIP validation and SHA-256 locks;
- [x] FDA quarterly potential-signal reference seed with source provenance;
- [x] independent-review and temporal-eligibility validation contract;
- [x] documented leakage controls, limitations, and expansion workflow;
- [ ] transcribe and independently review the complete FDA reference window;
- [ ] parse and reconcile one quarterly ASCII pilot;
- [ ] acquire and process all selected quarters;
- [ ] freeze analysis protocol and run equal-alert-burden comparisons;
- [ ] publish uncertainty, unmatched coverage, and sensitivity results.

**Status:** Data foundation complete. The checked-in eight-entry file is an
unverified workflow seed and intentionally produces zero eligible references.
No historical performance claim is supported until the remaining items are
completed.
