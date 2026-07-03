# Documentação Técnica

Projeto: Previsão de Vendas e Planejamento de Receita  
Versão documentada: 0.1.0  
Última atualização: 2026-07-03

## 1. Visão geral

Este projeto entrega um dashboard executivo em Dash para planejamento comercial com base em histórico real de vendas, previsão por loja e família de produto, cenários de planejamento e recomendações operacionais. A aplicação foi construída para transformar a base pública da competição Kaggle Store Sales - Time Series Forecasting em uma experiência de decisão voltada a receita, estoque, metas e ações comerciais.

Embora a interface use o termo receita para facilitar a leitura executiva, a base original não possui preço unitário, margem ou faturamento financeiro. Portanto, a métrica operacional usada pelo projeto é `sales`, tratada internamente como `revenue` para padronizar os cálculos do painel. Para transformar o projeto em planejamento financeiro de receita, é necessário integrar uma tabela confiável de preço, ticket médio ou margem por loja, família e período.

## 2. Escopo técnico

O sistema cobre:

- ingestão dos arquivos reais da competição Store Sales;
- preparação do histórico diário por loja e família;
- enriquecimento com metadados de loja;
- geração de previsões de curto prazo em três cenários;
- cálculo de indicadores executivos;
- comparação entre histórico e forecast;
- classificação de risco, atenção, oportunidade e plano;
- exportação do plano em CSV;
- avaliação de modelos por backtest reprodutível;
- execução local via Poetry ou containerizada via Docker.

Fora do escopo atual:

- previsão financeira com preço ou margem;
- otimização automática de estoque;
- integração com ERP, BI corporativo ou data warehouse;
- reforecast incremental em produção;
- autenticação, multiusuário e controle de permissões;
- monitoramento contínuo de drift do modelo.

## 3. Arquitetura do projeto

```text
previsao-vendas-planejamento-receita/
  assets/
    styles.css
  data/
    raw/
  docs/
    documentacao_tecnica.md
    insights_negocio.md
  notebooks/
    01_eda_dados_reais.ipynb
    02_modelagem_baselines.ipynb
    03_avaliacao_metricas.ipynb
  reports/
    model_comparison.csv
    model_comparison.json
    model_metrics.json
    model_metrics_by_family.csv
  scripts/
    download_store_sales.py
    evaluate_model.py
    setup_kaggle_token.ps1
  src/
    revenue_forecast_dashboard/
      app.py
      data.py
      figures.py
      model.py
      __main__.py
      __init__.py
  tests/
    test_dashboard_data.py
    test_forecast_models.py
```

### 3.1 Componentes principais

| Componente | Responsabilidade |
| --- | --- |
| `src/revenue_forecast_dashboard/app.py` | Define o app Dash, layout, navegação lateral, filtros, callbacks, KPIs, tabelas, exportação e estado de tela. |
| `src/revenue_forecast_dashboard/data.py` | Carrega CSVs reais, valida arquivos obrigatórios, prepara histórico, constrói forecast, aplica filtros e calcula sumários/recomendações. |
| `src/revenue_forecast_dashboard/model.py` | Define a classe base de modelos, baselines, modelo candidato, registro de modelos e métricas de avaliação. |
| `src/revenue_forecast_dashboard/figures.py` | Cria gráficos Plotly para evolução temporal, mix de vendas, gap vs. plano e estados vazios. |
| `scripts/download_store_sales.py` | Baixa e extrai a base Kaggle, validando credenciais e arquivos mínimos. |
| `scripts/evaluate_model.py` | Executa backtest, compara modelos e grava relatórios em `reports/`. |
| `reports/` | Armazena métricas consolidadas e comparativos usados pela aplicação e pelos notebooks. |
| `notebooks/` | Documenta EDA, modelagem e avaliação de métricas em formato exploratório. |
| `tests/` | Valida carregamento, cenários, recomendações, registro de modelos e métricas. |
| `Dockerfile` e `docker-compose.yml` | Empacotam dashboard e ambiente de notebooks. |

