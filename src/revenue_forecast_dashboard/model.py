from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RetailForecastModel:
    max_forecast_days: int = 90
    lookback_days: int = 112

    name: str = "RetailForecastModel"

    def predict(
        self,
        history: pd.DataFrame,
        future_promotions: dict[tuple[pd.Timestamp, int, str], float],
        scenarios: dict[str, dict[str, object]],
        forecast_dates: pd.DatetimeIndex | None = None,
    ) -> pd.DataFrame:
        latest_date = history["date"].max()
        if forecast_dates is None:
            forecast_dates = pd.date_range(
                latest_date + pd.Timedelta(1, unit="D"),
                periods=self.max_forecast_days,
            )

        records: list[dict[str, object]] = []
        grouped = history.groupby(["store_nbr", "store", "region", "family"], observed=True)

        for (store_nbr, store, region, family), series in grouped:
            series = series.sort_values("date")
            recent = series[
                series["date"] >= latest_date - pd.Timedelta(self.lookback_days, unit="D")
            ]
            if recent.empty:
                recent = series.tail(self.lookback_days)

            profile = self._fit_series_profile(recent)
            for horizon_idx, date in enumerate(forecast_dates):
                onpromotion = future_promotions.get(
                    (pd.Timestamp(date), int(store_nbr), str(family)),
                    profile["default_promotion"],
                )
                expected_sales = self._predict_expected_sales(
                    profile,
                    pd.Timestamp(date),
                    horizon_idx,
                    onpromotion,
                )
                risk_score = self._risk_score(profile, expected_sales, horizon_idx, onpromotion)
                confidence = float(
                    np.clip(0.92 - risk_score * 0.24 - horizon_idx / 750, 0.64, 0.94)
                )

                for scenario_key, scenario in scenarios.items():
                    records.append(
                        {
                            "date": date,
                            "store_nbr": int(store_nbr),
                            "store": store,
                            "region": region,
                            "family": str(family),
                            "scenario": scenario_key,
                            "revenue": expected_sales * float(scenario["multiplier"]),
                            "onpromotion": float(onpromotion),
                            "promo": bool(onpromotion > 0),
                            "risk_score": risk_score,
                            "confidence": confidence,
                            "model": self.name,
                        }
                    )

        return pd.DataFrame(records)

    def _fit_series_profile(self, recent: pd.DataFrame) -> dict[str, object]:
        recent_mean = float(recent.tail(28)["revenue"].mean())
        previous_mean = (
            float(recent.iloc[-56:-28]["revenue"].mean()) if len(recent) >= 56 else recent_mean
        )
        last14_mean = float(recent.tail(14)["revenue"].mean())
        weekday_mean = recent.groupby(recent["date"].dt.weekday)["revenue"].mean().to_dict()
        last_by_weekday = recent.groupby(recent["date"].dt.weekday)["revenue"].last().to_dict()
        fallback_sales = float(recent["revenue"].mean())
        last_value = float(recent.tail(1)["revenue"].iloc[0])

        return {
            "recent_mean": recent_mean,
            "previous_mean": previous_mean,
            "last14_mean": last14_mean,
            "weekday_mean": weekday_mean,
            "last_by_weekday": last_by_weekday,
            "fallback_sales": fallback_sales,
            "last_value": last_value,
            "volatility": _safe_ratio(float(recent["revenue"].std(ddof=0)), fallback_sales),
            "trend": float(
                np.clip(_safe_ratio(recent_mean - previous_mean, previous_mean), -0.25, 0.25)
            ),
            "default_promotion": float(recent["onpromotion"].median()),
            "promo_p75": float(recent["onpromotion"].quantile(0.75)),
        }

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        raise NotImplementedError

    def _risk_score(
        self,
        profile: dict[str, object],
        expected_sales: float,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        risk_score = (
            0.18
            + min(float(profile["volatility"]), 1.4) * 0.34
            + horizon_idx / 260
            + (0.08 if onpromotion > float(profile["promo_p75"]) and onpromotion > 0 else 0)
            + (0.06 if expected_sales > float(profile["recent_mean"]) * 1.22 else 0)
        )
        return float(np.clip(risk_score, 0.05, 0.95))


@dataclass(frozen=True)
class LastValueBaseline(RetailForecastModel):
    name: str = "LastValueBaseline"

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        return max(float(profile["last_value"]), 0.0)


@dataclass(frozen=True)
class MovingAverageBaseline(RetailForecastModel):
    name: str = "MovingAverageBaseline"

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        return max(float(profile["recent_mean"]), 0.0)


@dataclass(frozen=True)
class SeasonalNaiveBaseline(RetailForecastModel):
    name: str = "SeasonalNaiveBaseline"

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        value = profile["last_by_weekday"].get(date.weekday(), profile["fallback_sales"])
        return max(float(value), 0.0)


@dataclass(frozen=True)
class WeekdayAverageBaseline(RetailForecastModel):
    name: str = "WeekdayAverageBaseline"

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        value = profile["weekday_mean"].get(date.weekday(), profile["fallback_sales"])
        return max(float(value), 0.0)


@dataclass(frozen=True)
class SeasonalPromotionTrendForecaster(RetailForecastModel):
    name: str = "SeasonalPromotionTrendForecaster"

    def _predict_expected_sales(
        self,
        profile: dict[str, object],
        date: pd.Timestamp,
        horizon_idx: int,
        onpromotion: float,
    ) -> float:
        weekday_value = float(
            profile["weekday_mean"].get(date.weekday(), profile["fallback_sales"])
        )
        base_sales = (
            0.55 * weekday_value
            + 0.30 * float(profile["recent_mean"])
            + 0.15 * float(profile["last14_mean"])
        )
        trend_factor = 1 + float(profile["trend"]) * ((horizon_idx + 1) / self.max_forecast_days)
        promo_factor = 1 + min(float(onpromotion), 80.0) * 0.004
        return max(base_sales * trend_factor * promo_factor, 0.0)


def build_model_registry(max_forecast_days: int = 90) -> list[RetailForecastModel]:
    return [
        LastValueBaseline(max_forecast_days=max_forecast_days),
        MovingAverageBaseline(max_forecast_days=max_forecast_days),
        SeasonalNaiveBaseline(max_forecast_days=max_forecast_days),
        WeekdayAverageBaseline(max_forecast_days=max_forecast_days),
        SeasonalPromotionTrendForecaster(max_forecast_days=max_forecast_days),
    ]


def get_model_by_name(name: str, max_forecast_days: int = 90) -> RetailForecastModel:
    models = {model.name: model for model in build_model_registry(max_forecast_days)}
    return models.get(name, SeasonalPromotionTrendForecaster(max_forecast_days=max_forecast_days))


def evaluate_predictions(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    actual_values = actual.astype("float64").clip(lower=0).to_numpy()
    predicted_values = predicted.astype("float64").clip(lower=0).to_numpy()
    error = predicted_values - actual_values
    abs_error = np.abs(error)

    denominator = np.abs(actual_values) + np.abs(predicted_values)
    smape_terms = np.divide(
        2 * abs_error,
        denominator,
        out=np.zeros_like(abs_error, dtype="float64"),
        where=denominator != 0,
    )
    actual_sum = actual_values.sum()

    return {
        "mae": float(abs_error.mean()),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "rmsle": float(
            np.sqrt(np.mean((np.log1p(predicted_values) - np.log1p(actual_values)) ** 2))
        ),
        "smape": float(smape_terms.mean()),
        "wape": float(abs_error.sum() / actual_sum) if actual_sum else 0.0,
        "bias": float(error.sum() / actual_sum) if actual_sum else 0.0,
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)
