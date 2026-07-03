from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from revenue_forecast_dashboard.data import SCENARIOS, load_history
from revenue_forecast_dashboard.model import build_model_registry, evaluate_predictions

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
VALIDATION_DAYS = 16
PRIMARY_BASELINE = "SeasonalNaiveBaseline"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    latest_date = history["date"].max()
    cutoff_date = latest_date - pd.Timedelta(VALIDATION_DAYS, unit="D")

    train = history[history["date"] <= cutoff_date].copy()
    validation = history[history["date"] > cutoff_date].copy()
    validation_dates = pd.date_range(
        cutoff_date + pd.Timedelta(1, unit="D"),
        periods=VALIDATION_DAYS,
    )
    future_promotions = {
        (pd.Timestamp(row.date), int(row.store_nbr), str(row.family)): float(row.onpromotion)
        for row in validation.itertuples(index=False)
    }

    comparison_rows: list[dict[str, object]] = []
    scored_by_model: dict[str, pd.DataFrame] = {}

    for model in build_model_registry(max_forecast_days=VALIDATION_DAYS):
        print(f"Avaliando {model.name}...")
        forecast = model.predict(
            train,
            future_promotions,
            SCENARIOS,
            forecast_dates=validation_dates,
        )
        expected = forecast[forecast["scenario"] == "esperado"][
            ["date", "store_nbr", "family", "revenue"]
        ].rename(columns={"revenue": "prediction"})

        scored = validation.merge(expected, on=["date", "store_nbr", "family"], how="inner")
        scored_by_model[model.name] = scored

        metrics = evaluate_predictions(scored["revenue"], scored["prediction"])
        comparison_rows.append(
            {
                "model": model.name,
                "model_role": "baseline" if "Baseline" in model.name else "candidate",
                "validation_days": VALIDATION_DAYS,
                "train_end": cutoff_date.strftime("%Y-%m-%d"),
                "validation_start": validation_dates.min().strftime("%Y-%m-%d"),
                "validation_end": validation_dates.max().strftime("%Y-%m-%d"),
                "rows_scored": int(len(scored)),
                "series_scored": int(scored[["store_nbr", "family"]].drop_duplicates().shape[0]),
                **metrics,
            }
        )

    comparison = pd.DataFrame(comparison_rows).sort_values(
        ["wape", "smape", "rmse"], ascending=True
    )
    baseline = comparison[comparison["model"] == PRIMARY_BASELINE].iloc[0]
    winner = comparison.iloc[0].to_dict()
    winner["selected_by"] = "lowest_wape"
    winner["baseline_model"] = PRIMARY_BASELINE
    winner["baseline_wape"] = float(baseline["wape"])
    winner["wape_lift_vs_baseline"] = (float(baseline["wape"]) - float(winner["wape"])) / float(
        baseline["wape"]
    )
    winner["models_tested"] = int(len(comparison))
    winner["benchmark_models"] = comparison["model"].tolist()

    best_model_name = str(winner["model"])
    best_scored = scored_by_model[best_model_name]
    by_family = _metrics_by_family(best_scored)

    (REPORTS_DIR / "model_metrics.json").write_text(
        json.dumps(winner, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (REPORTS_DIR / "model_comparison.json").write_text(
        comparison.to_json(orient="records", indent=2, force_ascii=False),
        encoding="utf-8",
    )
    comparison.to_csv(REPORTS_DIR / "model_comparison.csv", index=False)
    by_family.to_csv(REPORTS_DIR / "model_metrics_by_family.csv", index=False)

    print("\nComparativo:")
    print(
        comparison[
            [
                "model",
                "model_role",
                "wape",
                "smape",
                "rmse",
                "rmsle",
                "bias",
                "rows_scored",
            ]
        ].to_string(index=False)
    )
    print("\nModelo selecionado:")
    print(json.dumps(winner, indent=2, ensure_ascii=False))


def _metrics_by_family(scored: pd.DataFrame) -> pd.DataFrame:
    family_metrics = []
    for family, group in scored.groupby("family", observed=True):
        row = {"family": family}
        row.update(evaluate_predictions(group["revenue"], group["prediction"]))
        family_metrics.append(row)
    return pd.DataFrame(family_metrics).sort_values("wape")


if __name__ == "__main__":
    main()
