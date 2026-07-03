# Insights de Negócio

Projeto: Previsão de Vendas e Planejamento de Receita  
Base analítica: Store Sales - Time Series Forecasting  
Última atualização: 2026-07-03

## 1. Resumo executivo

O projeto transforma dados históricos de vendas por loja e família de produto em uma visão executiva para planejamento comercial. A solução permite acompanhar previsão de vendas, crescimento esperado, risco operacional, dependência promocional, mix de contribuição, gap vs. plano e ações recomendadas.

O último backtest selecionou o modelo `WeekdayAverageBaseline`, com WAPE de 18,01% e bias de +1,97% em uma janela de validação de 16 dias. Na prática, isso indica que o padrão por dia da semana é um sinal forte para o negócio e deve ser tratado como referência mínima para qualquer evolução futura de modelagem.

Ponto crítico de interpretação: a base não possui preço ou margem. Portanto, os números representam volume de vendas registrado em `sales`, usado como proxy operacional para planejamento de receita. Para decisões financeiras, é necessário integrar preços, ticket médio ou margem por família e loja.

## 2. Perguntas de negócio respondidas

O dashboard ajuda a responder:

- quanto venderemos nos próximos 30, 60 ou 90 dias;
- quais lojas e famílias concentram o maior volume previsto;
- onde existe maior risco operacional;
- onde há queda relevante em relação ao período anterior;
- quais frentes têm oportunidade de crescimento com risco controlado;
- qual parcela do plano depende de promoções;
- que ações semanais devem ser priorizadas por loja e família;
- como o cenário conservador, esperado ou otimista altera o plano.

O dashboard ainda não responde:

- qual será a receita financeira em moeda;
- qual será a margem esperada;
- qual preço maximiza receita;
- quanto estoque comprar automaticamente;
- qual promoção causa incremento real;
- qual é o impacto causal de feriados, óleo ou eventos.

## 3. Resultado atual do modelo

### 3.1 Benchmark consolidado

| Indicador | Resultado |
| --- | ---: |
| Modelo vencedor | `WeekdayAverageBaseline` |
| Janela de validação | 2017-07-31 a 2017-08-15 |
| Séries avaliadas | 1.782 |
| Linhas avaliadas | 28.512 |
| WAPE | 18,01% |
| Bias | +1,97% |
| SMAPE | 47,07% |
| RMSE | 302,76 |
| Ganho vs. baseline principal | 12,86% |

### 3.2 Leitura executiva

O WAPE de 18,01% significa que, no agregado da validação, o erro absoluto representou aproximadamente 18% do volume real vendido. Para planejamento executivo, esse nível pode ser útil para priorização, discussão de metas e sinalização de risco, mas ainda exige prudência para decisões finas de abastecimento ou orçamento financeiro.

O bias de +1,97% indica leve tendência de superestimação no agregado. Esse valor é relativamente controlado, especialmente quando comparado ao modelo candidato com tendência promocional, que apresentou bias de +11,10%.

## 4. Principais insights

### 4.1 Sazonalidade semanal é o sinal dominante

O modelo vencedor usa a média recente por dia da semana. Isso sugere que o comportamento das vendas no varejo analisado tem forte estrutura semanal. Para a operação, essa descoberta é útil porque reforça a importância de planejar abastecimento, escala e ações comerciais considerando o calendário semanal, não apenas médias gerais.

Implicações:

- metas diárias devem respeitar padrões de segunda a domingo;
- rupturas e cobertura de estoque precisam ser avaliadas por dia da semana;
- campanhas devem considerar o comportamento natural do calendário;
- modelos futuros precisam preservar esse componente como referência.

### 4.2 Promoção ainda precisa de calibração

O modelo `SeasonalPromotionTrendForecaster` incorpora intensidade promocional, média recente e tendência. Apesar disso, ficou atrás do baseline semanal: WAPE de 19,85% contra 18,01% do vencedor.

A leitura de negócio não é que promoção seja irrelevante. A leitura correta é que o efeito promocional atual ainda não está calibrado com precisão suficiente para superar uma sazonalidade semanal simples. Como a base informa quantidade de itens em promoção, mas não desconto, preço, exposição, mídia ou estoque disponível, o sinal promocional fica incompleto.

Implicações:

- não usar promoção como único motor de forecast;
- separar promoções fortes, fracas e recorrentes quando houver dados;
- integrar preço/desconto para medir incremento real;
- acompanhar bias em famílias altamente promocionais.

