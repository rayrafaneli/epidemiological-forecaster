# Pipeline ETL — Clima (INMET) e Municípios (IBGE) para predição de superlotação hospitalar por dengue

**Sprint 1** do TCC: construção do pipeline ETL em Python e estruturação do banco PostgreSQL que servirão de base para o cruzamento entre variáveis climáticas, demográficas e (futuramente) casos de dengue notificados pela Prefeitura do Recife.

---

## 1. Visão geral da arquitetura

O projeto segue uma **arquitetura em camadas**, onde cada camada tem uma única responsabilidade e só conhece a camada imediatamente abaixo dela:

```
main.py  (orquestrador)
   │
   ├── src/extract/     -> SÓ busca dados brutos nas APIs (INMET, IBGE, Recife*)
   ├── src/transform/   -> SÓ limpa, padroniza e valida (não conhece API nem banco)
   ├── src/load/        -> SÓ insere no PostgreSQL (não sabe de onde os dados vieram)
   ├── src/scheduler/   -> SÓ decide QUANDO rodar o pipeline (chama main.run_all)
   └── src/database/    -> conexão e criação de schema, usada pela camada load
```

*(Recife = integração planejada para uma sprint futura, já com o "contrato" do código pronto.)*

### Por que essa separação (Extract / Transform / Load) importa?

Se amanhã o INMET mudar o nome de um campo na API, só `src/transform/inmet_transformer.py`
precisa ser tocado. Se decidirmos trocar PostgreSQL por outro banco, só
`src/load` e `src/database` mudam. Isso é o princípio de **responsabilidade
única**: cada arquivo tem um, e só um, motivo para mudar.

### Estrutura de pastas

```
dengue-etl/
├── main.py                        # orquestrador (ponto de entrada)
├── requirements.txt
├── .env.example                   # modelo de variáveis de ambiente
├── .gitignore
├── sql/
│   └── ddl.sql                    # criação de todas as tabelas (DDL)
├── src/
│   ├── config.py                  # leitura centralizada do .env
│   ├── logger.py                  # logging padronizado (console + arquivo)
│   ├── extract/
│   │   ├── base_extractor.py      # HTTP com retry/timeout, herdado pelos demais
│   │   ├── inmet_extractor.py     # estações + clima diário do INMET
│   │   ├── ibge_extractor.py      # municípios + população + área do IBGE
│   │   └── recife_extractor.py    # scaffold da integração futura
│   ├── transform/
│   │   ├── inmet_transformer.py   # limpeza/validação dos dados do INMET
│   │   └── ibge_transformer.py    # junção e cálculo de densidade demográfica
│   ├── load/
│   │   ├── postgres_loader.py     # upsert genérico (INSERT ... ON CONFLICT)
│   │   └── etl_log.py             # auditoria de cada execução
│   ├── scheduler/
│   │   └── daily_job.py           # rotina diária automática
│   └── database/
│       ├── connection.py          # engine SQLAlchemy + sessão
│       └── schema_setup.py        # aplica o sql/ddl.sql via Python
├── tests/
│   └── test_inmet_transformer.py  # testes unitários da camada transform
└── logs/                          # gerado em tempo de execução (etl.log)
```

---

## 2. Modelo de dados (PostgreSQL)

Veja `sql/ddl.sql` para o script completo e comentado. Resumo das tabelas:

| Tabela                | Fonte                          | Papel                                                             |
|------------------------|---------------------------------|--------------------------------------------------------------------|
| `municipios`            | IBGE                            | Dimensão: nome, UF, população, área, densidade demográfica         |
| `estacoes_inmet`         | INMET                           | Metadados das estações meteorológicas automáticas                  |
| `clima_diario`           | INMET                           | Fato: série histórica diária por estação, desde 2021               |
| `casos_dengue`           | Prefeitura do Recife *(futuro)* | Fato: casos notificados — schema já pronto para a próxima sprint  |
| `etl_execution_log`      | Interna                        | Auditoria de cada execução do pipeline (manual ou agendada)        |

**Como a duplicidade é evitada?** Cada tabela de fato tem uma `UNIQUE
CONSTRAINT` (ex.: `clima_diario` é única por `codigo_estacao + data_medicao`).
A camada `load` usa `INSERT ... ON CONFLICT (...) DO NOTHING` (ou `DO
UPDATE` quando o dado pode ser corrigido, como população). Rodar o
pipeline várias vezes sobre o mesmo período **nunca duplica linhas**.

---

## 3. Pré-requisitos

- Python 3.11+
- PostgreSQL 14+ instalado e rodando (local ou em container)
- Git

---

## 4. Passo a passo de execução

### 4.1. Clonar o repositório e criar a branch de trabalho

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd dengue-etl
git checkout -b feature/extracao-inmet
```

### 4.2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 4.3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4.4. Configurar as variáveis de ambiente

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Abra o `.env` e preencha `DB_USER`, `DB_PASSWORD`, `DB_NAME` com os dados
do seu PostgreSQL local.

### 4.5. Criar o banco de dados PostgreSQL

Se o banco ainda não existir:

```bash
# Linux/Mac (usuário postgres)
sudo -u postgres createdb dengue_db

