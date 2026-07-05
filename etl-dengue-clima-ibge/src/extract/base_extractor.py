"""
src/extract/base_extractor.py
===============================================================================
CAMADA: extract

O QUE ESTE ARQUIVO FAZ
-----------------------
Define uma classe-base (BaseExtractor) com um método `_get()` compartilhado
por todos os extratores concretos (INMET, IBGE, futuramente Recife).

POR QUE UMA CLASSE-BASE EM VEZ DE COPIAR/COLAR requests.get() EM CADA ARQUIVO?
-----------------------
1) DRY (Don't Repeat Yourself): lógica de retry/timeout fica em um só lugar.
2) Se amanhã precisarmos adicionar, por exemplo, um cabeçalho de
   autenticação padrão, alteramos em um único ponto.
3) APIs públicas (como INMET e IBGE) volta e meia engasgam ou demoram para
   responder. Um retry automático com espera crescente (backoff) evita que
   o pipeline inteiro falhe por causa de uma instabilidade momentânea.
===============================================================================
"""

import time
import requests

from src.logger import get_logger

logger = get_logger(__name__)


class BaseExtractor:
    """Classe-base com lógica de requisição HTTP resiliente."""

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 30):
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        # Uma única Session reaproveita conexões TCP entre requisições
        # (keep-alive), o que é mais eficiente do que abrir uma conexão
        # nova a cada chamada com requests.get().
        self.session = requests.Session()

    def _get(self, url: str, params: dict | None = None) -> dict | list:
        """
        Executa um GET HTTP com até `max_retries` tentativas, usando
        "exponential backoff" (espera 1s, depois 2s, depois 4s...) entre
        as tentativas. Levanta a exceção original se todas as tentativas
        falharem, para que a camada que chamou saiba que algo deu errado.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"GET {url} | params={params} | tentativa {attempt}/{self.max_retries}")
                response = self.session.get(url, params=params, timeout=self.timeout_seconds)
                response.raise_for_status()  # lança exceção se status >= 400
                return response.json()
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                wait_seconds = 2 ** (attempt - 1)
                logger.warning(
                    f"Falha na tentativa {attempt}/{self.max_retries} para {url}: {exc}. "
                    f"Aguardando {wait_seconds}s antes de tentar novamente."
                )
                time.sleep(wait_seconds)

        logger.error(f"Todas as {self.max_retries} tentativas falharam para {url}.")
        raise last_exception

    def _get_bytes(self, url: str, timeout_seconds: int | None = None) -> bytes:
        """
        Igual ao `_get()`, mas para downloads de arquivos binários (ex: ZIP),
        onde a resposta não é JSON. Usado para baixar os pacotes anuais de
        dados históricos do INMET, que podem ser relativamente grandes -
        por isso aceita um timeout maior específico para esta chamada.
        """
        last_exception: Exception | None = None
        effective_timeout = timeout_seconds or (self.timeout_seconds * 4)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"GET (binário) {url} | tentativa {attempt}/{self.max_retries}")
                response = self.session.get(url, timeout=effective_timeout)
                response.raise_for_status()
                return response.content
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                wait_seconds = 2 ** (attempt - 1)
                logger.warning(
                    f"Falha na tentativa {attempt}/{self.max_retries} para {url}: {exc}. "
                    f"Aguardando {wait_seconds}s antes de tentar novamente."
                )
                time.sleep(wait_seconds)

        logger.error(f"Todas as {self.max_retries} tentativas falharam para {url}.")
        raise last_exception
