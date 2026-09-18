# Resultado final — criticidade epidemiológica com horizonte de uma semana

## Resumo executivo

O XGBoost foi o melhor dos três modelos para prever `Baixo`, `Medio`, `Alto` e `Critico` em 2021. Obteve acurácia balanceada de **86,56%**, F1 macro de **85,18%**, F2 macro de **85,96%** e PR-AUC macro de **88,74%**. A LSTM ficou em segundo lugar e a RNA em terceiro.

O teste contém 4.888 observações bairro-semana: 4.276 Baixo, 536 Medio, 49 Alto e 27 Critico. Esse forte desbalanceamento é o motivo para não escolher o vencedor pela acurácia simples.

## Comparação global da classificação v2

| Modelo | Acurácia | Acurácia balanceada | F1 macro | F2 macro | PR-AUC macro | Erro médio de nível | Kappa quadrático |
|---|---:|---:|---:|---:|---:|---:|---:|
| XGBoost | 95,81% | 86,56% | 85,18% | 85,96% | 88,74% | 0,0423 | 0,8833 |
| LSTM | 95,77% | 80,37% | 78,89% | 79,36% | 85,24% | 0,0428 | 0,8802 |
| RNA | 94,74% | 74,26% | 69,82% | 71,78% | 71,31% | 0,0540 | 0,8503 |
| Referência: persistência | 95,29% | 78,06% | 78,06% | 78,06% | 64,18% | 0,0483 | 0,8564 |
| Referência: sempre Baixo | 87,48% | 25,00% | 23,33% | 24,30% | 25,00% | 0,1463 | 0,0000 |

As referências não são modelos concorrentes. “Persistência” repete para a semana futura a categoria observada na origem; “sempre Baixo” demonstra como a acurácia bruta pode parecer alta mesmo sem detectar agravamentos.

## Desempenho por categoria

| Modelo | Categoria | Precisão | Recall | F1 | F2 | Casos de teste |
|---|---|---:|---:|---:|---:|---:|
| XGBoost | Baixo | 99,11% | 96,73% | 97,91% | 97,19% | 4.276 |
| XGBoost | Medio | 76,29% | 91,23% | 83,09% | 87,79% | 536 |
| XGBoost | Alto | 72,34% | 69,39% | 70,83% | 69,96% | 49 |
| XGBoost | Critico | 88,89% | 88,89% | 88,89% | 88,89% | 27 |
| LSTM | Baixo | 98,58% | 97,75% | 98,17% | 97,92% | 4.276 |
| LSTM | Medio | 80,80% | 83,21% | 81,99% | 82,72% | 536 |
| LSTM | Alto | 48,72% | 77,55% | 59,84% | 69,34% | 49 |
| LSTM | Critico | 94,44% | 62,96% | 75,56% | 67,46% | 27 |
| RNA | Baixo | 98,19% | 97,85% | 98,02% | 97,92% | 4.276 |
| RNA | Medio | 79,60% | 74,25% | 76,83% | 75,26% | 536 |
| RNA | Alto | 32,69% | 69,39% | 44,44% | 56,67% | 49 |
| RNA | Critico | 65,22% | 55,56% | 60,00% | 57,25% | 27 |

## Leitura epidemiológica

- O XGBoost identificou corretamente 24 dos 27 registros Critico e não classificou nenhum deles como Baixo; os três restantes foram um Medio e dois Alto.
- Para Alto, o XGBoost acertou exatamente 34 de 49. Outros três foram classificados como Critico, onze como Medio e apenas um como Baixo.
- A LSTM teve maior recall em Alto (77,55%) que o XGBoost (69,39%), mas menor precisão e recall em Critico. Ela é uma segunda colocada plausível quando se deseja ser mais sensível a Alto, aceitando mais falsos alertas.
- A RNA detectou parte relevante de Alto e Critico, mas gerou mais confusões e ficou abaixo da regra de persistência no F1 macro.
- A taxa de subestimação grave foi 0,0409% no XGBoost e na LSTM (2 de 4.888 observações) e 0,0818% na RNA (4 de 4.888).

## Resultado do experimento numérico anterior

Essas métricas permanecem úteis para comparar a previsão de quantidade semanal, mas não medem o mesmo alvo da classificação v2.

| Modelo | MAE (casos) | RMSE (casos) | R² |
|---|---:|---:|---:|
| RNA | 0,9586 | 2,1561 | 0,6744 |
| LSTM | 0,9564 | 2,1766 | 0,6682 |
| XGBoost | 0,9747 | 2,2396 | 0,6487 |

Na regressão numérica, RNA e LSTM tiveram erro ligeiramente menor. Na tarefa central desta versão — identificar corretamente o nível epidemiológico — o XGBoost venceu com margem clara.

## Conclusão

Para o foco do TCC, o XGBoost deve ser considerado o melhor modelo no teste retrospectivo de 2021. Ele liderou acurácia balanceada, F1 macro, F2 macro, PR-AUC macro, recall de Critico e kappa quadrático, além de superar a persistência. Isso não prova desempenho prospectivo em produção: o conjunto Critico contém apenas 27 observações e os intervalos de incerteza ainda devem ser reportados como trabalho futuro.
