from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from revenue_forecast_dashboard.model import get_model_by_name

MAX_FORECAST_DAYS = 90
REQUIRED_FILES = ("train.csv", "stores.csv")
OPTIONAL_FILES = ("test.csv", "transactions.csv", "oil.csv", "holidays_events.csv")
COMPETITION_SLUG = "store-sales-time-series-forecasting"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCENARIOS = {
    "conservador": {
        "label": "Conservador",
        "multiplier": 0.92,
        "color": "#94A3B8",
    },
    "esperado": {
        "label": "Esperado",
        "multiplier": 1.00,
        "color": "#2563EB",
    },
    "otimista": {
        "label": "Otimista",
        "multiplier": 1.11,
        "color": "#16A34A",
    },
}


class DataNotAvailableError(RuntimeError):
    """Raised when the real Store Sales files are not available locally."""


def get_data_dir(data_dir: str | Path | None = None) -> Path:
    if data_dir is not None:
        return Path(data_dir).expanduser().resolve()
    configured = os.getenv("STORE_SALES_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / "data" / "raw").resolve()


def missing_required_files(data_dir: str | Path | None = None) -> list[str]:
    directory = get_data_dir(data_dir)
    return [filename for filename in REQUIRED_FILES if not (directory / filename).exists()]


def get_store_names() -> list[str]:
    directory = get_data_dir()
    try:
        stores = _load_stores(directory)
    except DataNotAvailableError:
        return []
    return sorted(stores["store"].dropna().unique().tolist())


def get_family_names() -> list[str]:
    train_path = get_data_dir() / "train.csv"
    if not train_path.exists():
        return []

    families = pd.read_csv(train_path, usecols=["family"], dtype={"family": "category"})
    return sorted(families["family"].astype("string").dropna().unique().tolist())


def load_real_data(data_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    directory = get_data_dir(data_dir)
    return _load_real_data_cached(str(directory))


def load_history(data_dir: str | Path | None = None) -> pd.DataFrame:
    directory = get_data_dir(data_dir)
    missing = missing_required_files(directory)
    if missing:
        files = ", ".join(missing)
        raise DataNotAvailableError(
            f"Arquivos reais ausentes em {directory}: {files}. "
            f"Baixe a competição Kaggle {COMPETITION_SLUG} e extraia os CSVs nessa pasta."
        )
    return _load_history(directory)


@lru_cache(maxsize=4)
def _load_real_data_cached(data_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    directory = Path(data_dir)
    missing = missing_required_files(directory)
    if missing:
        files = ", ".join(missing)
        raise DataNotAvailableError(
            f"Arquivos reais ausentes em {directory}: {files}. "
            f"Baixe a competição Kaggle {COMPETITION_SLUG} e extraia os CSVs nessa pasta."
        )

    history = load_history(directory)
    forecast = _build_forecast(history, directory)
    return history, forecast


def get_dashboard_slice(
    store: str,
    family: str,
    horizon_days: int,
    history_window_days: int,
    data_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    historical, forecast = load_real_data(data_dir)

    historical = _apply_common_filters(historical, store, family)
    forecast = _apply_common_filters(forecast, store, family)

    forecast_start = forecast["date"].min()
    forecast_end = forecast_start + pd.Timedelta(horizon_days - 1, unit="D")
    forecast = forecast[forecast["date"].between(forecast_start, forecast_end)].copy()

    display_start = forecast_start - pd.Timedelta(history_window_days, unit="D")
    display_history = historical[historical["date"] >= display_start].copy()

    comparison_start = forecast_start - pd.Timedelta(horizon_days, unit="D")
    comparison_history = historical[historical["date"] >= comparison_start].copy()

    return display_history, comparison_history, forecast


def build_summary(
    comparison_history: pd.DataFrame, forecast: pd.DataFrame, scenario: str
) -> dict[str, float]:
    scenario_forecast = forecast[forecast["scenario"] == scenario]
    sales = float(scenario_forecast["revenue"].sum())
    previous_sales = float(comparison_history["revenue"].sum())
    promo_sales = float(scenario_forecast.loc[scenario_forecast["promo"], "revenue"].sum())

    delta_pct = _safe_ratio(sales - previous_sales, previous_sales)
    confidence = _weighted_average(
        scenario_forecast["confidence"],
        scenario_forecast["revenue"],
        default=0.0,
    )
    risk_rate = _weighted_average(
        scenario_forecast["risk_score"],
        scenario_forecast["revenue"],
        default=0.0,
    )
    promo_share = _safe_ratio(promo_sales, sales)
    critical_count = int((scenario_forecast["risk_score"] >= 0.62).sum())

    return {
        "revenue": sales,
        "previous_revenue": previous_sales,
        "delta_pct": delta_pct,
        "confidence": confidence,
        "risk_rate": risk_rate,
        "promo_revenue": promo_sales,
        "promo_share": promo_share,
        "critical_count": critical_count,
    }


def build_recommendations_table(
    comparison_history: pd.DataFrame,
    forecast: pd.DataFrame,
    scenario: str,
    limit: int = 10,
) -> pd.DataFrame:
    scenario_forecast = forecast[forecast["scenario"] == scenario].copy()
    scenario_forecast["promo_revenue"] = np.where(
        scenario_forecast["promo"], scenario_forecast["revenue"], 0.0
    )

    plan = (
        scenario_forecast.groupby(["store", "family"], as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            risk_score=("risk_score", "mean"),
            confidence=("confidence", "mean"),
            promo_days=("promo", "sum"),
            promo_revenue=("promo_revenue", "sum"),
            onpromotion=("onpromotion", "sum"),
        )
        .reset_index(drop=True)
    )
    baseline = (
        comparison_history.groupby(["store", "family"], as_index=False)
        .agg(previous_revenue=("revenue", "sum"))
        .reset_index(drop=True)
    )

    table = plan.merge(baseline, on=["store", "family"], how="left")
    table["previous_revenue"] = table["previous_revenue"].fillna(0)
    table["delta_pct"] = table.apply(
        lambda row: _safe_ratio(row["revenue"] - row["previous_revenue"], row["previous_revenue"]),
        axis=1,
    )
    table["promo_share"] = table.apply(
        lambda row: _safe_ratio(row["promo_revenue"], row["revenue"]), axis=1
    )
    table["status"] = table.apply(_classify_status, axis=1)
    table["recommended_action"] = table.apply(_recommend_action, axis=1)
    table["priority"] = table["risk_score"] * 0.58 + table["revenue"].rank(pct=True) * 0.32

    return (
        table.sort_values(["priority", "revenue"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def _load_history(directory: Path) -> pd.DataFrame:
    train = pd.read_csv(
        directory / "train.csv",
        usecols=["date", "store_nbr", "family", "sales", "onpromotion"],
        parse_dates=["date"],
        dtype={
            "store_nbr": "int16",
            "family": "category",
            "sales": "float32",
            "onpromotion": "int16",
        },
    )
    stores = _load_stores(directory)

    history = train.merge(stores, on="store_nbr", how="left")
    history["sales"] = history["sales"].clip(lower=0)
    history["revenue"] = history["sales"].astype("float64")
    history["promo"] = history["onpromotion"] > 0
    history["family"] = history["family"].astype("string")

    return history[
        [
            "date",
            "store_nbr",
            "store",
            "region",
            "family",
            "revenue",
            "onpromotion",
            "promo",
        ]
    ].sort_values(["date", "store_nbr", "family"])


def _load_stores(directory: Path) -> pd.DataFrame:
    store_path = directory / "stores.csv"
    if not store_path.exists():
        raise DataNotAvailableError(
            f"Arquivo stores.csv ausente em {directory}. "
            f"Baixe a competição Kaggle {COMPETITION_SLUG}."
        )

    stores = pd.read_csv(
        store_path,
        dtype={
            "store_nbr": "int16",
            "city": "string",
            "state": "string",
            "type": "string",
            "cluster": "int16",
        },
    )
    city = stores["city"].fillna("Loja").astype("string")
    stores["store"] = city + " - Loja " + stores["store_nbr"].astype("string")
    stores["region"] = stores["state"].fillna(stores["city"]).fillna("Ecuador")
    return stores[["store_nbr", "store", "region"]]


def _build_forecast(history: pd.DataFrame, directory: Path) -> pd.DataFrame:
    future_promotions = _load_future_promotions(directory)
    model = _get_selected_model(MAX_FORECAST_DAYS)
    return model.predict(history, future_promotions, SCENARIOS)


def _get_selected_model(max_forecast_days: int):
    configured = os.getenv("FORECAST_MODEL_NAME")
    if configured:
        return get_model_by_name(configured, max_forecast_days=max_forecast_days)

    metrics_path = PROJECT_ROOT / "reports" / "model_metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        return get_model_by_name(str(metrics.get("model", "")), max_forecast_days=max_forecast_days)

    return get_model_by_name(
        "SeasonalPromotionTrendForecaster", max_forecast_days=max_forecast_days
    )


def _load_future_promotions(directory: Path) -> dict[tuple[pd.Timestamp, int, str], float]:
    test_path = directory / "test.csv"
    if not test_path.exists():
        return {}

    test = pd.read_csv(
        test_path,
        usecols=["date", "store_nbr", "family", "onpromotion"],
        parse_dates=["date"],
        dtype={
            "store_nbr": "int16",
            "family": "string",
            "onpromotion": "int16",
        },
    )
    return {
        (pd.Timestamp(row.date), int(row.store_nbr), str(row.family)): float(row.onpromotion)
        for row in test.itertuples(index=False)
    }


def _apply_common_filters(dataframe: pd.DataFrame, store: str, family: str) -> pd.DataFrame:
    filtered = dataframe
    if store != "all":
        filtered = filtered[filtered["store"] == store]
    if family != "all":
        filtered = filtered[filtered["family"] == family]
    return filtered


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)


def _weighted_average(values: pd.Series, weights: pd.Series, default: float) -> float:
    if values.empty or weights.sum() == 0:
        return default
    return float(np.average(values, weights=weights))


def _classify_status(row: pd.Series) -> str:
    if row["risk_score"] >= 0.62:
        return "Risco"
    if row["delta_pct"] < -0.05:
        return "Atencao"
    if row["delta_pct"] > 0.10 and row["risk_score"] < 0.50:
        return "Oportunidade"
    return "No plano"


def _recommend_action(row: pd.Series) -> str:
    if row["status"] == "Risco":
        return "Revisar abastecimento e cobertura de estoque"
    if row["status"] == "Atencao":
        return "Revisar meta local e acao comercial"
    if row["status"] == "Oportunidade":
        return "Aumentar exposicao e proteger disponibilidade"
    if row["promo_share"] >= 0.25:
        return "Monitorar dependencia de promocao"
    return "Manter plano e acompanhar execucao semanal"
