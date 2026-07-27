# ADR 0011: Adjusted FAERS estimates remain reporting associations

## Status

Accepted.

## Decision

OpenSignal PH will label crude, stratified, Mantel–Haenszel, penalized, and
hierarchical FAERS estimates as reporting associations. Covariate adjustment
does not convert spontaneous reports into a cohort and cannot supply a reliable
exposure denominator.

Unknown demographic values remain an explicit category. Seriousness is not
treated as a baseline confounder. Claims/EHR causal follow-up is separated by a
longitudinal adapter contract and will not run without an active comparator,
baseline observation, valid temporal ordering, and governed data.

## Consequences

Researchers can assess measured confounding and sparse-data sensitivity without
overstating causal interpretation. Stronger causal questions require a
different dataset and design.

