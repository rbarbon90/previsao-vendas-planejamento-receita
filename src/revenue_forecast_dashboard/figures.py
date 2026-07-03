from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from revenue_forecast_dashboard.data import SCENARIOS

COLORS = {
    "cobalt": "#2563EB",
    "navy": "#14213D",
    "cool_gray": "#94A3B8",
    "graphite": "#1F2937",
    "amber": "#D89B2B",
    "ice": "#F5F7FB",
    "green": "#059669",
    "red": "#DC2626",
    "border": "#E2E8F0",
    "muted": "#64748B",
}

SEGMENT_COLORS = ["#2563EB", "#14213D", "#D89B2B", "#64748B", "#0F766E", "#7C3AED"]


def make_forecast_figure(
    history: pd.DataFrame, forecast: pd.DataFrame, selected_scenario: str
) -> go.Figure:
    fig = go.Figure()
    history_line = history.groupby("date", as_index=False).agg(revenue=("revenue", "sum"))

    fig.add_trace(
        go.Scatter(
            x=history_line["date"],
            y=history_line["revenue"] / 1_000_000,
            mode="lines",
            name="Histórico real",
            line={"color": COLORS["navy"], "width": 2.6},
            hovertemplate="Vendas: %{y:.2f} mi<extra></extra>",
        )
    )

    for scenario_key, scenario in SCENARIOS.items():
        scenario_line = (
            forecast[forecast["scenario"] == scenario_key]
            .groupby("date", as_index=False)
            .agg(revenue=("revenue", "sum"))
        )
        selected = scenario_key == selected_scenario
        fig.add_trace(
            go.Scatter(
                x=scenario_line["date"],
                y=scenario_line["revenue"] / 1_000_000,
                mode="lines",
                name=scenario["label"],
                line={
                    "color": scenario["color"],
                    "width": 3.2 if selected else 1.9,
                    "dash": "solid" if selected else "dot",
                },
                opacity=1.0 if selected else 0.58,
                hovertemplate="Vendas: %{y:.2f} mi<extra></extra>",
            )
        )

    if not forecast.empty:
        fig.add_vline(
            x=forecast["date"].min(),
            line_dash="dot",
            line_width=1,
            line_color=COLORS["cool_gray"],
        )
    _apply_layout(fig, yaxis_title="Vendas (mi)", legend_orientation="h")
    fig.update_layout(legend={"x": 0, "y": 1.16, "xanchor": "left", "yanchor": "top"})
    return fig


def make_mix_figure(
    forecast: pd.DataFrame, selected_scenario: str, family_filter: str
) -> go.Figure:
    scenario_forecast = forecast[forecast["scenario"] == selected_scenario]
    dimension = "store" if family_filter != "all" else "family"
    segment = (
        scenario_forecast.groupby(dimension, as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
        .head(8)
        .sort_values("revenue", ascending=True)
    )

    fig = go.Figure(
        go.Bar(
            x=segment["revenue"] / 1_000_000,
            y=segment[dimension],
            orientation="h",
            marker={"color": SEGMENT_COLORS[: len(segment)], "line": {"width": 0}},
            text=(segment["revenue"] / scenario_forecast["revenue"].sum()).map(
                lambda value: f"{value:.1%}"
            ),
            textposition="auto",
            hovertemplate="%{y}<br>Vendas: %{x:.2f} mi<extra></extra>",
        )
    )
    fig.update_layout(
        margin={"l": 110, "r": 12, "t": 12, "b": 30},
        xaxis_title="Vendas (mi)",
        yaxis_title="",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter", "color": COLORS["graphite"], "size": 11},
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=COLORS["border"], zeroline=False)
    fig.update_yaxes(showgrid=False, automargin=True)
    return fig


def make_gap_figure(
    comparison_history: pd.DataFrame,
    forecast: pd.DataFrame,
    selected_scenario: str,
    store_filter: str,
) -> go.Figure:
    scenario_forecast = forecast[forecast["scenario"] == selected_scenario]
    dimension = "family" if store_filter != "all" else "store"

    planned = (
        scenario_forecast.groupby(dimension, as_index=False)
        .agg(revenue=("revenue", "sum"), risk_score=("risk_score", "mean"))
        .reset_index(drop=True)
    )
    baseline = (
        comparison_history.groupby(dimension, as_index=False)
        .agg(previous_revenue=("revenue", "sum"))
        .reset_index(drop=True)
    )
    gap = planned.merge(baseline, on=dimension, how="left").fillna({"previous_revenue": 0})
    gap["target"] = gap["previous_revenue"] * 1.06
    gap.loc[gap["target"] == 0, "target"] = gap.loc[gap["target"] == 0, "revenue"]
    gap["gap_pct"] = (gap["revenue"] - gap["target"]) / gap["target"]
    gap = gap.sort_values("gap_pct", ascending=True).tail(8)

    bar_colors = [
        COLORS["red"] if value < -0.08 else COLORS["amber"] if value < 0 else COLORS["cobalt"]
        for value in gap["gap_pct"]
    ]

    fig = go.Figure(
        go.Bar(
            x=gap["gap_pct"],
            y=gap[dimension],
            orientation="h",
            marker={"color": bar_colors, "line": {"width": 0}},
            customdata=gap[["revenue", "target"]],
            hovertemplate=(
                "Gap: %{x:.1%}<br>Vendas: %{customdata[0]:,.0f}"
                "<br>Plano: %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=0, line_color=COLORS["cool_gray"], line_width=1)
    _apply_layout(fig, xaxis_title="Gap vs. plano", yaxis_title="")
    fig.update_xaxes(tickformat=".0%")
    return fig


def _apply_layout(
    fig: go.Figure,
    yaxis_title: str = "",
    xaxis_title: str = "",
    legend_orientation: str = "v",
) -> None:
    fig.update_layout(
        margin={"l": 28, "r": 18, "t": 24, "b": 34},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter", "color": COLORS["graphite"], "size": 12},
        hovermode="x unified",
        legend={"orientation": legend_orientation, "font": {"size": 11}},
        xaxis={"title": xaxis_title, "showgrid": False, "zeroline": False},
        yaxis={
            "title": yaxis_title,
            "gridcolor": COLORS["border"],
            "zeroline": False,
            "showline": False,
        },
    )
    fig.update_xaxes(showline=False, tickfont={"color": "#475569"})
    fig.update_yaxes(showline=False, tickfont={"color": "#475569"})


def make_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        margin={"l": 24, "r": 24, "t": 24, "b": 24},
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "x": 0.5,
                "y": 0.5,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"family": "Inter", "size": 14, "color": COLORS["muted"]},
            }
        ],
    )
    return fig