### 4.3 Último valor observado é uma referência fraca

O `LastValueBaseline` teve WAPE de 44,42% e bias de +34,99%. Esse resultado mostra que repetir a venda do último dia não é adequado para o negócio, provavelmente por causa de sazonalidade semanal, volatilidade por família e mudanças de calendário.

Implicações:

- evitar decisões comerciais baseadas apenas no desempenho do dia anterior;
- sempre comparar indicadores recentes com padrões semanais;
- usar médias e sazonalidade como referência mínima de planejamento.

### 4.4 Acurácia varia muito por família

As famílias de maior volume tendem a apresentar melhor estabilidade relativa. Exemplos do último relatório por família:

| Família | WAPE | Leitura |
| --- | ---: | --- |
| `PRODUCE` | 11,55% | Boa previsibilidade relativa no período avaliado. |
| `BREAD/BAKERY` | 14,88% | Boa previsibilidade para planejamento agregado. |
| `MEATS` | 15,27% | Erro controlado, mas requer atenção por perecibilidade. |
| `GROCERY I` | 15,77% | Alta relevância de volume com WAPE competitivo. |
| `DAIRY` | 16,52% | Boa candidata a rotinas de abastecimento guiadas por forecast. |
| `BEVERAGES` | 20,18% | Volume alto, mas com erro maior que as melhores famílias. |

Famílias de baixo volume ou demanda intermitente apresentam WAPE muito alto:

| Família | WAPE | Leitura |
| --- | ---: | --- |
| `BOOKS` | 752,37% | Série possivelmente esparsa, WAPE instável e pouco adequada a leitura percentual simples. |
| `HOME APPLIANCES` | 286,59% | Baixo giro ou alta irregularidade. |
| `BABY CARE` | 138,49% | Necessita tratamento específico. |
| `SCHOOL AND OFFICE SUPPLIES` | 102,88% | Provável dependência de calendário/eventos. |

Implicações:

- priorizar forecast operacional para famílias de alto volume;
- criar regras separadas para itens intermitentes;
- evitar que WAPE de famílias pequenas distorça a leitura executiva;
- avaliar famílias com métricas complementares, como erro absoluto e frequência de venda.

## 5. Como interpretar os KPIs

### 5.1 Vendas previstas

Representa a soma do forecast no horizonte e cenário selecionados. Deve ser lida como volume operacional planejado. Para transformar em receita financeira, multiplique por preço ou ticket médio confiável.

### 5.2 Crescimento previsto

Compara o forecast com o período histórico equivalente. Crescimento positivo sinaliza expansão esperada; crescimento negativo indica risco de queda, mudança de mix ou possível desalinhamento de plano.

### 5.3 Confiança do forecast

Resume a estabilidade estimada do plano. Confiança maior indica séries menos voláteis, horizonte menos distante e menor risco relativo. Confiança menor sugere necessidade de revisão manual.

### 5.4 Risco operacional

Combina volatilidade, horizonte, intensidade promocional e projeções acima da média recente. Deve ser usado para priorizar conversas com abastecimento, loja e comercial.

### 5.5 Vendas em promoção

Mostra a dependência do plano em dias promocionais. Participação elevada pode indicar oportunidade comercial, mas também risco de margem, ruptura ou sensibilidade a execução.

## 6. Playbook de decisão

| Status | Sinal de negócio | Decisão recomendada |
| --- | --- | --- |
| Risco | Alto risco operacional ou volatilidade relevante. | Revisar abastecimento, cobertura de estoque, ruptura, capacidade de loja e exposição. |
| Atenção | Queda maior que 5% vs. base comparável. | Verificar meta local, calendário, preço, campanha, concorrência e disponibilidade. |
| Oportunidade | Crescimento acima de 10% com risco controlado. | Proteger estoque, aumentar exposição e avaliar reforço comercial. |
| No plano | Sem alerta relevante. | Manter acompanhamento semanal e monitorar desvios. |

## 7. Rituais recomendados

### 7.1 Reunião semanal de execução

Participantes:

- comercial;
- abastecimento;
- operações de loja;
- planejamento;
- dados/analytics.

Agenda sugerida:

1. Revisar vendas previstas por cenário.
2. Avaliar top riscos por loja e família.
3. Validar oportunidades com maior contribuição.
4. Verificar famílias com alta dependência promocional.
5. Definir ações da semana e responsáveis.
6. Registrar exceções de negócio que o modelo não captura.