## 4. Fonte de dados

A fonte utilizada é a competição Kaggle Store Sales - Time Series Forecasting, baseada em dados da Corporación Favorita.

### 4.1 Arquivos obrigatórios

| Arquivo | Uso no projeto |
| --- | --- |
| `train.csv` | Histórico diário por loja, família, vendas e promoções. É a principal fonte para treino, backtest e dashboard. |
| `stores.csv` | Metadados das lojas, usados para construir nomes de loja e região. |

### 4.2 Arquivos opcionais

| Arquivo | Uso atual |
| --- | --- |
| `test.csv` | Promoções futuras. Quando disponível, alimenta o forecast com `onpromotion` real do horizonte futuro. |
| `transactions.csv` | Reservado para exploração e futuras melhorias de modelagem. |
| `oil.csv` | Reservado para exploração de variáveis externas. |
| `holidays_events.csv` | Reservado para exploração de feriados e eventos. |
| `sample_submission.csv` | Não usado diretamente pelo dashboard. |

### 4.3 Contrato mínimo de dados

`train.csv` deve conter:

| Coluna | Tipo esperado | Observação |
| --- | --- | --- |
| `date` | data | Data diária da observação. |
| `store_nbr` | inteiro | Identificador da loja. |
| `family` | texto/categoria | Família de produto. |
| `sales` | numérico | Volume de vendas usado como métrica operacional. |
| `onpromotion` | inteiro | Quantidade de itens em promoção. |

`stores.csv` deve conter:

| Coluna | Tipo esperado | Observação |
| --- | --- | --- |
| `store_nbr` | inteiro | Chave de relacionamento com o histórico. |
| `city` | texto | Usada para compor o nome amigável da loja. |
| `state` | texto | Usada como região. |
| `type` | texto | Reservada para análise futura. |
| `cluster` | inteiro | Reservada para análise futura. |

## 5. Fluxo de processamento

O fluxo operacional pode ser resumido em oito etapas:

1. Baixar os dados reais via `scripts/download_store_sales.py`.
2. Armazenar os CSVs em `data/raw/` ou configurar `STORE_SALES_DATA_DIR`.
3. Carregar `train.csv` e `stores.csv` com `load_history`.
4. Enriquecer o histórico com nome da loja e região.
5. Converter `sales` para a coluna interna `revenue` e marcar linhas promocionais.
6. Selecionar o modelo ativo a partir de `reports/model_metrics.json` ou da variável `FORECAST_MODEL_NAME`.
7. Gerar previsões para até 90 dias em três cenários: conservador, esperado e otimista.
8. Calcular KPIs, gráficos, tabela de recomendações e exportação de plano.

### 5.1 Preparação do histórico

A função `load_history` lê apenas as colunas necessárias, aplica tipos econômicos de memória e garante que vendas negativas sejam truncadas para zero. Em seguida, a base é enriquecida com:

- `store`: nome de exibição no padrão cidade + número da loja;
- `region`: estado da loja, com fallback para cidade ou Equador;
- `revenue`: cópia operacional de `sales`;
- `promo`: indicador booleano derivado de `onpromotion > 0`.

### 5.2 Cache

O carregamento completo de histórico e forecast é protegido por `lru_cache(maxsize=4)` em `_load_real_data_cached`. Isso reduz recálculo durante a navegação no dashboard, principalmente quando filtros são alterados de forma recorrente.

## 6. Modelagem de previsão

### 6.1 Classe base

Todos os modelos derivam de `RetailForecastModel`, que define:

- horizonte máximo padrão de 90 dias;
- janela de lookback padrão de 112 dias;
- agrupamento por loja, região e família;
- criação de perfil recente de cada série;
- geração de previsões por data futura;
- expansão por cenário;
- cálculo de confiança e risco operacional.

O perfil da série considera:

- média dos últimos 28 dias;
- média do período anterior de 28 dias;
- média dos últimos 14 dias;
- média por dia da semana;
- último valor por dia da semana;
- último valor observado;
- volatilidade relativa;
- tendência recente limitada entre -25% e +25%;
- promoção mediana;
- percentil 75 de promoção.