# ou via psql
psql -U postgres -c "CREATE DATABASE dengue_db;"
```

### 4.6. Criar as tabelas (executar o DDL)

Você pode usar o `psql` diretamente:

```bash
psql -U postgres -d dengue_db -f sql/ddl.sql
```

Ou deixar o próprio Python fazer isso (mais prático no Windows):

```bash
python main.py --setup-db --pipeline ibge
```

*(a flag `--setup-db` roda o DDL antes do pipeline escolhido)*

### 4.7. Testar a conexão com o banco isoladamente (opcional)

```bash
python -m src.database.connection
```

### 4.8. Rodar o pipeline manualmente

```bash
# Roda IBGE (municípios) e depois INMET (clima) uma única vez
python main.py --pipeline all

# Ou separadamente:
python main.py --pipeline ibge
python main.py --pipeline inmet
```

Acompanhe a execução em tempo real no console ou depois em `logs/etl.log`.

### 4.9. Rodar os testes automatizados

```bash
pip install pytest
pytest tests/ -v
```

### 4.10. Ativar a rotina diária automática

```bash
python main.py --schedule
```

Isso inicia um processo Python que fica em execução contínua e dispara o
pipeline todos os dias no horário definido por `DAILY_JOB_TIME` no `.env`
(padrão: `03:00`). Para produção, recomenda-se rodar este comando sob um
supervisor de processos (systemd, Docker com `restart: always`, etc.), para
que ele seja reiniciado automaticamente caso o servidor reinicie.

---

## 5. Fluxo de trabalho Git recomendado para esta Sprint

```bash
# 1. Criar a branch de feature (já feito no passo 4.1, repetido aqui por clareza)
git checkout -b feature/extracao-inmet

# 2. Ir commitando por etapa lógica, não tudo de uma vez
git add sql/ddl.sql
git commit -m "feat(db): cria schema e tabelas do banco (municipios, clima_diario, casos_dengue)"

git add src/extract/
git commit -m "feat(extract): implementa extratores INMET e IBGE"

git add src/transform/
git commit -m "feat(transform): implementa limpeza e validação dos dados INMET e IBGE"

git add src/load/
git commit -m "feat(load): implementa upsert idempotente no PostgreSQL"

git add src/scheduler/ main.py
git commit -m "feat(scheduler): adiciona orquestrador e rotina diária automática"

git add tests/
git commit -m "test: adiciona testes unitários da camada transform"

# 3. Subir a branch para o repositório remoto
git push -u origin feature/extracao-inmet

# 4. Abrir o Pull Request (via GitHub CLI, se instalado)
gh pr create \
  --base main \
  --head feature/extracao-inmet \
  --title "Sprint 1: Pipeline ETL (INMET + IBGE) e estruturação do PostgreSQL" \
  --body "Implementa o pipeline ETL completo (extract/transform/load), o schema PostgreSQL (DDL), a rotina diária automática com prevenção de duplicidade, e prepara a arquitetura para a futura integração com a API da Prefeitura do Recife."

# Caso não tenha o GitHub CLI instalado, basta abrir o Pull Request pela
# interface web do GitHub/GitLab, comparando a branch "feature/extracao-inmet"
# com a branch principal (main/master).
```

---

## 6. Decisões de arquitetura — resumo para a defesa do TCC

| Decisão | Justificativa |
|---|---|
| Arquitetura em camadas (extract/transform/load/scheduler) | Isola responsabilidades; facilita manutenção e testes |
| `BaseExtractor` com retry/backoff | APIs públicas oscilam; evita que uma instabilidade momentânea derrube o pipeline inteiro |
| Upsert com `ON CONFLICT` em vez de `INSERT` simples | Atende diretamente ao requisito de "inserir apenas novos registros, evitando duplicidades" |
| `UNIQUE CONSTRAINT` no banco, não só validação em Python | A garantia de não-duplicidade fica no banco (mais forte), não depende de nenhuma aplicação se lembrar de checar |
| Tabela `etl_execution_log` | Evidência auditável de que a rotina automática funciona — importante para a defesa |
| `casos_dengue` e `recife_extractor.py` já criados (vazios/scaffold) | Atende ao requisito de já preparar a próxima integração sem redesenhar o schema depois |
| Variáveis sensíveis em `.env` (nunca no código) | Segurança e portabilidade entre ambientes (dev/produção) |
| Testes unitários só na camada `transform` | Extract/Load dependem de rede e banco (testes de integração); Transform é lógica pura e testável isoladamente |

---

## 7. Próximas sprints (fora do escopo desta entrega)

- Implementar `RecifeExtractor.extract()` de verdade, assim que a API da
  Prefeitura do Recife for definida/documentada.
- Criar `src/transform/recife_transformer.py` e carregar `casos_dengue`.
- Camada de análise/predição (modelo estatístico ou de machine learning)
  cruzando `clima_diario`, `municipios` e `casos_dengue`.
- Dashboard/API de visualização dos indicadores de risco de superlotação.
