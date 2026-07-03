from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, State, dcc, html
from dash_iconify import DashIconify

from revenue_forecast_dashboard.data import (
    COMPETITION_SLUG,
    SCENARIOS,
    DataNotAvailableError,
    build_recommendations_table,
    build_summary,
    get_dashboard_slice,
    get_data_dir,
    get_family_names,
    get_store_names,
    missing_required_files,
)
from revenue_forecast_dashboard.figures import (
    make_empty_figure,
    make_forecast_figure,
    make_gap_figure,
    make_mix_figure,
)

HORIZON_OPTIONS = [
    {"label": "30 dias", "value": 30},
    {"label": "60 dias", "value": 60},
    {"label": "90 dias", "value": 90},
]
HISTORY_OPTIONS = [
    {"label": "Ultimos 90 dias", "value": 90},
    {"label": "Ultimos 120 dias", "value": 120},
    {"label": "Ano atual", "value": 182},
]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_FOLDER = Path(os.getenv("DASH_ASSETS_FOLDER", Path.cwd() / "assets")).resolve()
if not ASSETS_FOLDER.exists():
    ASSETS_FOLDER = PROJECT_ROOT / "assets"

app = Dash(
    __name__,
    title="Planejamento de Receita",
    update_title=None,
    assets_folder=str(ASSETS_FOLDER),
    assets_url_path="/assets",
)
server = app.server


