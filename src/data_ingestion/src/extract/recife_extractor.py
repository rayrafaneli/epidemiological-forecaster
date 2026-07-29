"""
src/extract/recife_extractor.py
===============================================================================
CAMADA: extract

O QUE ESTE ARQUIVO FAZ (E POR QUE ELE JÁ EXISTE SEM ESTAR "PRONTO")
-----------------------
Este é um SCAFFOLD (esqueleto) para a futura integração com a API da
Prefeitura do Recife, que hoje ainda não está definida/documentada
publicamente o suficiente para implementarmos de verdade.

Por que criar esse arquivo já na Sprint 1, se ele não faz nada ainda?
Porque um dos requisitos do projeto é "preparar o projeto para futuramente
integrar dados da Prefeitura do Recife". Deixando o contrato (a assinatura
dos métodos) definido agora, garantimos que:

1) A tabela `casos_dengue` (ver sql/ddl.sql) já foi modelada pensando nesse
   formato de dados.
2) Quando a API for definida, quem for implementar (você, ou outro membro
   da equipe) só precisa preencher o método `extract()` - não precisa
   redesenhar a arquitetura do projeto.
3) O `main.py` já pode referenciar essa classe condicionalmente, sem
   quebrar o pipeline atual (INMET + IBGE).

Este extrator HERDA de BaseExtractor pelos mesmos motivos dos outros
(retry, timeout, sessão HTTP reaproveitável) - assim que a URL real da API
for configurada no .env (RECIFE_API_BASE_URL), o método `extract()` pode
ser implementado seguindo o mesmo padrão de `inmet_extractor.py` /
`ibge_extractor.py`.
===============================================================================
"""

import pandas as pd

from src.extract.base_extractor import BaseExtractor
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


class RecifeExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.base_url = config.recife.base_url
        self.token = config.recife.token

    def is_configured(self) -> bool:
        """Só faz sentido tentar extrair se a URL da API já foi definida no .env."""
        return bool(self.base_url)

    def extract(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        MÉTODO A SER IMPLEMENTADO NA PRÓXIMA SPRINT.

        Quando a API da Prefeitura do Recife for integrada, este método
        deve:
        1) Chamar self._get(url, params) para buscar os casos notificados
           no intervalo [start_date, end_date].
        2) Retornar um DataFrame com colunas cruas (antes da limpeza),
           que serão tratadas em src/transform/recife_transformer.py
           (a ser criado) e carregadas na tabela `casos_dengue`.

        Por enquanto, levantamos um erro claro em vez de falhar
        silenciosamente ou retornar dados fictícios.
        """
        if not self.is_configured():
            logger.warning(
                "RecifeExtractor ainda não está configurado (RECIFE_API_BASE_URL vazio no .env). "
                "Esta integração está planejada para uma sprint futura."
            )
            return pd.DataFrame()

        raise NotImplementedError(
            "A integração com a API da Prefeitura do Recife será implementada "
            "em uma sprint futura, assim que o endpoint oficial for definido."
        )
