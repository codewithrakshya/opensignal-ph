# ADR 0005: Share platform contracts, not one scientific schema

- Status: Accepted
- Date: 2026-07-27

## Context

OpenSignal PH now processes adverse-event reports and CDC wastewater samples.
The sources share operational requirements but have fundamentally different
scientific grains and interpretation constraints.

## Decision

Reuse manifests, bounded pagination, raw-page envelopes, immutable storage,
checkpoints, provenance, accepted/rejected artifact conventions, quality-check
structures, and processor registration.

Do not force drug-event pairs and wastewater observations into one analytical
table. Each source processor publishes an explicit curated model appropriate to
its scientific domain.

## Consequences

- Platform capabilities can be demonstrated across heterogeneous datasets.
- Dataset-specific validation and limitations remain visible.
- Cross-source operational monitoring is possible through shared quality-report
  conventions.
- Scientific analyses must choose and version a source-specific contract.
