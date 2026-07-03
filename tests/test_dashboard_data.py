from pathlib import Path

import pandas as pd

from revenue_forecast_dashboard.data import (
    build_recommendations_table,
    build_summary,
    get_dashboard_slice,
    load_real_data,
)


def test_real_store_sales_shape_loads_history_and_scenarios(tmp_path: Path) -> None:
    _write_store_sales_fixture(tmp_path)

    history, forecast = load_real_data(tmp_path)

    assert not history.empty
    assert not forecast.empty
    assert set(forecast["scenario"].unique()) == {"conservador", "esperado", "otimista"}
    assert {"date", "store", "family", "revenue", "promo"}.issubset(history.columns)


def test_dashboard_summary_is_business_ready_with_real_shape(tmp_path: Path) -> None:
    _write_store_sales_fixture(tmp_path)
    _, comparison_history, forecast = get_dashboard_slice("all", "all", 30, 60, tmp_path)

    summary = build_summary(comparison_history, forecast, "esperado")

    assert summary["revenue"] > 0
    assert 0 < summary["confidence"] <= 1
    assert 0 <= summary["risk_rate"] <= 1
    assert 0 <= summary["promo_share"] <= 1


def test_recommendations_table_returns_executive_actions(tmp_path: Path) -> None:
    _write_store_sales_fixture(tmp_path)
    _, comparison_history, forecast = get_dashboard_slice("all", "all", 30, 60, tmp_path)

    table = build_recommendations_table(comparison_history, forecast, "esperado")

    assert not table.empty
    assert {"store", "family", "status", "recommended_action"}.issubset(table.columns)
    assert table["recommended_action"].str.len().min() > 10


def _write_store_sales_fixture(path: Path) -> None:
    dates = pd.date_range("2017-06-01", periods=90)
    rows = []
    families = ["GROCERY I", "BEVERAGES"]
    for store_nbr in [1, 2]:
        for family_idx, family in enumerate(families):
            for day_idx, date in enumerate(dates):
                rows.append(
                    {
                        "id": len(rows),
                        "date": date.strftime("%Y-%m-%d"),
                        "store_nbr": store_nbr,
                        "family": family,
                        "sales": 120 + store_nbr * 14 + family_idx * 9 + day_idx * 0.8,
                        "onpromotion": 4 if day_idx % 11 == 0 else 0,
                    }
                )
    pd.DataFrame(rows).to_csv(path / "train.csv", index=False)

    stores = pd.DataFrame(
        [
            {"store_nbr": 1, "city": "Quito", "state": "Pichincha", "type": "D", "cluster": 13},
            {"store_nbr": 2, "city": "Guayaquil", "state": "Guayas", "type": "C", "cluster": 8},
        ]
    )
    stores.to_csv(path / "stores.csv", index=False)

    future_dates = pd.date_range("2017-08-30", periods=16)
    test_rows = []
    for store_nbr in [1, 2]:
        for family in families:
            for date in future_dates:
                test_rows.append(
                    {
                        "id": len(test_rows),
                        "date": date.strftime("%Y-%m-%d"),
                        "store_nbr": store_nbr,
                        "family": family,
                        "onpromotion": 3 if date.day % 5 == 0 else 0,
                    }
                )
    pd.DataFrame(test_rows).to_csv(path / "test.csv", index=False)
