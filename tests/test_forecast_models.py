import pandas as pd

from revenue_forecast_dashboard.model import (
    build_model_registry,
    evaluate_predictions,
    get_model_by_name,
)


def test_model_registry_contains_baselines_and_candidate() -> None:
    names = [model.name for model in build_model_registry(max_forecast_days=7)]

    assert "SeasonalNaiveBaseline" in names
    assert "SeasonalPromotionTrendForecaster" in names
    assert len(names) >= 5


def test_get_model_by_name_falls_back_to_forecaster() -> None:
    model = get_model_by_name("modelo-inexistente", max_forecast_days=7)

    assert model.name == "SeasonalPromotionTrendForecaster"
    assert model.max_forecast_days == 7


def test_evaluate_predictions_returns_business_metrics() -> None:
    metrics = evaluate_predictions(
        pd.Series([100.0, 120.0, 0.0]),
        pd.Series([90.0, 130.0, 5.0]),
    )

    assert {"mae", "rmse", "rmsle", "smape", "wape", "bias"}.issubset(metrics)
    assert metrics["wape"] > 0
