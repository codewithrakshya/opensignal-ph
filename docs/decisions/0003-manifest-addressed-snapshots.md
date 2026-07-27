# ADR 0003: Use manifest-addressed immutable snapshots

- Status: Accepted
- Date: 2026-07-26

## Context

Source data can change between requests. Re-running an ingestion job must not
silently replace inputs used by a prior analysis, and a failed job must resume
without duplicating completed work.

## Decision

Every run is defined by a strict, versioned manifest containing a human-readable
snapshot identifier, source query, page size, and maximum record count. Each raw
page stores the complete source response plus the manifest, manifest digest,
request parameters, and retrieval time.

Page files are immutable. Atomic checkpoints record the path and SHA-256 digest
of every completed page. Reruns verify those digests and reuse valid pages.
Changing the requested snapshot requires a new snapshot identifier.

## Consequences

- Historical inputs remain reproducible and auditable.
- Interrupted jobs resume at page boundaries.
- Corruption and accidental replacement fail closed.
- A manifest identifier becomes part of downstream data lineage.
- Snapshot retention must be managed explicitly as volume grows.
