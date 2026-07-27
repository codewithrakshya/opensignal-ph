# ADR 0004: Curate data at the report–drug–event grain

- Status: Accepted
- Date: 2026-07-27

## Context

An adverse-event report may contain multiple drugs and multiple reactions.
Disproportionality methods require auditable drug-event observations, while the
validated source report must remain available for lineage and future methods.

## Decision

Retain one validated representation of the latest version of each report, then
produce one curated row for every unique drug, drug-role, and reaction
combination within that report.

Drug-name provenance is recorded. Standardized openFDA generic and substance
names are preferred; reported medicinal-product text is a labeled fallback.
Reaction terms are normalized without claiming that related terms are
clinically equivalent.

## Consequences

- Downstream contingency tables have an explicit and testable grain.
- One report can contribute multiple unique drug-event observations.
- Duplicate pairs within a report are removed.
- Clinical synonym grouping remains a separate, versioned future decision.
