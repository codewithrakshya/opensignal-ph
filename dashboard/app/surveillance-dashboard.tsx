"use client";

import { useMemo, useState } from "react";
import { detectorMetrics, signals, type Signal } from "./demo-data";

const statusOrder = ["All", "Priority review", "Monitor", "Context needed"];

function MiniTrend({ values }: { values: number[] }) {
  const maximum = Math.max(...values);
  return (
    <div
      className="mini-trend"
      role="img"
      aria-label={`Quarterly report counts: ${values.join(", ")}`}
    >
      {values.map((value, index) => (
        <span
          key={`${value}-${index}`}
          style={{ height: `${Math.max(10, (value / maximum) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function StatusPill({ status }: { status: Signal["status"] }) {
  return (
    <span className={`status status-${status.toLowerCase().replaceAll(" ", "-")}`}>
      {status}
    </span>
  );
}

export function SurveillanceDashboard() {
  const [selectedId, setSelectedId] = useState(signals[0].id);
  const [status, setStatus] = useState("All");
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");

  const filtered = useMemo(() => {
    const term = query.trim().toUpperCase();
    return signals.filter(
      (signal) =>
        (status === "All" || signal.status === status) &&
        (!term ||
          signal.drug.includes(term) ||
          signal.event.includes(term) ||
          signal.detector.toUpperCase().includes(term)),
    );
  }, [query, status]);

  const selected =
    signals.find((signal) => signal.id === selectedId) ?? signals[0];

  function downloadBundle() {
    const bundle = {
      artifact_version: 1,
      exported_at: new Date().toISOString(),
      source_snapshot: "openfda-2025-q2-demo",
      selected_signal: selected,
      quality: {
        accepted_reports: 4872,
        rejected_reports: 31,
        required_field_completeness: 0.987,
      },
      responsible_use:
        "Potential reporting signals do not establish causality or incidence.",
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(bundle, null, 2)], {
        type: "application/json",
      }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selected.id}-analysis-bundle.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice("Versioned analysis bundle downloaded.");
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#main-content" aria-label="OpenSignal PH home">
          <span className="brand-mark">OS</span>
          <span>
            <strong>OpenSignal PH</strong>
            <small>Safety surveillance platform</small>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          <a className="active" href="#signals">Signals</a>
          <a href="#brief">Evidence brief</a>
          <a href="#quality">Data quality</a>
          <a href="#evaluation">Evaluation</a>
        </nav>
        <div className="snapshot">
          <span className="live-dot" />
          Snapshot 2025 Q2
        </div>
      </header>

      <section className="warning" aria-label="Responsible-use notice">
        <strong>Research use only.</strong>
        <span>
          These are reporting patterns for expert review. They do not establish
          causality, incidence, or treatment guidance.
        </span>
      </section>

      <div className="shell" id="main-content">
        <section className="hero">
          <div>
            <p className="eyebrow">Surveillance workspace / 30 Jun 2025</p>
            <h1>Review what changed,<br />with the evidence attached.</h1>
            <p className="lede">
              Statistical signals and temporal ML agree on two high-priority
              drug-event pairs. Every result retains its source, method, and
              uncertainty.
            </p>
          </div>
          <div className="summary-grid" aria-label="Snapshot summary">
            <article><span>Priority queue</span><strong>02</strong><small>of 46 scored pairs</small></article>
            <article><span>Stable signals</span><strong>07</strong><small>ROR or PRR criteria</small></article>
            <article><span>Data fitness</span><strong>98.7%</strong><small>required fields complete</small></article>
          </div>
        </section>

        <section className="workspace" id="signals">
          <div className="queue-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Triage queue</p>
                <h2>Potential signals</h2>
              </div>
              <span className="result-count">{filtered.length} shown</span>
            </div>
            <div className="filters">
              <label className="search">
                <span className="sr-only">Search signals</span>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search drug, event, detector"
                />
              </label>
              <div className="filter-row" aria-label="Filter by review status">
                {statusOrder.map((option) => (
                  <button
                    className={status === option ? "selected" : ""}
                    key={option}
                    onClick={() => setStatus(option)}
                    type="button"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            <div className="signal-list">
              {filtered.map((signal) => (
                <button
                  className={`signal-row ${selected.id === signal.id ? "current" : ""}`}
                  key={signal.id}
                  onClick={() => setSelectedId(signal.id)}
                  type="button"
                >
                  <span className="signal-name">
                    <strong>{signal.drug}</strong>
                    <small>{signal.event}</small>
                  </span>
                  <MiniTrend values={signal.trend} />
                  <span className="signal-score">
                    <strong>{signal.score.toFixed(2)}</strong>
                    <small>{signal.detector}</small>
                  </span>
                  <StatusPill status={signal.status} />
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="empty">No signals match these filters.</p>
              )}
            </div>
          </div>

          <aside className="detail-panel" aria-live="polite">
            <div className="detail-head">
              <div>
                <p className="eyebrow">Evidence review / {selected.quarter}</p>
                <h2>{selected.drug}</h2>
                <p>{selected.event}</p>
              </div>
              <StatusPill status={selected.status} />
            </div>

            <div className="metric-strip">
              <div><span>ROR</span><strong>{selected.score.toFixed(2)}</strong></div>
              <div><span>95% CI</span><strong>{selected.lower}–{selected.upper}</strong></div>
              <div><span>Reports</span><strong>{selected.cases}</strong></div>
              <div><span>Serious</span><strong>{selected.serious}</strong></div>
            </div>

            <div className="trend-card">
              <div className="trend-title">
                <div><span>Quarterly reports</span><strong>{selected.cases} current</strong></div>
                <span>2023 Q3 — 2025 Q2</span>
              </div>
              <MiniTrend values={selected.trend} />
              <div className="axis"><span>2023 Q3</span><span>2024 Q2</span><span>2025 Q2</span></div>
            </div>

            <div className="why-card">
              <h3>Why this was prioritized</h3>
              <ol>
                {selected.reasons.map((reason, index) => (
                  <li key={reason}>
                    <span>{String(index + 1).padStart(2, "0")}</span>{reason}
                  </li>
                ))}
              </ol>
            </div>

            <section className="brief-card" id="brief" aria-labelledby="brief-title">
              <div className="brief-heading">
                <div>
                  <p className="eyebrow">Constrained AI assistance</p>
                  <h3 id="brief-title">Evidence brief</h3>
                </div>
                <span className={`brief-state brief-${selected.brief.status}`}>
                  {selected.brief.status === "generated" ? "Citations verified" : "Abstained"}
                </span>
              </div>
              <strong className="brief-headline">{selected.brief.headline}</strong>
              {selected.brief.claims.map((claim) => (
                <p className="brief-claim" key={claim.text}>
                  {claim.text}{" "}
                  {claim.citationIds.map((citationId) => (
                    <a href={`#${citationId}`} key={citationId}>
                      [{selected.brief.citations.findIndex((item) => item.id === citationId) + 1}]
                    </a>
                  ))}
                </p>
              ))}
              <div className="uncertainty">
                <strong>Uncertainty</strong>
                <span>{selected.brief.uncertainty}</span>
              </div>
              <ol className="review-steps">
                {selected.brief.reviewSteps.map((step) => <li key={step}>{step}</li>)}
              </ol>
              {selected.brief.citations.length > 0 && (
                <div className="citations">
                  {selected.brief.citations.map((citation, index) => (
                    <a
                      id={citation.id}
                      href={citation.url}
                      target="_blank"
                      rel="noreferrer"
                      key={citation.id}
                    >
                      <span>{index + 1}</span>
                      <span><strong>{citation.title}</strong><small>{citation.publisher}</small></span>
                    </a>
                  ))}
                </div>
              )}
              <p className="brief-meta">
                {selected.brief.provider} · {selected.brief.model} · generated text cannot change scores
              </p>
            </section>

            <div className="provenance">
              <span>Evidence provenance</span>
              <dl>
                <div><dt>Source</dt><dd>openFDA FAERS API</dd></div>
                <div><dt>Snapshot</dt><dd>openfda-2025-q2-demo</dd></div>
                <div><dt>Criteria</dt><dd>phase3-v1 / phase4-v1</dd></div>
                <div><dt>Input digest</dt><dd>37c9…e81a</dd></div>
              </dl>
            </div>
            <button className="export" type="button" onClick={downloadBundle}>
              Download analysis bundle <span>JSON ↓</span>
            </button>
            {notice && <p className="notice" role="status">{notice}</p>}
          </aside>
        </section>

        <section className="lower-grid">
          <article className="quality-card" id="quality">
            <div className="section-heading">
              <div><p className="eyebrow">Data fitness</p><h2>Quality gate</h2></div>
              <span className="pass">All critical checks pass</span>
            </div>
            <div className="quality-bars">
              {[
                ["Required fields", 98.7],
                ["Unique reports", 99.4],
                ["Freshness", 100],
                ["Valid dates", 99.8],
              ].map(([label, value]) => (
                <div className="quality-row" key={label}>
                  <span>{label}</span>
                  <div><i style={{ width: `${value}%` }} /></div>
                  <strong>{value}%</strong>
                </div>
              ))}
            </div>
            <p className="quality-note">
              4,872 reports accepted · 31 rejected with recorded reasons ·
              newest report 18 days before analysis date
            </p>
          </article>

          <article className="evaluation-card" id="evaluation">
            <div className="section-heading">
              <div><p className="eyebrow">Walk-forward backtest</p><h2>Detector comparison</h2></div>
              <span className="reference">FDA reference v1</span>
            </div>
            <div className="metric-table" role="table" aria-label="Detector evaluation">
              <div className="table-row header" role="row">
                <span>Detector</span><span>Recall@10</span><span>Precision@10</span><span>Alerts</span>
              </div>
              {detectorMetrics.map((metric) => (
                <div className="table-row" role="row" key={metric.name}>
                  <strong>{metric.name}</strong>
                  <span>{Math.round(metric.recall * 100)}%</span>
                  <span>{Math.round(metric.precision * 100)}%</span>
                  <span>{metric.burden}</span>
                </div>
              ))}
            </div>
            <p className="quality-note">
              ML is evaluated only after sufficient prior-quarter history.
              Reference agreement is not clinical validation.
            </p>
          </article>
        </section>

        <section className="platform-card" aria-labelledby="platform-title">
          <div>
            <p className="eyebrow">Production architecture</p>
            <h2 id="platform-title">One traceable path from source to review.</h2>
            <p>
              Every stage saves a versioned artifact and digest. Statistical and
              temporal models rank signals; the evidence layer can only summarize
              retrieved sources and must abstain when grounding fails.
            </p>
          </div>
          <div className="architecture-flow" aria-label="Platform data flow">
            {["Public APIs", "Quality gates", "ROR · PRR", "Temporal ML", "Cited brief", "Expert review"].map(
              (stage, index) => (
                <div key={stage}><span>{String(index + 1).padStart(2, "0")}</span><strong>{stage}</strong></div>
              ),
            )}
          </div>
          <div className="operations">
            <span><strong>Ready</strong> API health and readiness probes</span>
            <span><strong>Audited</strong> append-only review events</span>
            <span><strong>Reproducible</strong> seeded models and source hashes</span>
          </div>
        </section>
      </div>

      <footer>
        <span>OpenSignal PH · reproducible public-health surveillance</span>
        <span>Methods documented · artifacts versioned · uncertainty visible</span>
      </footer>
    </main>
  );
}
