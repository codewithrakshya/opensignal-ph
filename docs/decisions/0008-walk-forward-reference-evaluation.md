# ADR 0008: Walk-forward evaluation uses explicit reference mappings

- Status: Accepted
- Date: 2026-07-27

## Context

FDA quarterly reports provide a useful external reference for retrospective
evaluation, but they are not a complete gold standard. Posted product text may
represent a brand, ingredient, combination, or class, and risk text may not
equal one normalized reaction term. FDA also states that a listing is a
potential signal under evaluation, not a causal conclusion.

Random train/test splits would leak future reporting patterns into earlier
simulated decisions. The Phase 4 Isolation Forest fit over a complete snapshot
is suitable for descriptive prioritization but not historical evaluation.

## Decision

Reference entries retain FDA's product and risk text, signal quarter, source
URL, retrieval time, normalized pair, match method, and mapping notes.
Mappings are classified as `exact`, `manual`, or `unmatched`. Unmatched entries
are reported as coverage gaps and excluded from metric denominators.

Backtests proceed quarter by quarter. Count, ROR, and PRR rank only the current
quarter. Isolation Forest is refit at every evaluation quarter using strictly
earlier feature rows, then scores the current quarter. It emits no result until
the configured minimum training size is available.

The report includes recall@K, precision@K, median lead time, alert burden,
matching coverage, per-quarter metrics, full rankings, configuration, and input
digests.

## Consequences

- Future rows cannot affect an earlier ML ranking.
- Detector availability and denominators remain visible.
- Mapping decisions are reviewable rather than hidden in fuzzy matching.
- Agreement with FDA postings measures retrospective prioritization utility;
  it does not establish causality, incidence, or clinical validity.
- The included 2025 Q2 file is an auditable demonstration subset, not a
  complete benchmark. A production evaluation requires a completed and
  independently reviewed reference set.
