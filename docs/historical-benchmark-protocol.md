# Historical FAERS benchmark protocol

## Purpose

This benchmark asks a narrow, testable question:

> Using only reports available before an FDA publication quarter, how well
> would each detector have prioritized drug-event pairs that FDA later listed
> as potential safety signals?

It evaluates prioritization, not causality, diagnosis, incidence, or regulatory
decision-making. FDA itself cautions that a listed potential signal does not
mean the product caused the event.

## Versioned sources

The initial window is 2024 Q1 through 2025 Q4.

- Input reports come from FDA's non-cumulative quarterly FAERS ASCII ZIP files.
  The acquisition manifest pins the official URL and posting metadata for each
  quarter. A download lock records the retrieval timestamp, byte count,
  SHA-256 digest, ETag, and Last-Modified value when available.
- Candidate reference outcomes come from FDA's quarterly lists of new safety
  information or potential signals. Source wording and publication quarter are
  retained without silently translating them into model terminology.

The checked-in reference file is a **seed**, not a completed gold standard. It
contains one example from each quarter to exercise the workflow. Its entries
are deliberately ineligible for scoring until independent terminology review
is recorded.

## Reproducible bounded acquisition

Validate the manifest without downloading data:

```bash
python -c "from pathlib import Path; from opensignal.benchmark.quarterly import QuarterlyAcquisitionManifest; print(QuarterlyAcquisitionManifest.from_path(Path('manifests/faers-quarterly-2024-2025.json')).manifest_id)"
```

Download one bounded pilot archive:

```bash
opensignal download-quarterly \
  --manifest manifests/faers-quarterly-2024-2025.json \
  --quarter 2024Q1 \
  --destination data/raw/faers-quarterly \
  --max-bytes 100000000
```

The downloader streams to a partial file, enforces the per-archive byte limit,
checks ZIP integrity, then atomically promotes the file. A rerun reuses the
archive only when its byte count, digest, URL, and quarter match its lock.
Conflicts fail closed. Raw archives and lock files should be retained together.

## Terminology review

Each FDA row must be transcribed with:

1. source product and event text;
2. source URL and FDA publication quarter;
3. normalized ingredient name or names;
4. normalized adverse-event term or terms;
5. match method: exact, manual, or unmatched;
6. reviewer identity, timestamp, and notes.

An entry is eligible only when an independent reviewer has approved nonempty
drug and event mappings. Ambiguous class-level products, broad clinical
concepts, spelling variants, and one-to-many MedDRA mappings require documented
manual review. Rejected and unmatched entries remain visible rather than being
deleted.

Validate the current seed:

```bash
opensignal validate-benchmark-reference \
  --reference-set reference_sets/fda-potential-signals-2024-2025-seed.json \
  --analysis-quarter 2025-Q4
```

The expected eligible count is zero until review is completed.

## Leakage prevention and evaluation

For simulated quarter `t`:

- include only reports whose availability date is no later than `t`;
- fit transformations and ML models using periods strictly earlier than the
  scoring period;
- never use a reference entry before its FDA publication quarter;
- freeze terminology mappings before inspecting detector rankings;
- give every detector the same alert budget `K`;
- report recall@K, precision@K, alert burden, and lead time by quarter;
- compare count, ROR, PRR, adjusted methods, and temporal ML;
- report missing/unmatched reference coverage alongside performance.

Publication-quarter matching is conservative: it tests whether a method
prioritizes a pair by the time FDA publicly lists it. A separate, predeclared
lead-time analysis may inspect earlier quarters, but cannot use future
terminology or tune thresholds against the answer key.

## Known limitations

FDA's list is an incomplete and policy-mediated reference, not a complete set
of all true adverse reactions. FAERS contains duplicate, stimulated, missing,
and confounded reporting and lacks a population denominator. Results therefore
measure agreement with a public regulatory signal list under a fixed alert
budget—not clinical risk, causal effect, or superiority over FDA surveillance.

## Expansion checklist

- transcribe every FDA row in the study window;
- have a second person independently verify source text and mappings;
- resolve disagreements without viewing model ranks;
- preserve the reviewed reference-set version and digest;
- parse and quality-check a single quarterly archive;
- scale only after the pilot reconciles report counts and schema changes;
- preregister detector configurations, thresholds, subgroup analyses, and
  sensitivity analyses;
- publish both positive and negative benchmark findings.
