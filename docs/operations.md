# Operations and recovery

## Service objectives

- `/health` confirms that the API process is running.
- `/ready` verifies that versioned artifact storage is writable.
- `/metrics` exposes request counters in Prometheus text format.
- Every response includes an `x-request-id`; request logs are structured JSON.

The API should be removed from rotation when readiness fails. Signal generation
must never continue after a quality gate or immutable-artifact conflict.

## Scheduled execution

`.github/workflows/surveillance.yml` runs the synthetic demonstration monthly
and on demand. Production manifests should be reviewed and pinned before
enabling an external-data schedule. Workflow artifacts are retained for 30
days; source snapshots and released analytical artifacts follow the policy
below.

## Retention policy

| Artifact | Minimum retention | Deletion rule |
|---|---:|---|
| Released source manifests and metadata | Permanent | Never automatically |
| Raw public-source snapshots | 365 days | Only after digest verification and release backup |
| Curated and analytical release artifacts | Permanent | Supersede; do not overwrite |
| Checkpoints for completed, backed-up runs | 90 days | Recoverable deletion |
| Request logs | 30 days | Rotate by environment |
| Review audit events | 7 years | Append-only; legal policy may extend |

No automated deletion is enabled in this portfolio release. This is deliberate:
retention enforcement requires deployment-specific storage and approval.

## Review access and audit

Review writes require `x-opensignal-role: reviewer` or `admin` and an actor
identifier. Events are appended to source/snapshot JSONL logs. Every event
records the digest of the preceding log, making unexpected rewriting visible.
Real deployments must replace trusted headers with identity-provider claims.

## Recovery exercise

1. Stop scheduled ingestion and remove the unhealthy API from service.
2. Restore the last released raw, curated, analytics, and audit directories.
3. Verify saved SHA-256 digests and immutable snapshot pages.
4. Re-run `opensignal demo` and the automated test suite.
5. Start the API and confirm `/health`, `/ready`, and `/metrics`.
6. Compare regenerated scores and model hashes with the release metadata.
7. Record the exercise, reviewer, recovery point, and any mismatches.

The recovery-point objective is the latest released immutable snapshot. The
demonstration recovery-time objective is 30 minutes on a prepared workstation.

## Supply chain

GitHub Actions creates an SPDX JSON software bill of materials. CI also runs
tests, lint, strict typing, and coverage. Container and dependency scanning
should be enforced by the target deployment platform before promotion.

