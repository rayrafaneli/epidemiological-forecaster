# Resultados da validação progressiva e dos horizontes de 1 a 4 semanas

## Resultado principal

O XGBoost apresentou o melhor desempenho geral quando o critério principal é detectar equilibradamente os quatro níveis, com maior F2 macro médio (63,83%) e maior acurácia balanceada média (64,90%). A LSTM ficou em segundo lugar e a RNA em terceiro.

O teste final usa exclusivamente 2021 e contém 4.888 observações bairro-semana em cada horizonte: 4.276 Baixo, 536 Medio, 49 Alto e 27 Critico. Nenhum resultado de 2021 foi utilizado para selecionar épocas, árvores, pesos ou hiperparâmetros.

## Métricas do teste de 2021

| Modelo | Horizonte | Acurácia | Acurácia balanceada | F1 macro | F2 macro | PR-AUC macro |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost | 1 | 95,85% | 86,49% | 85,21% | 85,93% | 88,90% |
| LSTM | 1 | 95,54% | 79,84% | 79,76% | 79,56% | 87,02% |
| RNA | 1 | 94,48% | 74,53% | 70,83% | 72,55% | 70,52% |
| XGBoost | 2 | 89,63% | 69,03% | 65,77% | 67,10% | 67,07% |
| LSTM | 2 | 92,88% | 63,90% | 65,74% | 64,36% | 69,16% |
| RNA | 2 | 92,08% | 58,45% | 55,76% | 56,90% | 59,56% |
| XGBoost | 3 | 88,58% | 58,06% | 58,12% | 57,45% | 59,11% |
| LSTM | 3 | 91,71% | 55,12% | 58,31% | 56,16% | 58,22% |
| RNA | 3 | 90,79% | 49,72% | 50,14% | 49,85% | 48,36% |
| XGBoost | 4 | 86,01% | 46,02% | 44,57% | 44,81% | 44,01% |
| LSTM | 4 | 89,71% | 41,74% | 43,88% | 42,37% | 44,31% |
| RNA | 4 | 88,91% | 39,97% | 37,92% | 39,06% | 43,74% |

## Média dos quatro horizontes

| Modelo | Acurácia balanceada | F1 macro | F2 macro | PR-AUC macro | Erro médio de nível | Subestimação grave |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost | 64,90% | 63,42% | 63,83% | 64,77% | 0,1032 | 0,2557% |
| LSTM | 60,15% | 61,92% | 60,61% | 64,68% | 0,0795 | 0,3222% |
| RNA | 55,67% | 53,66% | 54,59% | 55,54% | 0,0889 | 0,3222% |

## Interpretação por horizonte

- Uma semana: o XGBoost é claramente superior. Detectou 24 de 27 observações Critico e 34 de 49 Alto.
- Duas semanas: XGBoost e LSTM têm F1 macro praticamente empatado, mas o XGBoost mantém maior F2 macro e acurácia balanceada.
- Três semanas: a LSTM supera o XGBoost por 0,19 ponto percentual em F1 macro. O XGBoost permanece superior em F2 macro, acurácia balanceada e PR-AUC.
- Quatro semanas: o XGBoost volta a liderar F1/F2 e acurácia balanceada, mas o recall exato cai para 10,20% em Alto e 11,11% em Critico. Esse horizonte deve ser tratado como sinal antecipado de risco, não como classificação exata confiável.

## Efeito do horizonte

O F2 macro do XGBoost diminui de 85,93% em uma semana para 44,81% em quatro semanas. A queda é esperada porque o alvo usa uma incidência acumulada em quatro semanas: no horizonte 1, três semanas da janela já são observadas; no horizonte 4, toda a janela está à frente da origem da previsão.

Esse resultado é metodologicamente mais informativo que apresentar apenas o horizonte 1. Ele separa um alerta de curtíssimo prazo, bastante confiável, de uma antecipação mensal, que ainda possui incerteza elevada.

## Otimização selecionada para o XGBoost

| Horizonte | Árvores | Learning rate | Profundidade | Min child weight | Gamma | Subsample | Colsample | Lambda | Alpha | Potência do peso |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 593 | 0,035 | 5 | 2 | 0,0 | 0,85 | 0,85 | 2,0 | 0,05 | 0,75 |
| 2 | 572 | 0,020 | 5 | 2 | 0,5 | 1,00 | 0,85 | 5,0 | 0,20 | 1,00 |
| 3 | 494 | 0,080 | 3 | 8 | 0,5 | 0,70 | 1,00 | 5,0 | 1,00 | 0,75 |
| 4 | 493 | 0,080 | 3 | 8 | 0,5 | 0,70 | 1,00 | 5,0 | 1,00 | 0,75 |

## Comparação com a versão anterior no horizonte 1

- XGBoost: F1 macro passou de 85,18% para 85,21%; PR-AUC passou de 88,74% para 88,90%.
- LSTM: F1 macro passou de 78,89% para 79,76%; PR-AUC passou de 85,24% para 87,02%.
- RNA: F1 macro passou de 69,82% para 70,83%; F2 macro passou de 71,78% para 72,55%.

A alteração mais importante não é o pequeno ganho numérico em uma semana, mas a redução do risco de escolher configurações adaptadas a um único ano. A validação progressiva mede cinco transições temporais diferentes antes do teste final.

## Conclusão

O XGBoost continua sendo a escolha principal para o TCC. Ele lidera o critério de maior interesse epidemiológico nos quatro horizontes: F2 macro e acurácia balanceada. A LSTM é uma comparação competitiva, especialmente em F1 no horizonte 3 e no erro ordinal médio. A RNA apresenta desempenho inferior, sobretudo para Alto e Critico nos horizontes mais longos.
