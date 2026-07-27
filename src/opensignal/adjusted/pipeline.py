import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from opensignal.adjusted.models import (
    AdjustedEstimate,
    AdjustedRunMetadata,
    SensitivityResult,
    StratumEstimate,
)
from opensignal.adjusted.statistics import (
    StratumTable,
    heterogeneity,
    mantel_haenszel_or,
    stratum_estimates,
)
from opensignal.detection.ror import ContingencyTable, ReportingOddsRatio
from opensignal.ingestion.storage import atomic_write, canonical_json_bytes


@dataclass(frozen=True)
class Profile:
    report_id: str
    drugs: frozenset[str]
    events: frozenset[str]
    age_group: str
    sex: str
    year: int

    @property
    def stratum(self) -> str:
        return f"age={self.age_group}|sex={self.sex}|year={self.year}"


@dataclass(frozen=True)
class AdjustedResult:
    snapshot_id: str
    results_written: int
    sensitivity_path: str
    metadata_path: str


class CovariateAdjustedPipeline:
    source = "openfda"

    def __init__(
        self,
        data_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        random_state: int = 42,
    ) -> None:
        self.data_dir = data_dir
        self.clock = clock or (lambda: datetime.now(UTC))
        self.random_state = random_state

    def run(
        self,
        snapshot_id: str,
        comparator_sets: Path | None = None,
    ) -> AdjustedResult:
        curated = (
            self.data_dir
            / "curated"
            / self.source
            / snapshot_id
            / "drug_event_pairs.jsonl"
        )
        content = curated.read_bytes()
        profiles = self._profiles(content)
        comparators: dict[str, list[str]] = (
            json.loads(comparator_sets.read_text(encoding="utf-8"))
            if comparator_sets
            else {}
        )
        pairs = sorted(
            {
                (drug, event)
                for profile in profiles
                for drug in profile.drugs
                for event in profile.events
            }
        )
        generated_at = self.clock()
        results = [
            self._analyze(
                profiles,
                snapshot_id=snapshot_id,
                drug=drug,
                event=event,
                generated_at=generated_at,
                comparator_drugs=comparators.get(drug, []),
            )
            for drug, event in pairs
        ]
        output = self.data_dir / "analytics" / self.source / snapshot_id / "adjusted"
        sensitivity_path = output / "sensitivity.jsonl"
        metadata_path = output / "metadata.json"
        lines = "".join(
            json.dumps(
                result.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for result in results
        ).encode()
        atomic_write(sensitivity_path, lines)
        metadata = AdjustedRunMetadata(
            snapshot_id=snapshot_id,
            generated_at=generated_at,
            curated_input_sha256=hashlib.sha256(content).hexdigest(),
            results_written=len(results),
        )
        atomic_write(
            metadata_path,
            canonical_json_bytes(metadata.model_dump(mode="json")),
        )
        return AdjustedResult(
            snapshot_id=snapshot_id,
            results_written=len(results),
            sensitivity_path=str(sensitivity_path.relative_to(self.data_dir)),
            metadata_path=str(metadata_path.relative_to(self.data_dir)),
        )

    def _analyze(
        self,
        profiles: list[Profile],
        *,
        snapshot_id: str,
        drug: str,
        event: str,
        generated_at: datetime,
        comparator_drugs: list[str],
    ) -> SensitivityResult:
        crude_table = self._table(profiles, drug, event)
        crude = ReportingOddsRatio().score(
            drug=drug,
            event=event,
            analysis_date=generated_at.date(),
            inputs=crude_table,
        )
        groups: dict[str, list[Profile]] = {}
        for profile in profiles:
            groups.setdefault(profile.stratum, []).append(profile)
        strata = [
            StratumTable(name=name, table=self._table(group, drug, event))
            for name, group in sorted(groups.items())
            if len(group) >= 4
        ]
        mh, mh_lower, mh_upper = mantel_haenszel_or(strata)
        estimates = stratum_estimates(strata)
        q_value, q_df, q_p = heterogeneity(estimates)
        logistic = self._penalized_logistic(profiles, drug, event)
        bayesian = self._hierarchical_bayesian(profiles, drug, event)
        active_comparator = self._active_comparator(
            profiles, drug, event, comparator_drugs
        )
        return SensitivityResult(
            snapshot_id=snapshot_id,
            drug=drug,
            event=event,
            generated_at=generated_at,
            crude_ror=crude.score,
            crude_lower=crude.lower_bound or 0.0,
            crude_upper=crude.upper_bound or math.inf,
            mantel_haenszel=AdjustedEstimate(
                method="mantel_haenszel_ror",
                estimate=mh,
                lower_bound=mh_lower,
                upper_bound=mh_upper,
                covariates=["patient_age_group", "patient_sex", "calendar_year"],
                reports_used=len(profiles),
                reports_excluded_missing=0,
                interpretation="Common reporting odds ratio across observed strata.",
            ),
            penalized_logistic=logistic,
            hierarchical_bayesian=bayesian,
            active_comparator=active_comparator,
            strata=[
                StratumEstimate(
                    stratum=item.name,
                    reports=sum(
                        (item.table.a, item.table.b, item.table.c, item.table.d)
                    ),
                    cases=item.table.a,
                    ror=ror,
                    lower_bound=lower,
                    upper_bound=upper,
                    prr=prr,
                )
                for item, ror, lower, upper, prr in estimates
            ],
            heterogeneity_q=q_value,
            heterogeneity_df=q_df,
            heterogeneity_p_approx=q_p,
        )

    def _active_comparator(
        self,
        profiles: list[Profile],
        drug: str,
        event: str,
        comparator_drugs: list[str],
    ) -> AdjustedEstimate | None:
        normalized = {item.upper() for item in comparator_drugs}
        if not normalized:
            return None
        restricted = [
            profile
            for profile in profiles
            if drug in profile.drugs or bool(profile.drugs & normalized)
        ]
        if not restricted:
            return None
        table = ContingencyTable(
            a=sum(
                drug in profile.drugs and event in profile.events
                for profile in restricted
            ),
            b=sum(
                drug in profile.drugs and event not in profile.events
                for profile in restricted
            ),
            c=sum(
                drug not in profile.drugs
                and bool(profile.drugs & normalized)
                and event in profile.events
                for profile in restricted
            ),
            d=sum(
                drug not in profile.drugs
                and bool(profile.drugs & normalized)
                and event not in profile.events
                for profile in restricted
            ),
        )
        score = ReportingOddsRatio().score(
            drug=drug,
            event=event,
            analysis_date=self.clock().date(),
            inputs=table,
        )
        return AdjustedEstimate(
            method="active_comparator_ror",
            estimate=score.score,
            lower_bound=score.lower_bound,
            upper_bound=score.upper_bound,
            covariates=["therapeutic_comparator_set"],
            reports_used=len(restricted),
            reports_excluded_missing=len(profiles) - len(restricted),
            interpretation=(
                "Reporting odds compared only with the supplied therapeutic "
                "comparator medicines."
            ),
        )

    def _penalized_logistic(
        self,
        profiles: list[Profile],
        drug: str,
        event: str,
    ) -> AdjustedEstimate:
        try:
            np: Any = import_module("numpy")
            from sklearn.feature_extraction import (  # type: ignore[import-untyped]
                DictVectorizer,
            )
            from sklearn.linear_model import (  # type: ignore[import-untyped]
                LogisticRegression,
            )
        except ImportError as error:
            raise RuntimeError(
                "Install the 'ml' dependency for adjusted regression."
            ) from error
        rows = [
            {
                "target_drug": float(drug in profile.drugs),
                f"age={profile.age_group}": 1.0,
                f"sex={profile.sex}": 1.0,
                f"year={profile.year}": 1.0,
            }
            for profile in profiles
        ]
        outcome = np.asarray([int(event in profile.events) for profile in profiles])
        vectorizer = DictVectorizer(sparse=False)
        design = vectorizer.fit_transform(rows)
        if len(set(outcome.tolist())) < 2:
            return AdjustedEstimate(
                method="l2_penalized_logistic_ror",
                estimate=1.0,
                covariates=["patient_age_group", "patient_sex", "calendar_year"],
                reports_used=len(profiles),
                reports_excluded_missing=0,
                interpretation=(
                    "Outcome had no variation; adjusted estimate unavailable."
                ),
            )
        model = LogisticRegression(
            C=1.0,
            solver="liblinear",
            random_state=self.random_state,
        ).fit(design, outcome)
        index = list(vectorizer.get_feature_names_out()).index("target_drug")
        estimate = math.exp(float(model.coef_[0][index]))
        return AdjustedEstimate(
            method="l2_penalized_logistic_ror",
            estimate=estimate,
            covariates=["patient_age_group", "patient_sex", "calendar_year"],
            reports_used=len(profiles),
            reports_excluded_missing=0,
            interpretation=(
                "L2-regularized adjusted reporting odds ratio; confidence "
                "limits are omitted because penalized-model uncertainty requires "
                "a separately validated bootstrap or Bayesian interval."
            ),
        )

    def _hierarchical_bayesian(
        self,
        profiles: list[Profile],
        drug: str,
        event: str,
    ) -> AdjustedEstimate:
        try:
            np: Any = import_module("numpy")
        except ImportError as error:
            raise RuntimeError(
                "Install the 'ml' dependency for Bayesian sensitivity analysis."
            ) from error
        exposed = [profile for profile in profiles if drug in profile.drugs]
        comparison = [profile for profile in profiles if drug not in profile.drugs]
        overall_rate = sum(event in item.events for item in profiles) / len(profiles)
        prior_strength = 10.0
        alpha = 1.0 + prior_strength * overall_rate
        beta = 1.0 + prior_strength * (1 - overall_rate)
        rng = np.random.default_rng(self.random_state)
        exp_event = sum(event in item.events for item in exposed)
        cmp_event = sum(event in item.events for item in comparison)
        exp_draw = rng.beta(
            alpha + exp_event,
            beta + len(exposed) - exp_event,
            10_000,
        )
        cmp_draw = rng.beta(
            alpha + cmp_event,
            beta + len(comparison) - cmp_event,
            10_000,
        )
        draws = (exp_draw / (1 - exp_draw)) / (cmp_draw / (1 - cmp_draw))
        return AdjustedEstimate(
            method="hierarchical_beta_binomial_ror",
            estimate=float(np.median(draws)),
            lower_bound=float(np.quantile(draws, 0.025)),
            upper_bound=float(np.quantile(draws, 0.975)),
            covariates=["global_event_rate_partial_pooling"],
            reports_used=len(profiles),
            reports_excluded_missing=0,
            interpretation=(
                "Empirical hierarchical Beta-Binomial shrinkage toward the "
                "global event-reporting rate."
            ),
        )

    @staticmethod
    def _table(
        profiles: list[Profile],
        drug: str,
        event: str,
    ) -> ContingencyTable:
        return ContingencyTable(
            a=sum(drug in p.drugs and event in p.events for p in profiles),
            b=sum(drug in p.drugs and event not in p.events for p in profiles),
            c=sum(drug not in p.drugs and event in p.events for p in profiles),
            d=sum(drug not in p.drugs and event not in p.events for p in profiles),
        )

    @staticmethod
    def _profiles(content: bytes) -> list[Profile]:
        reports: dict[str, dict[str, Any]] = {}
        for line in content.splitlines():
            if not line:
                continue
            row = json.loads(line)
            report = reports.setdefault(
                str(row["report_id"]),
                {
                    "drugs": set(),
                    "events": set(),
                    "age_group": row.get("patient_age_group", "unknown"),
                    "sex": row.get("patient_sex", "unknown"),
                    "year": int(str(row["received_date"])[:4]),
                },
            )
            report["drugs"].add(str(row["drug_name"]).upper())
            report["events"].add(str(row["reaction"]).upper())
        return [
            Profile(
                report_id=report_id,
                drugs=frozenset(value["drugs"]),
                events=frozenset(value["events"]),
                age_group=str(value["age_group"]),
                sex=str(value["sex"]),
                year=int(value["year"]),
            )
            for report_id, value in sorted(reports.items())
        ]
