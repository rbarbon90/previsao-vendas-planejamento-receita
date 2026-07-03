# Previsão de Vendas e Planejamento de Receita

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Dash](https://img.shields.io/badge/Dash-2.18%2B-008DE4?style=flat-square&logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.2%2B-150458?style=flat-square&logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Poetry](https://img.shields.io/badge/Poetry-managed-60A5FA?style=flat-square&logo=poetry&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Dashboard executivo em Dash para apoiar decisões de vendas, compras, estoque e metas comerciais com base em histórico real, forecast, cenários de planejamento e recomendações por loja e família de produto.

O projeto foi desenvolvido como um case end-to-end de dados: ingestão via Kaggle, análise exploratória, modelagem de séries temporais, backtest, avaliação de métricas, dashboard executivo, Docker, testes automatizados e documentação técnica.

## Demonstração

A demonstração da interface será apresentada em vídeo no portfólio, cobrindo:

- navegação pelo dashboard executivo;
- filtros por loja, família, horizonte e cenário;
- leitura de KPIs e gráficos;
- interpretação da tabela de recomendações;
- explicação do modelo vencedor e das métricas de backtest.

## Destaques do projeto

- Usa dados reais da competição Kaggle Store Sales - Time Series Forecasting.
- Compara cinco modelos de previsão e seleciona automaticamente o menor WAPE.
- Entrega visão executiva com KPIs, cenários, mix de vendas, gap vs. plano e plano de ação.
- Inclui notebooks de EDA, modelagem e avaliação de métricas.
- Possui execução local com Poetry e execução containerizada com Docker.
- Mantém documentação técnica e leitura de negócio separadas.
- Protege dados brutos e credenciais para publicação pública do repositório.

## Principais resultados

Último backtest registrado:

| Indicador | Resultado |
| --- | ---: |
| Modelo vencedor | `WeekdayAverageBaseline` |
| Baseline principal | `SeasonalNaiveBaseline` |
| Janela de validação | 2017-07-31 a 2017-08-15 |
| Séries avaliadas | 1.782 |
| Linhas avaliadas | 28.512 |
| Modelos testados | 5 |
| WAPE | 18,01% |
| SMAPE | 47,07% |
| Bias | +1,97% |
| Ganho de WAPE vs. baseline principal | 12,86% |

A principal conclusão do benchmark é que a sazonalidade por dia da semana é um sinal forte para o varejo analisado. O modelo vencedor usa a média recente por dia da semana e superou alternativas baseadas em último valor, média móvel, sazonal naive e uma abordagem interpretável com promoção e tendência.

## Stack

| Camada | Tecnologias |
| --- | --- |
| Aplicação | Python, Dash, Plotly, Dash Iconify |
| Dados | Pandas, NumPy, Kaggle API |
| Modelagem | Baselines estatísticos, backtest temporal, métricas de forecast |
| Qualidade | Pytest, Ruff |
| Ambiente | Poetry, Docker, Docker Compose, Gunicorn |
| Documentação | Markdown, notebooks Jupyter |

## Visão do produto

O painel foi desenhado para gestores de negócio. Ele mostra vendas previstas, crescimento esperado, confiança do forecast, risco operacional, participação promocional, evolução temporal, mix de vendas, gap vs. plano e uma tabela de ações recomendadas por loja e família de produto.

Os notebooks ficam reservados para EDA, modelagem, métricas e experimentos. O dashboard entrega a camada executiva de decisão.

## Documentação

Documentos complementares:

- [Documentação técnica](docs/documentacao_tecnica.md): arquitetura, fluxo de dados, modelagem, métricas, execução, testes e limitações técnicas.
- [Insights de negócio](docs/insights_negocio.md): leitura executiva dos resultados, insights, playbook de decisão e recomendações de evolução.

## Dashboard

O painel é construído em Dash.

| Área | Arquivo |
| --- | --- |
| Layout e callbacks | `src/revenue_forecast_dashboard/app.py` |
| Loader e agregações | `src/revenue_forecast_dashboard/data.py` |
| Modelos e métricas | `src/revenue_forecast_dashboard/model.py` |
| Gráficos Plotly | `src/revenue_forecast_dashboard/figures.py` |
| Identidade visual | `assets/styles.css` |

### Funcionalidades

- Filtros por período histórico, loja, família, horizonte e cenário.
- Cenários conservador, esperado e otimista.
- KPIs de vendas previstas, crescimento, confiança, risco e participação promocional.
- Gráfico de evolução histórica e forecast.
- Gráfico de mix por família ou loja.
- Gráfico de gap vs. plano.
- Tabela priorizada com status e ação recomendada.
- Exportação do plano em CSV.

## Modelo e métricas

O painel lê `reports/model_metrics.json` e usa automaticamente o modelo com menor WAPE. Também é possível forçar um modelo via variável de ambiente `FORECAST_MODEL_NAME`.

Modelos avaliados:

- `LastValueBaseline`;
- `MovingAverageBaseline`;
- `SeasonalNaiveBaseline`;
- `WeekdayAverageBaseline`;
- `SeasonalPromotionTrendForecaster`.

O candidato estatístico interpretável para varejo usa:

- sazonalidade por dia da semana;
- médias móveis recentes por loja e família;
- tendência recente;
- quantidade de itens em promoção;
- cenários conservador, esperado e otimista.

Para reexecutar a avaliação:

```bash
poetry run python scripts/evaluate_model.py
```

Relatórios gerados:

- `reports/model_metrics.json`;
- `reports/model_comparison.csv`;
- `reports/model_comparison.json`;
- `reports/model_metrics_by_family.csv`.

## Dados

A fonte de dados é a competição Kaggle Store Sales - Time Series Forecasting, com dados da Corporación Favorita.

O painel usa arquivos reais em `data/raw/`:

- `train.csv`: histórico diário por loja, família de produto, vendas (`sales`) e promoções;
- `stores.csv`: metadados das lojas;
- `test.csv`: promoções futuras quando disponível;
- `transactions.csv`, `oil.csv` e `holidays_events.csv`: reservados para notebooks e futuras melhorias.

Importante: a base não traz preço unitário, receita financeira nem margem. Por isso, o dashboard usa `sales` como métrica operacional de vendas planejadas. Qualquer conversão para receita em moeda precisa de uma tabela real de preços, ticket médio ou margem.

Os CSVs reais são ignorados pelo Git e não devem ser publicados no repositório. A pasta `data/raw/` mantém apenas `.gitkeep`.

## Como rodar

### Poetry

```bash
poetry install
poetry run dashboard-receita
```

Abra:

```text
http://localhost:8050
```

### Docker

```bash
docker compose up --build dashboard
```

Abra:

```text
http://localhost:8050
```

## Como baixar os dados

Configure suas credenciais Kaggle e execute:

```bash
poetry run python scripts/download_store_sales.py
```

O projeto suporta:

- `KAGGLE_API_TOKEN`;
- `KAGGLE_USERNAME` e `KAGGLE_KEY`;
- `~/.kaggle/access_token`;
- `~/.kaggle/kaggle.json`.

Também é possível usar o arquivo `.env` local:

```powershell
.\scripts\setup_kaggle_token.ps1
poetry run python scripts/download_store_sales.py
```

No Docker, baixe os CSVs localmente primeiro. O `docker-compose.yml` monta `./data/raw` em `/app/data/raw`.

## Notebooks

Os notebooks documentam a etapa analítica em português:

1. `notebooks/01_eda_dados_reais.ipynb`: leitura da base real, granularidade, período histórico, mix de vendas, promoções e principais conclusões para modelagem.
2. `notebooks/02_modelagem_baselines.ipynb`: construção do backtest, separação treino/validação, baselines, modelo candidato e comparação por WAPE.
3. `notebooks/03_avaliacao_metricas.ipynb`: interpretação das métricas, leitura dos relatórios, modelo vencedor, bias, erro por família e próximos passos.

Para rodar Jupyter Lab com Docker:

```bash
docker compose up --build notebooks
```

Abra:

```text
http://localhost:8888/lab?token=receita
```

## Qualidade

Execute os testes e o lint:

```bash
poetry run pytest
poetry run ruff check .
```

Os testes cobrem:

- carregamento de dados no formato real esperado;
- geração dos três cenários;
- cálculo de sumário executivo;
- tabela de recomendações;
- registro e fallback de modelos;
- métricas de avaliação.

## Estrutura

```text
src/revenue_forecast_dashboard/
  app.py       # Layout Dash e callbacks
  data.py      # Loader dos CSVs reais e agregações de negócio
  figures.py   # Gráficos Plotly
  model.py     # Modelos, baselines e métricas
assets/
  styles.css
data/raw/
  .gitkeep     # CSVs reais ficam apenas localmente
docs/
  documentacao_tecnica.md
  insights_negocio.md
notebooks/
  01_eda_dados_reais.ipynb
  02_modelagem_baselines.ipynb
  03_avaliacao_metricas.ipynb
reports/
  model_metrics.json
  model_comparison.csv
scripts/
  download_store_sales.py
  evaluate_model.py
tests/
  test_dashboard_data.py
  test_forecast_models.py
```

## Limitações

- `sales` é usado como proxy de volume planejado, não como receita monetária.
- Os cenários são multiplicadores de planejamento, não probabilidades calibradas.
- O backtest atual usa janela de validação de 16 dias.
- Variáveis como feriados, petróleo, transações, preço e margem ainda não entram no modelo ativo.
- Famílias de baixo volume podem apresentar WAPE instável e devem ser avaliadas com métricas complementares.

## Próximas evoluções

- Integrar preço, ticket médio ou margem para estimar receita financeira.
- Adicionar variáveis de feriados, eventos e transações no modelo.
- Criar backtests com múltiplas janelas temporais.
- Tratar famílias de demanda intermitente com estratégia específica.
- Persistir previsões para auditoria e comparação com realizado.
- Publicar uma demo hospedada do dashboard.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte [LICENSE](LICENSE).
