# ADR 0009: The surveillance interface is evidence-first

- Status: Accepted
- Date: 2026-07-27

## Context

Signal scores become misleading when detached from their analysis window,
uncertainty, input quality, or method. A useful surveillance interface must
support rapid triage without turning statistical or ML output into a diagnosis.

## Decision

The Phase 6 interface presents a prioritized queue beside a persistent evidence
panel. Selecting a signal exposes the analysis quarter, detector, estimate,
confidence interval, report count, serious-report count, temporal history,
named prioritization reasons, source snapshot, criteria version, and input
digest.

Quality and walk-forward evaluation remain visible in the same workspace.
Filters change only the review queue; they do not alter saved detector scores.
Exports are versioned JSON analysis bundles and repeat the responsible-use
statement. The interface uses semantic controls, keyboard focus states,
responsive layouts, reduced-motion support, and text alternatives for trends.

The deployed portfolio demonstration uses clearly labeled realistic fixture
data. It illustrates the delivery contract without representing live FDA
surveillance or clinical findings.

## Consequences

- Every displayed result retains its method, time window, and provenance.
- Reviewers can distinguish statistical stability from ML prioritization.
- Demonstration data cannot be mistaken for live operational monitoring.
- Future API integration can replace the fixture adapter without redesigning
  the review workflow.
