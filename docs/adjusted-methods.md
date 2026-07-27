# Covariate-aware reporting-association methods

## Purpose

Phase 9 tests whether a crude FAERS disproportionality estimate is sensitive to
age group, sex, calendar year, sparse data, or subgroup variation. These methods
estimate **reporting associations**, not incidence, relative risk, or causality.

## Analysis population

The processor normalizes patient age into `0-1`, `2-17`, `18-44`, `45-64`,
`65+`, or `unknown`, and patient sex into `female`, `male`, or `unknown`.
Unknown is retained as an explicit category rather than silently dropping a
large and potentially non-random portion of spontaneous reports.

The current adjustment set is:

- patient age group;
- patient sex;
- calendar year.

Seriousness is deliberately not included as a baseline confounder because it
can be part of, or downstream from, the reported outcome. Indication and
comorbidity are not included because the current FAERS contract cannot establish
their completeness or temporal relationship reliably.

## Methods

### Stratified ROR and PRR

ROR and PRR are calculated within each observed age-sex-year stratum. The
artifact includes report counts, confidence intervals, and an approximate
Cochran Q heterogeneity statistic. Sparse stratum estimates must be interpreted
carefully.

### Mantel–Haenszel ROR

The common odds ratio combines stratum-specific 2×2 tables. Confidence limits
use the Robins–Breslow–Greenland variance approximation. This is the primary
interpretable covariate-adjusted sensitivity estimate.

### L2-penalized logistic model

A report-level logistic model predicts whether the target event is present
using target-drug presence, age group, sex, and year. L2 regularization reduces
coefficient instability. The target-drug coefficient is exponentiated as an
adjusted reporting odds ratio.

The release intentionally omits a confidence interval for this penalized
coefficient until a separately validated bootstrap or Bayesian interval is
implemented. A point estimate without a validated interval must not be used as
a decision threshold.

### Active-comparator ROR

An optional reviewed JSON mapping can restrict the comparison group to
medicines serving a similar clinical role. This can reduce distortions from
comparing a target medicine with the entire database. Comparator selection is a
scientific design decision and must not be inferred from product names.

```bash
opensignal adjust \
  --snapshot-id <snapshot-id> \
  --comparator-sets comparator_sets/reviewed-classes.json
```

### Empirical hierarchical Beta-Binomial model

Target-drug and comparator event-reporting probabilities receive a shared prior
centered on the global event-reporting rate. Posterior draws produce a shrunk
reporting odds ratio and 95% credible interval. Partial pooling reduces extreme
small-count estimates.

This is an empirical hierarchical sensitivity model, not a causal model and
not an implementation of FDA's proprietary Empirica/MGPS software.

## Sensitivity interpretation

Reviewers compare:

```text
crude ROR
Mantel–Haenszel adjusted ROR
L2-penalized adjusted reporting OR
hierarchical Bayesian shrunk reporting OR
```

A material reduction after adjustment may reflect measured confounding,
comparator composition, sparse-data shrinkage, or subgroup imbalance. It does
not prove that the crude estimate was false. Stability across estimates does
not prove causality.

## Missingness

Missing demographic values are displayed and modeled as `unknown`. Every
result records reports used and reports excluded. Researchers should repeat
analyses with:

1. unknown as an explicit category;
2. complete cases;
3. missingness-stratified summaries.

Multiple imputation is not enabled because its assumptions would require a
validated missingness model and richer predictors.

## Claims and EHR validation boundary

`LongitudinalCohortRecord` and `LongitudinalValidator` define a future adapter
for governed longitudinal data. The contract requires:

- exactly one row per new user;
- target and active-comparator cohorts;
- at least 180 days of baseline observation;
- exposure within the observation window;
- outcomes after exposure and within follow-up;
- baseline covariates recorded before exposure.

No causal estimator is supplied without a real governed dataset. A production
adapter should add propensity-score diagnostics, overlap checks, negative
controls, outcome validation, censoring rules, and a pre-registered protocol.
