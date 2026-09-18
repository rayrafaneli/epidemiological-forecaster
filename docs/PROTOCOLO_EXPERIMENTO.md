# Protocolo do experimento comparativo

- Unidade de analise: bairro por semana epidemiologica.
- Populacao: Censo 2022, constante em todo o periodo.
- Treinamento final: semanas-alvo de 2015 a 2020.
- Validacao interna: 2020; usada para selecionar arvores/epocas.
- Teste final: semanas-alvo de 2021; nunca usado na imputacao nem na selecao do treinamento.
- Horizonte: 1 a 4 semanas, com padrao de uma semana.
- Historico observavel: quatro semanas terminando na semana de origem da previsao.
- Imputacao climatica: mediana da mesma semana epidemiologica, calculada exclusivamente em 2015-2020.
- Alvo: numero de casos na semana futura.
- Incidencia: casos previstos divididos pela populacao do bairro e multiplicados por 100.000.
- Categorias: Baixo < 100; Medio < 300; Alto < 500; Critico >= 500 casos por 100 mil habitantes.
- Comparacao principal: RMSE/MAE para contagem e acuracia balanceada/F1 macro para categoria.
- Predicoes negativas sao limitadas a zero; arredondamento e aplicado apenas para incidencia/categoria.
- O teste e retrospectivo e deslizante: para cada semana-alvo de 2021, usam-se apenas as quatro semanas imediatamente anteriores que ja estariam disponiveis naquela data.

`casos_lag1` representa a semana mais recente disponivel na origem da previsao; `casos_lag4`, a quarta semana observada. A LSTM recebe essas mesmas quatro semanas como sequencia, enquanto XGBoost e RNA recebem as quatro observacoes como colunas.

## Interpretacao das categorias

A acuracia simples nao deve ser usada isoladamente. Como a classe `Baixo` domina as observacoes bairro-semana, um modelo pode ter acuracia alta e ainda falhar nos surtos raros. Para discutir capacidade de alerta, priorize recall por classe, acuracia balanceada, F1 macro e a matriz de confusao, sempre junto de MAE/RMSE.
