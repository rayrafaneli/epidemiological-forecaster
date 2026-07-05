-- =============================================================================
-- sql/ddl.sql
-- Script de criação das tabelas do banco "dengue_db"
--
-- DECISÕES DE MODELAGEM (explicadas para quem está aprendendo):
--
-- 1) Por que tabelas separadas para município, estação e clima diário, em vez
--    de uma tabela só "achatada"?
--    Isso é normalização: evita repetir "Recife, PE, 1.653.461 habitantes"
--    em milhares de linhas de clima. Guardamos essa informação uma vez em
--    "municipios" e apenas referenciamos o código (chave estrangeira) nas
--    demais tabelas. Economiza espaço e evita inconsistência (ex: se a
--    população mudar, atualizamos em um único lugar).
--
-- 2) Por que existem restrições UNIQUE em (estacao, data) e (municipio, data)?
--    É exatamente o mecanismo que usaremos na camada "load" para evitar
--    duplicidade: ao inserir, usamos "ON CONFLICT DO NOTHING/UPDATE" sobre
--    essa constraint. Se o job diário rodar de novo sobre um dia que já
--    existe, o banco simplesmente ignora ou atualiza, em vez de duplicar.
--
-- 3) Por que a tabela "casos_dengue" já existe, se a API da Prefeitura do
--    Recife ainda não foi integrada?
--    Para deixar o schema pronto (requisito do enunciado: "preparar o
--    projeto para futuramente integrar dados da Prefeitura do Recife").
--    Assim, quando a Sprint 2 chegar, só será necessário implementar o
--    extrator/transformador - a tabela já existe e já se relaciona com
--    "municipios" e "clima_diario" para os cruzamentos estatísticos.
--
-- 4) Por que existe "etl_execution_log"?
--    Para auditoria: cada execução do pipeline (manual ou agendada) grava
--    quando rodou, quantos registros inseriu e se deu certo ou não. Isso é
--    essencial para um TCC, pois permite comprovar e demonstrar o
--    funcionamento da rotina automática.
-- =============================================================================

-- Criação do schema opcional (organiza objetos do projeto separados de
-- outros bancos que possam existir na mesma instância PostgreSQL).
CREATE SCHEMA IF NOT EXISTS dengue;
SET search_path TO dengue, public;

