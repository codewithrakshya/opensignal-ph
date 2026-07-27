import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.preprocessing import RobustScaler  # type: ignore[import-untyped]

from opensignal.backtesting.models import (
    BacktestSummary,
    DetectorSummary,
    QuarterMetric,
    RankingRow,
    ReferenceEntry,
    ReferenceSet,
)
from opensignal.temporal.detector import feature_vector
from opensignal.temporal.models import TemporalFeature

DETECTORS = ("report_count", "ror", "prr", "isolation_forest")


def quarter_ordinal(value: str) -> int:
    return int(value[:4]) * 4 + int(value[-1]) - 1


@dataclass(frozen=True)
class EvaluationResult:
    rankings: list[RankingRow]
    quarter_metrics: list[QuarterMetric]
    summary: BacktestSummary


def _baseline_scores(
    current: list[TemporalFeature],
    detector: str,
) -> list[float]:
    return [float(getattr(row, detector)) for row in current]


def _walk_forward_ml_scores(
    history: list[TemporalFeature],
    current: list[TemporalFeature],
    *,
    random_state: int,
    minimum_training_rows: int,
) -> list[float] | None:
    if len(history) < minimum_training_rows:
        return None
    scaler = RobustScaler().fit([feature_vector(row) for row in history])
    model = IsolationForest(
        contamination="auto",
        n_estimators=200,
        random_state=random_state,
    ).fit(scaler.transform([feature_vector(row) for row in history]))
    return [
        float(value)
        for value in -model.decision_function(
            scaler.transform([feature_vector(row) for row in current])
        )
    ]


def _rank(
    rows: list[TemporalFeature],
    scores: list[float],
    detector: str,
    references: dict[tuple[str, str], list[str]],
) -> list[RankingRow]:
    ordered = sorted(
        zip(rows, scores, strict=True),
        key=lambda item: (-item[1], item[0].drug, item[0].event),
    )
    return [
        RankingRow(
            quarter=row.quarter,
            detector=detector,
            rank=rank,
            drug=row.drug,
            event=row.event,
            score=score,
            is_reference_signal=(row.drug, row.event) in references,
            matched_reference_ids=references.get((row.drug, row.event), []),
        )
        for rank, (row, score) in enumerate(ordered, start=1)
    ]


def evaluate(
    features: Iterable[TemporalFeature],
    reference_set: ReferenceSet,
    *,
    snapshot_id: str,
    generated_at: datetime,
    k: int,
    random_state: int,
    minimum_training_rows: int,
) -> EvaluationResult:
    feature_rows = list(features)
    quarters = sorted({row.quarter for row in feature_rows})
    rows_by_quarter: dict[str, list[TemporalFeature]] = defaultdict(list)
    for row in feature_rows:
        rows_by_quarter[row.quarter].append(row)

    matched = [
        entry for entry in reference_set.entries if entry.match_method != "unmatched"
    ]
    in_window = [entry for entry in matched if entry.signal_quarter in quarters]
    refs_by_quarter: dict[str, list[ReferenceEntry]] = defaultdict(list)
    for entry in in_window:
        refs_by_quarter[entry.signal_quarter].append(entry)

    rankings: list[RankingRow] = []
    metrics: list[QuarterMetric] = []
    top_pairs: dict[tuple[str, str], set[tuple[str, str]]] = {}
    detector_available: dict[tuple[str, str], bool] = {}

    for quarter in quarters:
        current = rows_by_quarter[quarter]
        history = [row for row in feature_rows if row.quarter < quarter]
        quarter_refs = refs_by_quarter[quarter]
        reference_lookup: dict[tuple[str, str], list[str]] = defaultdict(list)
        for entry in quarter_refs:
            assert entry.normalized_drug is not None
            assert entry.normalized_event is not None
            reference_lookup[(entry.normalized_drug, entry.normalized_event)].append(
                entry.reference_id
            )

        for detector in DETECTORS:
            scores = (
                _walk_forward_ml_scores(
                    history,
                    current,
                    random_state=random_state,
                    minimum_training_rows=minimum_training_rows,
                )
                if detector == "isolation_forest"
                else _baseline_scores(current, detector)
            )
            available = scores is not None
            detector_available[(detector, quarter)] = available
            ranked = (
                _rank(current, scores, detector, reference_lookup)
                if scores is not None
                else []
            )
            rankings.extend(ranked)
            selected = ranked[:k]
            selected_pairs = {(row.drug, row.event) for row in selected}
            top_pairs[(detector, quarter)] = selected_pairs
            hits = sum(
                (entry.normalized_drug, entry.normalized_event) in selected_pairs
                for entry in quarter_refs
            )
            eligible_count = len(quarter_refs)
            metrics.append(
                QuarterMetric(
                    quarter=quarter,
                    detector=detector,
                    available=available,
                    k=k,
                    eligible_references=eligible_count,
                    hits=hits,
                    alerts=len(selected),
                    recall_at_k=(hits / eligible_count if eligible_count else None),
                    precision_at_k=(
                        hits / len(selected) if selected and eligible_count else None
                    ),
                )
            )

    summaries: list[DetectorSummary] = []
    for detector in DETECTORS:
        available_quarters = {
            quarter for quarter in quarters if detector_available[(detector, quarter)]
        }
        eligible_entries = [
            entry for entry in in_window if entry.signal_quarter in available_quarters
        ]
        hits = 0
        lead_times: list[int] = []
        for entry in eligible_entries:
            assert entry.normalized_drug is not None
            assert entry.normalized_event is not None
            pair = (entry.normalized_drug, entry.normalized_event)
            alert_quarters = [
                quarter
                for quarter in available_quarters
                if quarter <= entry.signal_quarter
                and pair in top_pairs[(detector, quarter)]
            ]
            if pair in top_pairs[(detector, entry.signal_quarter)]:
                hits += 1
            if alert_quarters:
                earliest = min(alert_quarters)
                lead_times.append(
                    quarter_ordinal(entry.signal_quarter) - quarter_ordinal(earliest)
                )
        alerts = sum(
            len(top_pairs[(detector, quarter)]) for quarter in available_quarters
        )
        summaries.append(
            DetectorSummary(
                detector=detector,
                evaluated_quarters=len(available_quarters),
                eligible_references=len(eligible_entries),
                hits=hits,
                recall_at_k=(
                    hits / len(eligible_entries) if eligible_entries else None
                ),
                precision_at_k=(hits / alerts if alerts else None),
                median_lead_quarters=(
                    float(statistics.median(lead_times)) if lead_times else None
                ),
                detected_with_lead_time=len(lead_times),
                alert_burden=alerts,
            )
        )

    method_counts = Counter(entry.match_method for entry in reference_set.entries)
    summary = BacktestSummary(
        snapshot_id=snapshot_id,
        reference_set_id=reference_set.reference_set_id,
        generated_at=generated_at,
        k=k,
        minimum_training_rows=minimum_training_rows,
        total_references=len(reference_set.entries),
        matched_references=len(matched),
        unmatched_references=method_counts["unmatched"],
        out_of_window_references=len(matched) - len(in_window),
        match_method_counts=dict(sorted(method_counts.items())),
        detector_summaries=summaries,
        interpretation=(
            "Retrospective ranking evaluation against FDA-posted potential "
            "signals. Metrics measure agreement with the reference set, not "
            "causality, incidence, or clinical validity."
        ),
    )
    return EvaluationResult(rankings, metrics, summary)
