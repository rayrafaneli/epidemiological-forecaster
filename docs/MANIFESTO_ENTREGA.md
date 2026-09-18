# Manifesto da entrega

## Codigo novo

- `src/config.py`: periodos, horizonte, caminhos, sementes e categorias.
- `src/data_pipeline.py`: filtros, deduplicacao, bairros, clima, lags e painel.
- `src/evaluation.py`: metricas de regressao e classificacao.
- `src/modeling.py`: pre-processamento e arquiteturas neurais.
- `prepare_data.py`: gera as bases processadas.
- `train_xgboost.py`: novo treinamento XGBoost.
- `train_ann.py`: treinamento da Rede Neural Artificial.
- `train_lstm.py`: treinamento LSTM.
- `compare_results.py`: comparacao e matrizes de confusao.
- `run_all.py`: execucao completa para horizonte de 1 a 4 semanas.
- `validate_outputs.py`: checagem final dos artefatos.
- `tests/`: testes de regras e integridade temporal.

## Dados processados

- CSV e XLSX de populacao Censo 2022.
- CSV e XLSX dos casos de dengue elegiveis de 2015-2021.
- CSV e XLSX do clima de 2015-2021 com imputacoes sinalizadas.
- CSV e XLSX do painel bairro-semana para horizonte 1.
- CSVs de registros removidos, mapeamento de bairros e imputacoes climaticas.

## Resultados

- Modelo e pre-processadores de XGBoost, RNA e LSTM.
- Previsoes linha a linha de 2021.
- Metricas gerais e por categoria.
- Matrizes de confusao e historicos de treinamento neural.

O codigo legado, o README anterior e o modelo XGBoost antigo foram mantidos na copia para rastreabilidade; os novos artefatos ficam em `models`, `results`, `data/processed` e nos arquivos de nivel raiz listados acima.
