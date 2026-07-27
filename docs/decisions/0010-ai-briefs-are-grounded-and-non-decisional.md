# ADR 0010: AI briefs are grounded and non-decisional

## Status

Accepted.

## Decision

Generated text is a separate, immutable artifact derived from a saved signal
artifact and a versioned evidence set. It cannot write statistical or ML
outputs. Each factual claim must cite a retrieved document identifier.

The system abstains when retrieval returns no evidence or validation finds an
unknown citation, unsupported structure, causal assertion, safety conclusion,
or treatment direction. A deterministic offline provider is the default.
The optional OpenAI provider uses Structured Outputs through the Responses API.

## Consequences

Reviewers can reproduce the source hashes and inspect every citation. AI can
reduce reading effort but cannot promote, dismiss, or change a signal. A
ChatGPT subscription is not required; API usage is optional and separately
credentialed.