### 7.2 Revisão quinzenal de performance

Objetivo:

- comparar forecast vs. realizado;
- revisar WAPE, bias e erro por família;
- identificar famílias que precisam de tratamento específico;
- ajustar regras de status e cenários quando necessário.

### 7.3 Revisão mensal executiva

Objetivo:

- avaliar aderência do plano ao resultado agregado;
- discutir metas por cenário;
- decidir investimentos comerciais;
- priorizar integração de novas variáveis, como preço, margem e feriados.

## 8. Recomendações por área

### 8.1 Comercial

- Usar o cenário esperado como plano base.
- Usar o cenário conservador para metas mínimas e gestão de risco.
- Usar o cenário otimista para dimensionar oportunidades e campanhas.
- Priorizar famílias com alto volume e gap negativo.
- Validar promoções com alta dependência de volume.

### 8.2 Abastecimento

- Priorizar linhas com status `Risco` e volume alto.
- Cruzar forecast com cobertura de estoque e lead time.
- Tratar perecíveis com maior frequência de revisão.
- Não usar famílias intermitentes apenas por WAPE percentual.

### 8.3 Operações de loja

- Avaliar lojas com maior gap vs. plano.
- Reforçar execução em oportunidades de crescimento.
- Monitorar famílias promocionais para evitar ruptura.
- Registrar eventos locais que expliquem desvios.

### 8.4 Finanças

- Não interpretar `sales` como faturamento monetário.
- Exigir tabela de preço, ticket médio ou margem antes de projeções financeiras.
- Acompanhar bias agregado para evitar orçamento superestimado.
- Separar leitura de volume, receita bruta e margem.

## 9. Priorização prática

Uma forma simples de priorizar ações é combinar impacto e urgência:

| Prioridade | Critério sugerido | Ação |
| --- | --- | --- |
| Alta | Alto volume previsto + status `Risco`. | Ação imediata de abastecimento e operação. |
| Alta | Alto volume + queda vs. base. | Revisão comercial e validação de meta. |
| Média | Crescimento alto + baixo risco. | Proteger disponibilidade e ampliar exposição. |
| Média | Alta participação promocional. | Revisar execução e dependência de promoção. |
| Baixa | Baixo volume + erro percentual alto. | Acompanhar com regra específica, sem sobrepriorizar. |

## 10. Cuidados de interpretação

1. WAPE baixo no agregado pode esconder erros relevantes em famílias específicas.
2. SMAPE pode ficar elevado em séries pequenas ou com muitos zeros.
3. Bias positivo indica tendência de superestimar; bias negativo indica subestimar.
4. Famílias de baixo volume precisam de tratamento próprio.
5. Promoção sem preço/desconto não permite medir incremento real.
6. Forecast não substitui conhecimento operacional de ruptura, campanha, concorrência ou evento local.
7. Cenários são multiplicadores de planejamento, não probabilidades.

## 11. Evoluções de maior valor para o negócio

Prioridades recomendadas:

1. Integrar preço ou ticket médio para converter volume em receita financeira.
2. Incluir margem para priorizar crescimento rentável, não apenas volume.
3. Integrar estoque e cobertura para transformar risco em plano de compra.
4. Incluir calendário de feriados e eventos locais.
5. Separar famílias de venda intermitente em modelo ou regra própria.
6. Criar backtests por múltiplas janelas para medir estabilidade.
7. Medir forecast por região, loja, família e faixa de volume.
8. Registrar ações tomadas e comparar impacto no realizado.
9. Criar metas por cenário com aprovação executiva.
10. Integrar alertas automáticos para frentes críticas.

## 12. Conclusão executiva

O projeto já oferece uma base sólida para planejamento operacional de vendas: usa dados reais, compara modelos, seleciona o melhor benchmark por WAPE e traduz forecast em indicadores e ações. A principal descoberta atual é que a sazonalidade semanal é o melhor sinal disponível no benchmark, superando o modelo candidato com promoção e tendência.

Para elevar a solução de planejamento de vendas para planejamento financeiro de receita, o próximo passo mais importante é integrar preço, ticket médio ou margem. Com isso, o dashboard poderá separar volume, receita e rentabilidade, permitindo decisões mais precisas para comercial, abastecimento e finanças.
