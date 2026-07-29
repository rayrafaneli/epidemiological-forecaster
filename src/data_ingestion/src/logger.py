"""
src/logger.py
===============================================================================
CAMADA: Transversal (usada por todas as outras camadas)

POR QUE NÃO USAR print()?
-----------------------
print() não tem nível de severidade (info, warning, error), não mostra
automaticamente data/hora, e não pode ser facilmente redirecionado para um
arquivo. Um pipeline que roda sozinho todo dia (via scheduler) precisa
deixar rastro em arquivo de log, para que, se algo falhar às 3h da manhã,
seja possível investigar depois. O módulo `logging` da biblioteca padrão do
Python resolve isso.

COMO USAR EM OUTRO ARQUIVO
-----------------------
    from src.logger import get_logger
    logger = get_logger(__name__)
    logger.info("mensagem")
===============================================================================
"""

import logging
import sys
from pathlib import Path

from src.config import config

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)  # cria a pasta logs/ se ainda não existir


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com dois "destinos" (handlers):
    1) Console (stdout) - para acompanhar em tempo real durante o desenvolvimento.
    2) Arquivo (logs/etl.log) - para consultar depois, principalmente quando
       o pipeline roda automaticamente pelo scheduler, sem ninguém olhando.
    """
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados se essa função for chamada
    # várias vezes para o mesmo módulo (aconteceria se não checássemos isso).
    if logger.handlers:
        return logger

    logger.setLevel(config.log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "etl.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