def create_layout() -> html.Div:
    return html.Div(
        className="app-shell",
        children=[
            html.Main(
                className="main-view",
                children=[
                    dcc.Download(id="download-plan"),
                    _header(),
                    html.Section(id="kpi-grid", className="kpi-grid"),
                    html.Section(
                        className="dashboard-grid",
                        children=[
                            html.Div(
                                className="primary-column",
                                children=[
                                    html.Article(
                                        className="panel chart-panel",
                                        children=[
                                            _panel_title(
                                                "Evolucao e forecast",
                                                "Historico real e cenarios projetados",
                                            ),
                                            dcc.Graph(
                                                id="forecast-chart",
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                className="chart chart-large",
                                                style={"height": "360px"},
                                            ),
                                        ],
                                    ),
                                    html.Article(
                                        className="panel chart-panel",
                                        children=[
                                            _panel_title(
                                                "Gap vs. plano",
                                                "Prioridade comercial por frente",
                                            ),
                                            dcc.Graph(
                                                id="gap-chart",
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                className="chart chart-medium",
                                                style={"height": "330px"},
                                            ),
                                        ],
                                    ),
                                    html.Article(
                                        className="panel panel-table",
                                        children=[
                                            _panel_title(
                                                "Plano por loja e familia",
                                                "Registros com maior prioridade",
                                            ),
                                            html.Div(id="records-table", className="table-wrap"),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="secondary-column",
                                children=[
                                    _model_quality_panel(),
                                    html.Article(
                                        className="panel chart-panel",
                                        children=[
                                            _panel_title(
                                                "Mix de vendas",
                                                "Top familias ou lojas no cenario",
                                            ),
                                            dcc.Graph(
                                                id="mix-chart",
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                className="chart chart-small",
                                                style={"height": "280px"},
                                            ),
                                        ],
                                    ),
                                    html.Article(
                                        className="panel",
                                        children=[
                                            _panel_title(
                                                "Sinais de decisao",
                                                "Alertas de vendas e operacao",
                                            ),
                                            html.Div(id="insight-list", className="insight-list"),
                                        ],
                                    ),
                                    html.Article(
                                        className="panel",
                                        children=[
                                            _panel_title(
                                                "Acoes rapidas",
                                                "Recomendacoes para execucao semanal",
                                            ),
                                            html.Div(id="action-list", className="action-list"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def _header() -> html.Header:
    return html.Header(
        className="topbar",
        children=[
            html.Div(
                className="title-block",
                children=[
                    html.H1("Planejamento de Receita"),
                    html.P(
                        "Forecast executivo com dados reais da Store Sales Favorita.",
                        className="subtitle",
                    ),
                ],
            ),
            html.Div(
                className="filters",
                children=[
                    _filter_control(
                        "Periodo",
                        "history-filter",
                        HISTORY_OPTIONS,
                        120,
                        "lucide:calendar-range",
                    ),
                    _filter_control(
                        "Loja",
                        "store-filter",
                        [{"label": "Todas as lojas", "value": "all"}]
                        + [{"label": name, "value": name} for name in get_store_names()],
                        "all",
                        "lucide:store",
                    ),
                    _filter_control(
                        "Familia",
                        "family-filter",
                        [{"label": "Todas as familias", "value": "all"}]
                        + [{"label": name, "value": name} for name in get_family_names()],
                        "all",
                        "lucide:boxes",
                    ),
                    _filter_control(
                        "Horizonte", "horizon-filter", HORIZON_OPTIONS, 60, "lucide:timer"
                    ),
                    _filter_control(
                        "Cenario",
                        "scenario-filter",
                        [
                            {"label": scenario["label"], "value": scenario_key}
                            for scenario_key, scenario in SCENARIOS.items()
                        ],
                        "esperado",
                        "lucide:target",
                    ),
                    html.Button(
                        id="export-button",
                        className="export-button",
                        children=[
                            DashIconify(icon="lucide:download", width=17),
                            html.Span("Exportar"),
                        ],
                    ),
                ],
            ),
        ],
    )


def _filter_control(
    label: str,
    component_id: str,
    options: list[dict[str, object]],
    value: object,
    icon: str,
) -> html.Div:
    return html.Div(
        className="filter-control",
        children=[
            html.Label(
                children=[
                    DashIconify(icon=icon, width=15),
                    html.Span(label),
                ]
            ),
            dcc.Dropdown(
                id=component_id,
                options=options,
                value=value,
                clearable=False,
                searchable=False,
                className="dropdown",
            ),
        ],
    )


def _panel_title(title: str, subtitle: str) -> html.Div:
    return html.Div(
        className="panel-title",
        children=[
            html.Div(
                children=[
                    html.H2(title),
                    html.P(subtitle),
                ]
            ),
        ],
    )


def _model_quality_panel() -> html.Article:
    metrics = _load_model_metrics()
    if not metrics:
        return html.Article(
            className="panel model-panel",
            children=[
                _panel_title("Qualidade do modelo", "Backtest ainda nao gerado"),
                html.Div(
                    className="metric-empty",
                    children="Execute: poetry run python scripts/evaluate_model.py",
                ),
            ],
        )

    metric_items = [
        ("Modelo", str(metrics.get("model", "Nao definido"))),
        ("Baseline", str(metrics.get("baseline_model", "Nao definido"))),
        ("Testados", str(metrics.get("models_tested", 1))),
        ("WAPE", _format_percent(float(metrics.get("wape", 0.0)))),
        ("SMAPE", _format_percent(float(metrics.get("smape", 0.0)))),
        ("Bias", _format_percent(float(metrics.get("bias", 0.0)))),
    ]
    return html.Article(
        className="panel model-panel",
        children=[
            _panel_title(
                "Qualidade do modelo",
                (
                    "Backtest "
                    f"{metrics.get('validation_start', 'n/a')} a "
                    f"{metrics.get('validation_end', 'n/a')}"
                ),
            ),
            html.Div(
                className="metric-grid",
                children=[
                    html.Div(
                        className="metric-item",
                        children=[
                            html.Span(label),
                            html.Strong(value),
                        ],
                    )
                    for label, value in metric_items
                ],
            ),
        ],
    )


def _load_model_metrics() -> dict[str, object]:
    metrics_path = PROJECT_ROOT / "reports" / "model_metrics.json"
    if not metrics_path.exists():
        return {}
    return json.loads(metrics_path.read_text(encoding="utf-8"))


@app.callback(
    Output("kpi-grid", "children"),
    Output("forecast-chart", "figure"),
    Output("mix-chart", "figure"),
    Output("gap-chart", "figure"),
    Output("insight-list", "children"),
    Output("records-table", "children"),
    Output("action-list", "children"),
    Input("store-filter", "value"),
    Input("family-filter", "value"),
    Input("horizon-filter", "value"),
    Input("history-filter", "value"),
    Input("scenario-filter", "value"),
)
def update_dashboard(
    store: str,
    family: str,
    horizon_days: int,
    history_window_days: int,
    scenario: str,
) -> tuple[
    list[html.Article], object, object, object, list[html.Div], html.Table, list[html.Button]
]:
    try:
        display_history, comparison_history, forecast = get_dashboard_slice(
            store,
            family,
            int(horizon_days),
            int(history_window_days),
        )
    except DataNotAvailableError:
        return _missing_data_dashboard()

    summary = build_summary(comparison_history, forecast, scenario)
    table = build_recommendations_table(comparison_history, forecast, scenario)

    return (
        _kpi_cards(summary),
        make_forecast_figure(display_history, forecast, scenario),
        make_mix_figure(forecast, scenario, family),
        make_gap_figure(comparison_history, forecast, scenario, store),
        _insights(summary, table),
        _records_table(table),
        _actions(table),
    )


@app.callback(
    Output("download-plan", "data"),
    Input("export-button", "n_clicks"),
    State("store-filter", "value"),
    State("family-filter", "value"),
    State("horizon-filter", "value"),
    State("history-filter", "value"),
    State("scenario-filter", "value"),
    prevent_initial_call=True,
)
def export_plan(
    _: int,
    store: str,
    family: str,
    horizon_days: int,
    history_window_days: int,
    scenario: str,
) -> dict[str, object]:
    try:
        _, comparison_history, forecast = get_dashboard_slice(
            store,
            family,
            int(horizon_days),
            int(history_window_days),
        )
    except DataNotAvailableError:
        return dcc.send_string(_missing_data_text(), "dados_reais_ausentes.txt")

    table = build_recommendations_table(comparison_history, forecast, scenario, limit=100)
    export = table.rename(
        columns={
            "store": "loja",
            "family": "familia",
            "revenue": "vendas_previstas",
            "delta_pct": "variacao_vs_base",
            "promo_share": "participacao_promocional",
            "risk_score": "risco",
            "confidence": "confianca",
            "status": "status",
            "recommended_action": "acao_recomendada",
        }
    )
    return dcc.send_data_frame(
        export[
            [
                "loja",
                "familia",
                "vendas_previstas",
                "variacao_vs_base",
                "participacao_promocional",
                "risco",
                "confianca",
                "status",
                "acao_recomendada",
            ]
        ].to_csv,
        "planejamento_vendas.csv",
        index=False,
        sep=";",
    )


def _kpi_cards(summary: dict[str, float]) -> list[html.Article]:
    return [
        _kpi_card(
            "Vendas previstas",
            _format_volume(summary["revenue"]),
            _format_delta(summary["delta_pct"], "vs. periodo anterior"),
            "lucide:badge-dollar-sign",
            "positive" if summary["delta_pct"] >= 0 else "negative",
        ),
        _kpi_card(
            "Crescimento previsto",
            _format_percent(summary["delta_pct"]),
            "Baseado no historico real",
            "lucide:trending-up",
            "positive" if summary["delta_pct"] >= 0 else "negative",
        ),
        _kpi_card(
            "Confianca do forecast",
            _format_percent(summary["confidence"]),
            "Consistencia do plano",
            "lucide:shield-check",
            "positive" if summary["confidence"] >= 0.80 else "warning",
        ),
        _kpi_card(
            "Risco operacional",
            _format_percent(summary["risk_rate"]),
            f"{summary['critical_count']} frentes em atencao",
            "lucide:triangle-alert",
            "warning" if summary["risk_rate"] < 0.62 else "negative",
        ),
        _kpi_card(
            "Vendas em promocao",
            _format_percent(summary["promo_share"]),
            f"{_format_volume(summary['promo_revenue'])} do plano",
            "lucide:megaphone",
            "neutral",
        ),
    ]


def _kpi_card(title: str, value: str, detail: str, icon: str, state: str) -> html.Article:
    return html.Article(
        className=f"kpi-card {state}",
        children=[
            html.Div(
                className="kpi-icon",
                children=DashIconify(icon=icon, width=22),
            ),
            html.Div(
                className="kpi-copy",
                children=[
                    html.Span(title),
                    html.Strong(value),
                    html.Small(detail),
                ],
            ),
        ],
    )


def _insights(summary: dict[str, float], table: pd.DataFrame) -> list[html.Div]:
    top_sales = table.sort_values("revenue", ascending=False).iloc[0]
    top_risk = table.sort_values("risk_score", ascending=False).iloc[0]
    attention_count = int((table["status"].isin(["Risco", "Atencao"])).sum())

    items = [
        (
            "Controle",
            "Vendas projetadas",
            (
                "O cenario selecionado soma "
                f"{_format_volume(summary['revenue'])} no horizonte filtrado."
            ),
        ),
        (
            "Oportunidade",
            "Maior contribuicao",
            (
                f"{top_sales['family']} em {top_sales['store']} concentra "
                f"{_format_volume(top_sales['revenue'])}."
            ),
        ),
        (
            "Atencao",
            "Risco operacional",
            f"{top_risk['family']} em {top_risk['store']} exige revisao de abastecimento.",
        ),
        (
            "Prioridade",
            "Execucao semanal",
            f"{attention_count} frentes aparecem com status de atencao ou risco.",
        ),
    ]

    return [
        html.Div(
            className="insight-row",
            children=[
                html.Span(label, className=f"status-badge {_slug(label)}"),
                html.Div(
                    children=[
                        html.Strong(title),
                        html.P(description),
                    ]
                ),
            ],
        )
        for label, title, description in items
    ]


def _records_table(table: pd.DataFrame) -> html.Table:
    return html.Table(
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Loja"),
                        html.Th("Familia"),
                        html.Th("Vendas"),
                        html.Th("Variacao"),
                        html.Th("Promocao"),
                        html.Th("Status"),
                        html.Th("Acao recomendada"),
                    ]
                )
            ),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(row["store"]),
                            html.Td(row["family"]),
                            html.Td(_format_volume(row["revenue"])),
                            html.Td(
                                _format_delta(row["delta_pct"]),
                                className="positive-text"
                                if row["delta_pct"] >= 0
                                else "negative-text",
                            ),
                            html.Td(_format_percent(row["promo_share"])),
                            html.Td(
                                html.Span(
                                    row["status"], className=f"status-badge {_slug(row['status'])}"
                                )
                            ),
                            html.Td(row["recommended_action"], className="action-cell"),
                        ]
                    )
                    for _, row in table.iterrows()
                ]
            ),
        ]
    )


def _actions(table: pd.DataFrame) -> list[html.Button]:
    risk_rows = table[table["status"] == "Risco"]
    opportunity_rows = table[table["status"] == "Oportunidade"]
    first_risk = risk_rows.iloc[0] if not risk_rows.empty else table.iloc[0]
    first_opportunity = (
        opportunity_rows.iloc[0]
        if not opportunity_rows.empty
        else table.sort_values("delta_pct").iloc[-1]
    )

    actions = [
        (
            "lucide:package-check",
            "Revisar abastecimento",
            f"{first_risk['family']} em {first_risk['store']}",
        ),
        (
            "lucide:trending-up",
            "Proteger crescimento",
            f"{first_opportunity['family']} em {first_opportunity['store']}",
        ),
        (
            "lucide:badge-percent",
            "Revisar promocoes",
            "Priorizar campanhas com disponibilidade preservada",
        ),
    ]
    return [
        html.Button(
            className="action-row",
            children=[
                DashIconify(icon=icon, width=19),
                html.Span(
                    children=[
                        html.Strong(title),
                        html.Small(detail),
                    ]
                ),
                DashIconify(icon="lucide:chevron-right", width=17),
            ],
        )
        for icon, title, detail in actions
    ]


def _missing_data_dashboard() -> tuple[
    list[html.Article], object, object, object, list[html.Div], html.Table, list[html.Button]
]:
    message = _missing_data_text()
    return (
        _missing_kpis(),
        make_empty_figure("Dados reais da Kaggle ainda nao encontrados em data/raw."),
        make_empty_figure("Baixe e extraia os CSVs da competicao Store Sales."),
        make_empty_figure("O painel nao usa dados demonstrativos."),
        [
            html.Div(
                className="insight-row",
                children=[
                    html.Span("Atencao", className="status-badge atencao"),
                    html.Div(
                        children=[
                            html.Strong("Fonte de dados pendente"),
                            html.P(message),
                        ]
                    ),
                ],
            )
        ],
        _missing_table(),
        _missing_actions(),
    )


def _missing_kpis() -> list[html.Article]:
    return [
        _kpi_card(
            "Vendas previstas", "Sem dados", "CSV real ausente", "lucide:database", "warning"
        ),
        _kpi_card(
            "Crescimento previsto", "Sem dados", "CSV real ausente", "lucide:trending-up", "warning"
        ),
        _kpi_card(
            "Confianca do forecast",
            "Sem dados",
            "CSV real ausente",
            "lucide:shield-check",
            "warning",
        ),
        _kpi_card(
            "Risco operacional", "Sem dados", "CSV real ausente", "lucide:triangle-alert", "warning"
        ),
        _kpi_card(
            "Vendas em promocao", "Sem dados", "CSV real ausente", "lucide:megaphone", "warning"
        ),
    ]


def _missing_table() -> html.Table:
    return html.Table(
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Arquivo"),
                        html.Th("Status"),
                        html.Th("Pasta esperada"),
                    ]
                )
            ),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(filename),
                            html.Td(html.Span("Ausente", className="status-badge risco")),
                            html.Td(str(get_data_dir())),
                        ]
                    )
                    for filename in missing_required_files()
                ]
            ),
        ]
    )


