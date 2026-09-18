# Alteracoes entre o XGBoost anterior e a versao comparativa

| Aspecto | Versao anterior | Nova versao |
|---|---|---|
| Fonte | Consulta direta ao Supabase | CSVs locais congelados e auditaveis |
| Data do caso | Data de notificacao (`dt_notific`) | Semana do inicio dos sintomas (`sem_pri`), com fallback documentado |
| Casos elegiveis | Sem filtro de classificacao final | Exclui classificacao 5 e classificacao ausente |
| Duplicidades | Nao tratadas | Remove marcacoes explicitas e duplicidade analitica conservadora |
| Bairros | Normalizacao textual simples | Lista canonica do Censo 2022, aliases deterministas e auditoria de nao mapeados |
| Populacao | Todas as linhas da tabela, causando risco de multiplicacao no join | Somente Censo 2022, uma linha por bairro |
| Semanas sem caso | Ausentes da base agregada | Painel completo com zero quando ha cobertura da fonte |
| Clima ausente | Mantido como ausente | Mediana da mesma semana epidemiologica, calculada apenas em 2015-2020 |
| Lags climaticos | Fornecidos pela fonte | Recalculados depois da imputacao |
| Historico de dengue | Nao usado | `casos_lag1` a `casos_lag4` |
| Alvo | Casos da mesma semana das entradas | Casos futuros, com horizonte configuravel de 1 a 4 semanas |
| Divisao temporal | Treino ate 2024; teste 2025 | Treino 2015-2020; teste final 2021 |
| Validacao | Teste usado como validacao | 2020 seleciona numero de arvores; 2021 e usado uma unica vez no teste final |
| Bairro no modelo | Nao era uma feature explicita | Codificacao one-hot comum aos modelos |
| Metricas | MAE e RMSE | MAE, RMSE, R2, acuracia, acuracia balanceada e F1 macro das categorias |
| Reprodutibilidade | Semente apenas no XGBoost | Semente comum, dados processados, auditorias e artefatos salvos |

## Observacao metodologica

Os numeros da versao antiga nao devem ser comparados diretamente aos novos como se fossem o mesmo experimento: o alvo, as datas, a cobertura e o recorte temporal mudaram. A comparacao justa entre XGBoost, RNA e LSTM e a produzida pela nova pipeline compartilhada.
