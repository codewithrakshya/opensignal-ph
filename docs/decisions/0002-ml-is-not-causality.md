# ADR 0002: Treat model output as prioritization, not causality

- Status: Accepted
- Date: 2026-07-26

## Context

Spontaneous adverse-event reports are affected by underreporting, publicity,
missing exposure denominators, duplicates, confounding, and incomplete clinical
information.

## Decision

All statistical and ML outputs are named and presented as reporting signals.
No component may label a product as causing an event, estimate incidence, or
recommend treatment. AI-generated summaries operate only after scoring and
cannot modify scores or review status.

## Consequences

- User-facing language must preserve uncertainty.
- Evaluation focuses on prioritization and lead time.
- Expert review remains an explicit step in the workflow.
