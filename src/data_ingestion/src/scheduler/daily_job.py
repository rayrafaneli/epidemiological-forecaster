"""
src/scheduler/daily_job.py
===============================================================================
CAMADA: scheduler

O QUE ESTE ARQUIVO FAZ
-----------------------
Usa a biblioteca `schedule` para rodar o pipeline ETL automaticamente,
todos os dias, no horário definido em DAILY_JOB_TIME (.env). Como a
carga é feita com `upsert` (ON CONFLICT DO NOTHING/UPDATE - ver
src/load/postgres_loader.py), rodar o mesmo dia várias vezes ou reprocessar
dias antigos NUNCA duplica dados: se o registro já existe, é simplesmente
ignorado. É esse comportamento em conjunto (agendamento + upsert) que
implementa o requisito "consulte as APIs e insira apenas novos registros,
evitando duplicidades".

POR QUE UM PROCESSO PYTHON DE LONGA DURAÇÃO (schedule) E NÃO SÓ UM CRON?
-----------------------
Usar a lib `schedule` deixa a lógica de agendamento DENTRO do projeto
Python (portável entre Windows/Linux/Mac, fácil de testar). Em produção,
esse processo normalmente seria supervisionado por algo como systemd,
Docker + restart:always, ou um cron chamando `python main.py --pipeline all`
uma vez por dia - qualquer uma das duas abordagens é válida; aqui optamos
pela biblioteca `schedule` por ser mais simples de demonstrar no TCC
(basta rodar `python main.py --schedule` e deixar o processo ativo).

COMO RODAR
-----------------------
    python main.py --schedule
===============================================================================
"""

import time
import schedule

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


def _job():
    """
    Função chamada automaticamente pelo `schedule` no horário configurado.
    Importação tardia de main.run_all evita import circular (main.py também
    importa este módulo, sob demanda, quando --schedule é usado).
    """
    logger.info("Disparando execução agendada do pipeline ETL...")
    try:
        from main import run_all
        run_all()
    except Exception as exc:
        # Mesmo se o pipeline falhar, o processo do scheduler NÃO deve
        # morrer - ele deve continuar de pé para tentar novamente amanhã.
        logger.error(f"Execução agendada falhou: {exc}")


def start_scheduler():
    """Registra o job diário e entra em loop de espera (bloqueante)."""
    horario = config.scheduler.daily_job_time
    schedule.every().day.at(horario).do(_job)

    logger.info(f"Agendador iniciado. O pipeline ETL rodará todos os dias às {horario}.")
    logger.info("Pressione Ctrl+C para interromper o agendador.")

    try:
        while True:
            schedule.run_pending()
            # Dorme 30s entre verificações - suficiente para um job diário
            # (não precisamos checar a cada segundo, o que gastaria CPU à toa).
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Agendador interrompido manualmente.")
