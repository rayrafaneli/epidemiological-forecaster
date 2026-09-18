# Comparacao XGBoost, Rede Neural Artificial e LSTM

Este diretorio e uma copia independente do projeto original. Ele prepara os dados de Recife, treina os tres modelos com o mesmo protocolo e produz resultados tabulares, sem interface visual.

## Recorte e regras

- Dados-alvo de treinamento: 2015-2020.
- Teste final: 2021.
- Horizonte padrao: uma semana; configuravel de 1 a 4.
- Populacao: Censo 2022 em todos os anos.
- Caso elegivel: classificacao final informada e diferente de 5.
- Semana do caso: `sem_pri`; se invalida, semana epidemiologica derivada de `dt_sin_pri`.
- Clima ausente: mediana da mesma semana epidemiologica calculada somente em 2015-2020.
- Semanas sem caso: zero dentro da cobertura escolhida.
- Historico: quatro semanas de casos e clima.

## Execucao

Instale as dependencias de `requirements-ml.txt` e, na raiz deste diretorio, execute:

```powershell
python run_all.py --horizon 1
```

Troque `1` por `2`, `3` ou `4` para mudar o horizonte. A constante equivalente fica em `src/config.py` (`FORECAST_HORIZON_WEEKS`).

Tambem e possivel executar cada etapa separadamente:

```powershell
python prepare_data.py --horizon 1
python train_xgboost.py --horizon 1
python train_ann.py --horizon 1
python train_lstm.py --horizon 1
python compare_results.py --horizon 1
```

## Saidas

- `data/processed`: tres fontes limpas, painel semanal e auditorias.
- `models`: modelos treinados, escalonadores e codificadores.
- `results`: previsoes individuais, metricas, historicos de treino e comparacao consolidada.
- `docs`: protocolo, resultados e diferencas para o XGBoost anterior.

O resultado principal do horizonte padrao e `results/comparacao_modelos_h1.csv`. Para avaliar surtos, nao use apenas a acuracia: consulte tambem `comparacao_categorias_h1.csv` e `matrizes_confusao_h1.csv`.

## Testes

```powershell
python -m unittest discover -s tests -v
```
