# ADR 0006: Calculate disproportionality at report level

- Status: Accepted
- Date: 2026-07-27

## Context

A source report can contain repeated terms and multiple drug-event pairs.
Counting raw rows would allow one report to contribute more than once to a
single contingency-table cell.

## Decision

Build ROR and PRR contingency tables from unique report membership:

- `a`: reports containing the target drug and target event;
- `b`: reports containing the target drug but not the target event;
- `c`: reports containing the target event but not the target drug;
- `d`: reports containing neither.

Score only observed drug-event pairs. Apply the Haldane-Anscombe correction
only when at least one table cell is zero.

ROR signals require at least three target reports and a lower 95% confidence
bound above one. PRR signals require at least three target reports, PRR at least
two, and Pearson chi-square at least four. A separate conservative stability
flag requires at least five target reports and a lower confidence bound above
one.

## Consequences

- Every table has an auditable report-level interpretation.
- Duplicate curated rows cannot inflate a table cell.
- Named criteria are preserved with every score.
- Threshold-based signals remain screening results and require expert review.
