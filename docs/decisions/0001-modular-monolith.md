# ADR 0001: Begin with a modular monolith

- Status: Accepted
- Date: 2026-07-26

## Context

OpenSignal PH needs clear platform boundaries but does not initially require the
operational cost of multiple deployed services.

## Decision

Begin as one Python package and one API deployment. Enforce module boundaries
between ingestion, quality, detection, and delivery. Persist data through
explicit interfaces so components can be extracted later if scale or ownership
requires it.

## Consequences

- Local development and testing remain simple.
- Architectural boundaries are visible in code.
- We avoid premature distributed-system complexity.
- Future extraction requires preserving stable interfaces from the beginning.
