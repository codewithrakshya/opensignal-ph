# ADR 0007: Temporal ML is a prioritization layer

- Status: Accepted
- Date: 2026-07-27

## Context

Disproportionality scores summarize an analysis window but do not directly
identify abrupt reporting changes. An unsupervised model can prioritize unusual
quarterly patterns before a labeled reference set is available, but its output
is especially vulnerable to reporting artifacts and must not be described as a
causal or validated safety finding.

## Decision

Phase 4 creates one row for every historically observed drug-event pair in
every represented calendar quarter, including zero-count rows. Features include
report count, reporting share, quarter-over-quarter growth, serious-report
proportion, ROR, and PRR.

A robust scaler and seeded Isolation Forest produce an anomaly ranking.
Absolute robust-scaled deviations provide a simple feature-level explanation;
they describe why an input looks unusual and are not causal effects or exact
model attributions. A separate median/MAD change detector compares the current
count only with prior quarters and requires four prior quarters by default.

The fitted scaler and model, feature table, scores, input hashes, feature names,
hyperparameters, and random seed are saved together. Core signal scoring does
not use an LLM. Pickled model artifacts are internal build products and must
never be loaded from an untrusted source.

## Consequences

- The same curated snapshot and configuration reproduce the saved scores.
- Zero quarters remain visible rather than silently dropping inactive pairs.
- Isolation Forest scores are descriptive in Phase 4; strict walk-forward
  evaluation and threshold selection belong to Phase 5.
- An anomaly or change point is a review priority, not evidence that a medicine
  caused an event.