def _missing_actions() -> list[html.Button]:
    return [
        html.Button(
            className="action-row",
            children=[
                DashIconify(icon="lucide:download-cloud", width=19),
                html.Span(
                    children=[
                        html.Strong("Baixar dados reais"),
                        html.Small("poetry run python scripts/download_store_sales.py"),
                    ]
                ),
                DashIconify(icon="lucide:chevron-right", width=17),
            ],
        )
    ]


def _missing_data_text() -> str:
    missing = ", ".join(missing_required_files()) or "nenhum"
    return (
        f"Arquivos ausentes: {missing}. Pasta esperada: {get_data_dir()}. "
        f"Fonte: Kaggle competition {COMPETITION_SLUG}."
    )


def _format_volume(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{_format_number(value / 1_000_000, 1)} mi"
    if abs_value >= 1_000:
        return f"{_format_number(value / 1_000, 1)} mil"
    return _format_number(value, 0)


def _format_percent(value: float) -> str:
    return f"{_format_number(value * 100, 1)}%"


def _format_delta(value: float, suffix: str = "") -> str:
    sign = "+" if value >= 0 else ""
    text = f"{sign}{_format_percent(value)}"
    return f"{text} {suffix}".strip()


def _format_number(value: float, decimals: int) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


app.layout = create_layout


def main() -> None:
    host = os.getenv("DASH_HOST", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
