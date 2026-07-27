import math
import statistics
from collections import defaultdict
from typing import Any

from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.preprocessing import RobustScaler  # type: ignore[import-untyped]

from opensignal.temporal.models import TemporalFeature, TemporalSignal

FEATURE_NAMES = [
    "report_count",
    "reporting_share",
    "quarter_over_quarter_growth",
    "serious_proportion",
    "ror",
    "prr",
]


def feature_vector(row: TemporalFeature) -> list[float]:
    return [
        float(row.report_count),
        row.reporting_share,
        row.quarter_over_quarter_growth,
        row.serious_proportion,
        math.log1p(row.ror),
        math.log1p(row.prr),
    ]


def robust_change_scores(
    features: list[TemporalFeature],
    minimum_history: int,
) -> dict[tuple[str, str, str], tuple[float, bool, int]]:
    histories: dict[tuple[str, str], list[int]] = defaultdict(list)
    results: dict[tuple[str, str, str], tuple[float, bool, int]] = {}
    for row in sorted(features, key=lambda item: item.quarter):
        key = (row.drug, row.event)
        history = histories[key]
        score = 0.0
        if len(history) >= minimum_history:
            values = [float(value) for value in history]
            median = statistics.median(values)
            mad = statistics.median(abs(value - median) for value in values)
            scale = max(1.4826 * mad, 1.0)
            score = (row.report_count - median) / scale
        results[(row.drug, row.event, row.quarter)] = (
            score,
            score >= 3.5,
            len(history),
        )
        history.append(row.report_count)
    return results


def fit_temporal_detector(
    features: list[TemporalFeature],
    *,
    contamination: float,
    random_state: int,
    minimum_history: int,
) -> tuple[dict[str, Any], list[TemporalSignal]]:
    if len(features) < 2:
        raise ValueError("Temporal modeling requires at least two feature rows")
    matrix = [feature_vector(row) for row in features]
    scaler = RobustScaler().fit(matrix)
    transformed = scaler.transform(matrix)
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=200,
    ).fit(transformed)
    anomaly_scores = -model.decision_function(transformed)
    predictions = model.predict(transformed)
    changes = robust_change_scores(features, minimum_history)

    signals: list[TemporalSignal] = []
    for index, row in enumerate(features):
        deviations = {
            name: round(abs(float(transformed[index, position])), 6)
            for position, name in enumerate(FEATURE_NAMES)
        }
        ranked = sorted(
            deviations, key=lambda name: deviations[name], reverse=True
        )
        change_score, is_change, history_count = changes[
            (row.drug, row.event, row.quarter)
        ]
        signals.append(
            TemporalSignal(
                drug=row.drug,
                event=row.event,
                quarter=row.quarter,
                quarter_end=row.quarter_end,
                detector="isolation_forest",
                anomaly_score=float(anomaly_scores[index]),
                is_anomaly=bool(predictions[index] == -1),
                change_score=change_score,
                is_change_point=is_change,
                baseline_quarters=history_count,
                feature_contributions={name: deviations[name] for name in ranked},
                explanation=(
                    "Isolation Forest prioritization; contribution values are "
                    "absolute robust-scaled feature deviations, not causal effects."
                ),
            )
        )
    artifact: dict[str, Any] = {
        "scaler": scaler,
        "model": model,
        "feature_names": FEATURE_NAMES,
    }
    return artifact, signals
