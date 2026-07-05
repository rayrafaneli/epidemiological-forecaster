"""
src/config.py
===============================================================================
CAMADA: Configuração (transversal - usada por todas as outras camadas)

O QUE ESTE ARQUIVO FAZ
-----------------------
Centraliza a leitura de variáveis de ambiente (arquivo .env) em um único
lugar. Em vez de cada módulo do projeto chamar os.getenv("DB_HOST") em
pontos diferentes do código (o que dificulta saber "quais variáveis esse
projeto usa?"), toda configuração fica documentada e tipada aqui, em uma
única classe.

POR QUE UMA DATACLASS?
-----------------------
Uma `dataclass` do Python gera automaticamente o construtor (__init__) e
outros métodos úteis, a partir apenas da declaração dos atributos e seus
tipos. Isso deixa o código mais legível e ajuda o autocomplete da IDE a te
avisar se você digitar o nome errado de uma configuração.
===============================================================================
"""

from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

# BASE_DIR aponta para a raiz do projeto (a pasta onde está este arquivo, subindo 2 níveis: src/ -> raiz)
BASE_DIR = Path(__file__).resolve().parent.parent

# load_dotenv() procura um arquivo ".env" na raiz e carrega suas variáveis
# para o ambiente do processo (os.environ). Se o .env não existir, o
# programa não quebra aqui - ele só vai falhar depois, quando tentar ler
# uma variável obrigatória que não foi definida. Por isso validamos abaixo.
load_dotenv(BASE_DIR / ".env")


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    """
    Função auxiliar para ler uma variável de ambiente com uma mensagem de
    erro clara caso ela seja obrigatória e não tenha sido definida.

    Por que não usar direto os.environ[key]?
    Porque o erro padrão do Python (KeyError) não diz o que fazer para
    corrigir. Aqui, orientamos o usuário a checar o arquivo .env.
    """
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(
            f"A variável de ambiente '{key}' é obrigatória e não foi encontrada. "
            f"Verifique se o arquivo .env existe na raiz do projeto e contém '{key}=...'. "
            f"Use o .env.example como referência."
        )
    return value


@dataclass
class DatabaseConfig:
    """Agrupa tudo que é necessário para conectar ao PostgreSQL."""
    host: str = field(default_factory=lambda: _get_env("DB_HOST", "localhost"))
    port: str = field(default_factory=lambda: _get_env("DB_PORT", "5432"))
    name: str = field(default_factory=lambda: _get_env("DB_NAME", required=True))
    user: str = field(default_factory=lambda: _get_env("DB_USER", required=True))
    password: str = field(default_factory=lambda: _get_env("DB_PASSWORD", required=True))

    @property
    def sqlalchemy_url(self) -> str:
        """
        Monta a URL de conexão no formato que o SQLAlchemy espera:
        postgresql+psycopg2://usuario:senha@host:porta/nome_do_banco
        """
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass
class InmetConfig:
    """Configurações específicas da extração de dados do INMET."""
    base_url: str = field(default_factory=lambda: _get_env(
        "INMET_API_BASE_URL", "https://apitempo.inmet.gov.br"))
    # Pacotes anuais oficiais de dados históricos (fonte estável, usada para
    # o clima diário desde 2021 - ver src/extract/inmet_extractor.py para
    # o porquê de usarmos isso em vez da API "apitempo" para o histórico).
    historical_data_base_url: str = field(default_factory=lambda: _get_env(
        "INMET_HISTORICAL_DATA_BASE_URL", "https://portal.inmet.gov.br/uploads/dadoshistoricos"))
    start_date: str = field(default_factory=lambda: _get_env("INMET_START_DATE", "2021-01-01"))
    station_codes: list[str] = field(default_factory=lambda: [
        c.strip() for c in _get_env("INMET_STATION_CODES", "A307").split(",") if c.strip()
    ])


@dataclass
class IbgeConfig:
    """Configurações específicas da extração de dados do IBGE."""
    uf: str = field(default_factory=lambda: _get_env("IBGE_UF", "PE"))
    localidades_base_url: str = field(default_factory=lambda: _get_env(
        "IBGE_LOCALIDADES_BASE_URL", "https://servicodados.ibge.gov.br/api/v1/localidades"))
    sidra_base_url: str = field(default_factory=lambda: _get_env(
        "IBGE_SIDRA_BASE_URL", "https://apisidra.ibge.gov.br/values"))


@dataclass
class RecifeConfig:
    """
    Configuração para a futura integração com a API da Prefeitura do Recife.
    Hoje os campos podem vir vazios - isso é intencional. A ideia é que,
    quando essa API for liberada/definida, baste preencher o .env, sem
    precisar alterar a estrutura do projeto.
    """
    base_url: str = field(default_factory=lambda: _get_env("RECIFE_API_BASE_URL", ""))
    token: str = field(default_factory=lambda: _get_env("RECIFE_API_TOKEN", ""))


@dataclass
class SchedulerConfig:
    daily_job_time: str = field(default_factory=lambda: _get_env("DAILY_JOB_TIME", "03:00"))


@dataclass
class AppConfig:
    """Ponto único de acesso: `from src.config import config` e pronto."""
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    inmet: InmetConfig = field(default_factory=InmetConfig)
    ibge: IbgeConfig = field(default_factory=IbgeConfig)
    recife: RecifeConfig = field(default_factory=RecifeConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))


# Instância única (singleton simples) importada pelo resto do projeto.
config = AppConfig()