### 6.2 Modelos disponíveis

| Modelo | Tipo | Descrição |
| --- | --- | --- |
| `LastValueBaseline` | Baseline | Repete o último valor observado. |
| `MovingAverageBaseline` | Baseline | Usa a média recente da série. |
| `SeasonalNaiveBaseline` | Baseline | Usa o último valor observado para o mesmo dia da semana. |
| `WeekdayAverageBaseline` | Baseline | Usa a média histórica recente do mesmo dia da semana. |
| `SeasonalPromotionTrendForecaster` | Candidato | Combina sazonalidade semanal, médias recentes, tendência e intensidade promocional. |

### 6.3 Seleção do modelo ativo

A seleção segue esta ordem:

1. Se `FORECAST_MODEL_NAME` estiver definida, o projeto tenta usar o modelo informado.
2. Se `reports/model_metrics.json` existir, o dashboard usa o modelo vencedor registrado no arquivo.
3. Se nenhuma opção anterior estiver disponível, o fallback é `SeasonalPromotionTrendForecaster`.

Quando um nome inválido é informado, `get_model_by_name` retorna o modelo candidato `SeasonalPromotionTrendForecaster`.

### 6.4 Cenários

Os cenários são definidos em `data.py`:

| Cenário | Multiplicador | Interpretação |
| --- | ---: | --- |
| Conservador | 0,92 | Redução de 8% sobre a previsão esperada. |
| Esperado | 1,00 | Previsão central do modelo ativo. |
| Otimista | 1,11 | Aumento de 11% sobre a previsão esperada. |

Esses cenários não são modelos independentes. Eles são uma camada de planejamento aplicada sobre a previsão central para apoiar discussão executiva.

### 6.5 Confiança e risco

O projeto calcula dois indicadores interpretáveis para cada previsão:

- `risk_score`: combina volatilidade histórica, avanço do horizonte, intensidade promocional e crescimento acima da média recente.
- `confidence`: deriva do risco e do horizonte, limitada entre 64% e 94%.

Esses indicadores não substituem intervalos estatísticos formais de previsão. Eles funcionam como heurísticas operacionais para priorização de atenção no dashboard.

## 7. Backtest e métricas

O backtest reprodutível é executado por:

```bash
poetry run python scripts/evaluate_model.py
```

O script:

- carrega o histórico real;
- separa treino e validação;
- usa os últimos 16 dias como janela de validação;
- preserva as promoções observadas do período de validação como entrada futura;
- avalia todos os modelos do registro;
- calcula métricas padronizadas;
- seleciona o modelo com menor WAPE;
- grava relatórios em `reports/`.

### 7.1 Último resultado registrado

| Indicador | Valor |
| --- | ---: |
| Janela de validação | 2017-07-31 a 2017-08-15 |
| Fim do treino | 2017-07-30 |
| Séries avaliadas | 1.782 |
| Linhas avaliadas | 28.512 |
| Modelos testados | 5 |
| Modelo selecionado | `WeekdayAverageBaseline` |
| MAE | 84,12 |
| RMSE | 302,76 |
| RMSLE | 0,546 |
| SMAPE | 47,07% |
| WAPE | 18,01% |
| Bias | +1,97% |
| Ganho de WAPE vs. baseline principal | 12,86% |

### 7.2 Comparativo de modelos

| Modelo | Papel | WAPE | SMAPE | Bias | RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| `WeekdayAverageBaseline` | Baseline | 18,01% | 47,07% | +1,97% | 302,76 |
| `SeasonalPromotionTrendForecaster` | Candidato | 19,85% | 47,70% | +11,10% | 308,24 |
| `SeasonalNaiveBaseline` | Baseline principal | 20,67% | 43,34% | +0,41% | 348,38 |
| `MovingAverageBaseline` | Baseline | 20,81% | 47,71% | +1,34% | 318,55 |
| `LastValueBaseline` | Baseline | 44,42% | 50,82% | +34,99% | 725,69 |

