# Resultados do teste final de 2021 — horizonte de uma semana

| Modelo | MAE (casos) | RMSE (casos) | R2 | Acuracia de categoria | Acuracia balanceada | F1 macro |
|---|---:|---:|---:|---:|---:|---:|
| RNA | 0,959 | 2,156 | 0,674 | 98,732% | 27,595% | 29,068% |
| LSTM | 0,956 | 2,177 | 0,668 | 98,691% | 25,418% | 25,642% |
| XGBoost | 0,975 | 2,240 | 0,649 | 98,711% | 30,191% | 31,985% |

No erro de contagem, a RNA obteve o menor RMSE e o maior R2; a LSTM obteve o menor MAE por pequena margem. Na classificacao de risco, o XGBoost foi o melhor dos tres em acuracia balanceada e F1 macro.

## Limite importante

Das 4.888 observacoes de teste, 4.827 sao `Baixo`, 57 `Medio`, 3 `Alto` e 1 `Critico`. Nenhum modelo identificou corretamente os tres exemplos `Alto` nem o unico exemplo `Critico`. Portanto, a acuracia de aproximadamente 98,7% nao pode ser descrita como 98,7% de capacidade de detectar surtos. Este teste sustenta comparacao de erro geral, mas ainda tem poucos eventos graves para estimar com estabilidade a sensibilidade a surtos.

Os arquivos `comparacao_categorias_h1.csv` e `matrizes_confusao_h1.csv` apresentam os valores completos por classe.
