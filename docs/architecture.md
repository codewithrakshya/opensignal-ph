# Architecture

## Design goals

OpenSignal PH is designed around capabilities that can be reused for additional
public-health surveillance sources:

1. reproducible acquisition;
2. explicit schemas and data contracts;
3. observable transformation and quality;
4. interchangeable analytics;
5. time-aware evaluation;
6. explainable delivery.

## Components

### Source adapters

Each source adapter retrieves bounded pages, records retrieval metadata, obeys
rate limits, and supports resumable checkpoints. Source-specific representations
must not leak beyond the ingestion boundary.

The first two adapters demonstrate different API conventions:

- openFDA uses `limit` and `skip` with a nested response object;
- Socrata uses SoQL parameters such as `$limit`, `$offset`, `$where`, and
  `$order` and returns a list of records.

Both are wrapped in the same raw-page envelope and stored through the same
source-neutral snapshot and checkpoint service.

### Data layers

- **Raw:** immutable source payloads plus retrieval metadata.
- **Validated:** typed records that passed structural checks; rejected records
  are retained with reasons.
- **Curated:** normalized drug, reaction, case, outcome, and reporting-period
  entities.
- **Analytics:** aggregate contingency tables, detector scores, alerts, and
  backtest results.

### Quality service

Quality checks produce data, not only log messages. Results include freshness,
completeness, validity, uniqueness, volume, and distribution checks and are
available to both the API and dashboard.

Source processors implement a shared snapshot-processing protocol and are
selected through a registry. Adding another source requires an adapter and
registration; it does not require changes to the CLI or artifact layout.

OpenFDA produces report–drug–event rows for safety-signal analysis. CDC
wastewater data produces site–sample–pathogen observations. They deliberately
do not share a forced analytical schema; the platform contract is shared while
the scientific grain remains explicit.

### Detector interface

Every statistical or ML method accepts a defined analysis window and produces
a documented score. Detectors must explain their output and declare the
minimum data they require. ROR and PRR provide the statistical baseline.

The temporal layer builds a versioned quarterly feature table and uses a
seeded Isolation Forest for unsupervised prioritization. A separate robust
change score uses only a pair's prior quarters. Model metadata records feature
names, configuration, input digest, and fitted-artifact digest. ML output is a
review ranking and never overrides the underlying statistical evidence.

### Signal registry

The future registry will store detector version, feature window, source snapshot,
score, threshold decision, explanation, and review status. This enables
reproducible comparison across methods and quarters.

### Backtesting

Backtests use only data available at the simulated decision date. Statistical
baselines rank the current quarter, while Isolation Forest is refit from
strictly earlier rows before scoring each simulated quarter. FDA-published
quarterly potential signals act as an external evaluation reference, not as
proof of causal association. Original FDA text and explicit exact, manual, or
unmatched normalization decisions remain in the versioned reference set.

### Delivery

FastAPI provides health, metadata, quality, signal, temporal-signal, and
backtest endpoints. The separate `dashboard/` application implements the human
review contract and can consume these APIs without querying analytical storage
directly. Its deployed portfolio mode uses explicit demonstration fixtures.

### Operations and review

The API emits structured request logs, a request identifier, Prometheus-format
request counters, and separate liveness and storage-readiness endpoints.
Role-gated review decisions are append-only events whose previous-log digest
makes rewriting detectable. The portfolio uses filesystem artifacts so every
contract stays inspectable; a production deployment would map the same
contracts to managed object storage and an identity-backed operational store.

## Trust boundaries

- Secrets enter through environment variables and are never committed.
- Raw public records remain separate from derived analytics.
- Generated summaries cannot alter detector scores.
- AI-generated text must cite its input evidence and must support abstention.
- The interface must label all outputs as potential reporting signals.

## Initial technology choices

- Python for ingestion, analytics, and API services
- Parquet for versioned analytical artifacts
- DuckDB for local analytical queries
- PostgreSQL later for operational signal metadata
- FastAPI for a typed, documented service
- scikit-learn for initial ML baselines
- Docker Compose for reproducible local operation
- GitHub Actions for continuous validation