### 7.3 Definição das métricas

| Métrica | Interpretação |
| --- | --- |
| MAE | Erro absoluto médio, na unidade original de vendas. |
| RMSE | Penaliza erros grandes com maior intensidade. |
| RMSLE | Avalia erro relativo em escala logarítmica, reduzindo impacto de séries muito grandes. |
| SMAPE | Erro percentual simétrico médio. Útil para comparar séries de escalas diferentes, mas sensível a valores próximos de zero. |
| WAPE | Erro absoluto ponderado pelo volume real total. É a métrica de seleção do projeto. |
| Bias | Tendência agregada de superestimar ou subestimar. Valor positivo indica superestimação. |

## 8. Dashboard

O dashboard é composto por uma navegação lateral e uma visão principal com filtros, indicadores, gráficos e recomendações.

### 8.1 Filtros

| Filtro | Opções |
| --- | --- |
| Período histórico | Últimos 90 dias, últimos 120 dias ou ano atual. |
| Loja | Todas as lojas ou uma loja específica. |
| Família | Todas as famílias ou uma família específica. |
| Horizonte | 30, 60 ou 90 dias. |
| Cenário | Conservador, esperado ou otimista. |

### 8.2 Indicadores executivos

| KPI | Cálculo |
| --- | --- |
| Vendas previstas | Soma da previsão no cenário selecionado. |
| Crescimento previsto | Variação percentual vs. período histórico comparável. |
| Confiança do forecast | Média ponderada de `confidence` pelo volume previsto. |
| Risco operacional | Média ponderada de `risk_score` pelo volume previsto. |
| Vendas em promoção | Participação do volume previsto em dias promocionais. |

### 8.3 Gráficos

| Gráfico | Objetivo |
| --- | --- |
| Evolução e forecast | Comparar histórico real com os três cenários projetados. |
| Mix de vendas | Identificar famílias ou lojas com maior contribuição no cenário. |
| Gap vs. plano | Comparar previsão com uma referência de plano baseada no período anterior acrescido de 6%. |

### 8.4 Tabela de recomendações

A tabela consolida loja, família, vendas previstas, variação vs. base, participação promocional, status e ação recomendada. A prioridade de exibição combina risco e relevância de volume.

Status possíveis:

| Status | Regra atual | Ação típica |
| --- | --- | --- |
| Risco | `risk_score >= 0,62` | Revisar abastecimento e cobertura de estoque. |
| Atenção | Queda maior que 5% vs. período anterior | Revisar meta local e ação comercial. |
| Oportunidade | Crescimento acima de 10% com risco menor que 50% | Aumentar exposição e proteger disponibilidade. |
| No plano | Demais casos | Manter plano e acompanhar execução semanal. |

### 8.5 Exportação

O botão de exportação gera `planejamento_vendas.csv` com separador `;` e colunas em português:

- `loja`;
- `familia`;
- `vendas_previstas`;
- `variacao_vs_base`;
- `participacao_promocional`;
- `risco`;
- `confianca`;
- `status`;
- `acao_recomendada`.

## 9. Execução local

### 9.1 Instalação com Poetry

```bash
poetry install
```

### 9.2 Baixar dados

Configure a credencial Kaggle e execute:

```bash
poetry run python scripts/download_store_sales.py
```

Também é possível usar um diretório alternativo:

```bash
poetry run python scripts/download_store_sales.py --output-dir caminho/para/dados
```

### 9.3 Rodar dashboard

```bash
poetry run dashboard-receita
```

URL padrão:

```text
http://localhost:8050
```

### 9.4 Rodar avaliação de modelos

```bash
poetry run python scripts/evaluate_model.py
```

### 9.5 Rodar testes

```bash
poetry run pytest
```

## 10. Execução com Docker

### 10.1 Dashboard

```bash
docker compose up --build dashboard
```

URL:

```text
http://localhost:8050
```

O serviço monta `./data/raw` como volume somente leitura em `/app/data/raw`.

### 10.2 Notebooks