-- -----------------------------------------------------------------------------
-- Tabela: municipios
-- Fonte: IBGE (localidades + população + área territorial)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS municipios (
    codigo_ibge         BIGINT PRIMARY KEY,          -- código único de 7 dígitos do IBGE
    nome                 VARCHAR(150) NOT NULL,
    uf                   CHAR(2) NOT NULL,
    regiao               VARCHAR(20),
    populacao_estimada   INTEGER,                     -- último ano disponível na API do IBGE
    area_km2             NUMERIC(12, 3),
    densidade_demografica NUMERIC(12, 3),              -- calculada = populacao / area_km2
    latitude             NUMERIC(9, 6),
    longitude            NUMERIC(9, 6),
    ano_referencia_populacao SMALLINT,                 -- de qual ano é a estimativa populacional
    atualizado_em        TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE municipios IS 'Dados cadastrais e demográficos dos municípios (fonte: IBGE), usados para cruzamento com casos de dengue.';

-- -----------------------------------------------------------------------------
-- Tabela: estacoes_inmet
-- Fonte: IBGE-INMET (metadados das estações meteorológicas automáticas)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estacoes_inmet (
    codigo_estacao       VARCHAR(10) PRIMARY KEY,     -- ex: 'A307'
    nome                 VARCHAR(150),
    uf                   CHAR(2),
    municipio_codigo_ibge BIGINT REFERENCES municipios(codigo_ibge),
    latitude              NUMERIC(9, 6),
    longitude             NUMERIC(9, 6),
    altitude_m            NUMERIC(9, 2),
    situacao              VARCHAR(20),                -- 'Operante' / 'Pane', etc.
    data_inicio_operacao  DATE,
    atualizado_em         TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE estacoes_inmet IS 'Metadados das estações meteorológicas automáticas do INMET.';

-- -----------------------------------------------------------------------------
-- Tabela: clima_diario
-- Fonte: INMET (histórico diário por estação, desde 2021)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clima_diario (
    id                       BIGSERIAL PRIMARY KEY,
    codigo_estacao          VARCHAR(10) NOT NULL REFERENCES estacoes_inmet(codigo_estacao),
    data_medicao             DATE NOT NULL,
    temp_max_c               NUMERIC(5, 2),
    temp_min_c               NUMERIC(5, 2),
    temp_media_c              NUMERIC(5, 2),
    precipitacao_total_mm    NUMERIC(7, 2),
    umidade_relativa_media_pct NUMERIC(5, 2),
    velocidade_vento_media_ms NUMERIC(5, 2),
    pressao_atm_media_mb      NUMERIC(7, 2),
    fonte                     VARCHAR(30) NOT NULL DEFAULT 'INMET',
    criado_em                 TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Esta constraint é a peça-chave anti-duplicidade: nunca pode existir
    -- mais de um registro para a mesma estação no mesmo dia.
    CONSTRAINT uq_clima_estacao_data UNIQUE (codigo_estacao, data_medicao)
);

COMMENT ON TABLE clima_diario IS 'Série histórica diária de variáveis meteorológicas por estação do INMET (a partir de 2021).';

CREATE INDEX IF NOT EXISTS ix_clima_diario_data ON clima_diario (data_medicao);

-- -----------------------------------------------------------------------------
-- Tabela: casos_dengue  (scaffold para a Sprint futura - API da Prefeitura do Recife)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS casos_dengue (
    id                     BIGSERIAL PRIMARY KEY,
    municipio_codigo_ibge  BIGINT NOT NULL REFERENCES municipios(codigo_ibge),
    data_notificacao       DATE NOT NULL,
    faixa_etaria           VARCHAR(30),
    sexo                   CHAR(1),
    classificacao          VARCHAR(50),                -- ex: suspeito, confirmado, descartado
    evolucao                VARCHAR(30),                -- ex: cura, óbito, em acompanhamento
    bairro                  VARCHAR(100),
    id_externo_origem       VARCHAR(100),               -- id do registro na API de origem, se existir
    fonte                   VARCHAR(30) NOT NULL DEFAULT 'PREFEITURA_RECIFE',
    criado_em                TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Evita reimportar o mesmo caso vindo da mesma fonte/id externo.
    CONSTRAINT uq_casos_fonte_id_externo UNIQUE (fonte, id_externo_origem)
);

COMMENT ON TABLE casos_dengue IS 'Casos de dengue notificados (fonte futura: API da Prefeitura do Recife). Tabela preparada com antecedência para a próxima sprint.';

CREATE INDEX IF NOT EXISTS ix_casos_dengue_data ON casos_dengue (data_notificacao);
CREATE INDEX IF NOT EXISTS ix_casos_dengue_municipio ON casos_dengue (municipio_codigo_ibge);

-- -----------------------------------------------------------------------------
-- Tabela: etl_execution_log
-- Auditoria de cada execução do pipeline (manual ou automática)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_execution_log (
    id                    BIGSERIAL PRIMARY KEY,
    pipeline_name         VARCHAR(50) NOT NULL,   -- ex: 'inmet', 'ibge'
    iniciado_em            TIMESTAMP NOT NULL,
    finalizado_em           TIMESTAMP,
    status                 VARCHAR(20) NOT NULL,   -- 'SUCESSO' | 'FALHA' | 'EM_EXECUCAO'
    registros_extraidos     INTEGER DEFAULT 0,
    registros_inseridos      INTEGER DEFAULT 0,
    registros_ignorados_duplicados INTEGER DEFAULT 0,
    mensagem_erro           TEXT
);

COMMENT ON TABLE etl_execution_log IS 'Auditoria de execuções do pipeline ETL, usada para comprovar o funcionamento da rotina automática diária.';