```bash
docker compose up --build notebooks
```

URL:

```text
http://localhost:8888/lab?token=receita
```

O token pode ser alterado com a variável `JUPYTER_TOKEN`.

## 11. Variáveis de ambiente

| Variável | Uso | Padrão |
| --- | --- | --- |
| `STORE_SALES_DATA_DIR` | Diretório dos CSVs reais. | `data/raw` no diretório de execução. |
| `FORECAST_MODEL_NAME` | Força um modelo específico do registro. | Modelo vencedor em `reports/model_metrics.json`. |
| `DASH_HOST` | Host do servidor Dash. | `127.0.0.1`. |
| `DASH_PORT` | Porta do servidor Dash. | `8050`. |
| `DASH_DEBUG` | Ativa debug do Dash quando `true`. | `false`. |
| `DASH_ASSETS_FOLDER` | Pasta de assets do Dash. | `assets` na raiz do projeto. |
| `KAGGLE_API_TOKEN` | Token de autenticação Kaggle. | Não definido. |
| `KAGGLE_USERNAME` e `KAGGLE_KEY` | Alternativa de autenticação Kaggle. | Não definido. |
| `JUPYTER_TOKEN` | Token do Jupyter Lab no Docker. | `receita`. |

## 12. Qualidade e testes

Os testes automatizados cobrem:

- carregamento de dados no formato real esperado;
- geração dos três cenários;
- cálculo de sumário executivo;
- geração da tabela de recomendações;
- presença dos modelos principais no registro;
- fallback de modelo inválido;
- cálculo das métricas de avaliação.

Comando recomendado antes de publicar alterações:

```bash
poetry run pytest
poetry run ruff check .
```

## 13. Governança e segurança

Recomendações atuais:

- não versionar `.env`, tokens Kaggle ou arquivos de credenciais;
- manter dados brutos em `data/raw/` fora de commits quando houver restrição de licença;
- usar `data/raw/.gitkeep` apenas para preservar a estrutura da pasta;
- revisar termos de uso da Kaggle antes de distribuir os dados;
- documentar a data de geração dos relatórios em `reports/` quando houver novo backtest;
- validar se o modelo ativo no dashboard corresponde ao último benchmark aprovado.

## 14. Limitações conhecidas

1. A base não contém preço, margem ou faturamento financeiro.
2. A coluna interna `revenue` representa `sales`, não receita contábil.
3. Os cenários são multiplicadores fixos, não projeções probabilísticas.
4. A confiança e o risco são heurísticas interpretáveis, não intervalos estatísticos calibrados.
5. O backtest atual usa uma janela curta de 16 dias.
6. O modelo selecionado é um baseline forte por dia da semana, não um modelo causal.
7. Variáveis externas como feriados, petróleo e transações ainda não entram no modelo ativo.
8. Famílias de baixo volume podem ter WAPE instável e exigir tratamento separado.

## 15. Rotina recomendada de manutenção

| Frequência | Atividade |
| --- | --- |
| Semanal | Atualizar dados, executar avaliação, revisar variações de WAPE e bias. |
| Quinzenal | Validar famílias com maior erro e revisar regras de status. |
| Mensal | Comparar modelos, recalibrar cenários e revisar métricas executivas. |
| Trimestral | Reavaliar arquitetura, variáveis externas, integração de preços e governança de dados. |

## 16. Próximas evoluções técnicas

Prioridades sugeridas:

1. Integrar preços ou ticket médio para estimar receita financeira real.
2. Incluir feriados e eventos no modelo candidato.
3. Criar backtests com múltiplas janelas temporais.
4. Medir desempenho por loja, região, família e faixa de volume.
5. Separar famílias de baixa demanda em estratégia específica.
6. Adicionar intervalos de previsão calibrados.
7. Persistir forecast gerado para auditoria e comparação histórica.
8. Criar camada de configuração para regras de risco e cenário.
9. Adicionar pipeline automatizado de atualização e validação.
10. Publicar documentação de API interna caso o projeto evolua para serviço.
