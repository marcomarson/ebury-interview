# Ebury — Data Engineering Case Study

A containerized data pipeline that ingests `customer_transactions.csv` into PostgreSQL,
transforms it with **dbt** into a dimensional model with data-quality checks, and
orchestrates the flow with **Airflow** — all runnable via `docker compose up`.

> Take-home for the Senior Data Engineer (Platform) role. **Status: Plans 01–04 complete** —
> infra, raw ingestion, data-quality profiling, and the dbt star schema (with quarantine)
> are built and verified end-to-end (see [Roadmap](ai-plans/ROADMAP.md)). Remaining plans
> harden observability, verification, and docs.

## Stack

| Component | Role | Notes |
|-----------|------|-------|
| **PostgreSQL 16** (`warehouse`) | Raw + processed data storage | Schemas: `raw`, `analytics` |
| **PostgreSQL 16** (`airflow-meta`) | Airflow metadata DB | Kept separate from the warehouse on purpose |
| **Airflow 2.9** | Orchestration | LocalExecutor |
| **dbt** (`dbt-core 1.9`, `dbt-postgres`) | Transformations & tests | Runs in an **isolated venv**, invoked via **Cosmos** ([ADR 0001](docs/adr/0001-dbt-orchestration.md)) |
| **Docker Compose** | One-command local deploy | `docker compose up` |

## Prerequisites

Everything runs in containers, so the **only host requirement is Docker**. Specifically:

- **Docker Desktop** with the **WSL2 backend** (Windows) — or Docker Engine + Compose v2
  on Linux/macOS. Verified here with Docker **29.x** / Compose **v2**.
  - Windows: enable WSL2 (`wsl --install` if needed), then install Docker Desktop and make
    sure **Settings → General → "Use the WSL2 based engine"** is on. You do **not** need to
    install a separate Linux distro — Docker Desktop manages its own.
- **~4 GB free RAM** for the containers.
- **Ports `8080` and `5432` free** on the host (both overridable — see [Configuration](#configuration)).
- That's it — **no local Python, dbt, or Airflow install needed**. `make` is optional
  (Windows users can run the underlying `docker compose` commands directly).

## Quick start

From the repository root:

```bash
docker compose up -d --build
```

This builds the Airflow image, starts both databases, runs a one-shot init (metadata DB
migration + admin user), then launches the Airflow webserver and scheduler. First run
takes a few minutes while images build/pull; subsequent runs are fast.

Then open the Airflow UI:

- **URL:** http://localhost:8080
- **Login:** `admin` / `admin` (local defaults)

Unpause and run the full pipeline from the UI, or from the CLI:

```bash
docker compose exec airflow-scheduler airflow dags unpause customer_transactions_pipeline
docker compose exec airflow-scheduler airflow dags trigger customer_transactions_pipeline
```

This ingests the CSV into `raw`, then builds the dbt star schema and runs the tests.

Stop the stack (data is preserved in named volumes):

```bash
docker compose down
```

Full reset (also removes the databases):

```bash
docker compose down -v
```

## Verify it works

```bash
# 1. dbt connects to the warehouse (expect: "All checks passed!")
docker compose run --rm dbt debug

# 2. Unit + integration tests (expect: "11 passed")
docker compose run --rm --entrypoint bash airflow-scheduler -lc "cd /opt/airflow && pytest tests -q"

# 3. Build the whole dbt project + tests directly (expect: PASS=38 WARN=1 ERROR=0)
docker compose run --rm dbt build
```

The one WARN is intentional — the quarantine test surfaces the 29 rejected rows without
failing the run (see [Data quality](#data-quality--quarantine)).

### After running the pipeline

Trigger `customer_transactions_pipeline` (above), then inspect the results:

```bash
# raw landing (100 rows, dirty values preserved as text)
docker compose exec warehouse psql -U ebury -d ebury -c "SELECT count(*) FROM raw.customer_transactions;"

# star schema + quarantine (expect fact=71, quarantine=29, reconciles=t)
docker compose exec warehouse psql -U ebury -d ebury -c "SELECT (SELECT count(*) FROM analytics.fct_transactions) fact, (SELECT count(*) FROM analytics.quarantine_customer_transactions) quarantine, (SELECT reconciles FROM analytics.dq_completeness);"
```

If you have `make`, the same actions are wrapped as `make up`, `make dbt-debug`,
`make test`, `make down`, `make clean` — run `make help` for the full list.

## Configuration

The stack runs with **built-in defaults — no `.env` file required** (`docker-compose.yml`
uses `${VAR:-default}`). To override anything (e.g. a port clash), copy `.env.example` to
`.env` and edit. These defaults are **throwaway local values**; a real deployment would
source secrets from a manager (AWS Secrets Manager, GCP Secret Manager, Vault) — see
[ADR 0002](docs/adr/0002-configuration-and-secrets.md).

| Setting | Default | Override var |
|---------|---------|--------------|
| Airflow UI port | `8080` | `AIRFLOW_PORT` |
| Warehouse port | `5432` | `WAREHOUSE_PORT` |
| Warehouse db/user/pass | `ebury` / `ebury` / `ebury` | `WAREHOUSE_DB` / `_USER` / `_PASSWORD` |
| Airflow admin | `admin` / `admin` | `AIRFLOW_ADMIN_USER` / `_PASSWORD` |

## How it's designed

- **ELT, not ETL.** The raw CSV is landed as-is in `raw`, then cleaned/validated inside
  dbt. This keeps an immutable source of truth and makes transformations reproducible.
- **dbt is decoupled from Airflow.** dbt lives in its own virtualenv so its dependencies
  never collide with Airflow's; Cosmos renders dbt models as individual Airflow tasks for
  per-model observability. ([ADR 0001](docs/adr/0001-dbt-orchestration.md))
- **Metadata vs. warehouse are separate databases** — different lifecycles, cleaner
  separation of concerns.
- **Layered dbt with contracts.** `staging` (clean/classify) → `intermediate` → `marts`
  (star + aggregates), in separate schemas, with **enforced model contracts** on the
  dims/fact so downstream consumers get a stable, typed interface.
- **Nothing is dropped silently.** Unrecoverable rows are quarantined with reasons; a
  completeness metric reconciles received vs modelled vs quarantined.

Design decisions are recorded as [ADRs](docs/adr/README.md); each change is planned in
[`ai-plans/`](ai-plans/) before implementation (see [AGENTS.md](AGENTS.md)).

## Pipeline & data model

The `customer_transactions_pipeline` DAG runs ingestion, then dbt (rendered per-model by
Cosmos), then tests:

```
acquire_source → create_raw_table → load_raw → reconcile_rowcount
        → dbt_transform:  staging → intermediate → marts → tests
```

The dbt layers (see [ai-plans/04](ai-plans/04-dbt-transformation-star-schema.md)):

| Layer | Schema | Models |
|-------|--------|--------|
| staging | `staging` | `stg_customer_transactions` (coerce + classify) |
| intermediate | (ephemeral) | `int_transactions_valid` (clean rows, unknown-customer = -1) |
| marts (star) | `analytics` | `dim_product`, `dim_date`, `dim_customer`, `fct_transactions` |
| marts (aggregates) | `analytics` | `agg_monthly_sales`, `agg_sales_by_customer`, `agg_sales_by_product` |
| marts (DQ) | `analytics` | `quarantine_customer_transactions`, `dq_quarantine_reasons`, `dq_completeness` |

Grain of `fct_transactions` = one transaction; `total_amount = quantity × unit_price + tax`
(tax is an absolute amount — [ADR 0005](docs/adr/0005-data-quality-strategy.md)). The
brief's literal `dim_table` / `fact_table` names are provided as thin alias views.

## Data quality & quarantine

The source data is intentionally dirty. Each row is **coerced**, **quarantined**, or
**flagged** (full report + counts in [`docs/data-quality.md`](docs/data-quality.md)):

- **Coerce** recoverable formatting (strip `T`/`P` prefixes, float→int, parse both date
  formats).
- **Quarantine** rows whose amount can't be computed (non-numeric `price`/`tax`, missing
  `quantity`) into `quarantine_customer_transactions` with a `dq_reasons` array — never
  dropped. On the sample: **61 clean + 10 flagged = 71 modelled, 29 quarantined**.
- **Flag** rows that are usable but imperfect (missing `customer_id` → unknown member).
- **Observability:** a dbt test *warns* on any quarantine and *errors* only in the extreme;
  `dq_completeness` reconciles received = modelled + quarantined.

## Repository layout

```
ai-plans/            # design plans (one per change) + template + roadmap
dags/                # Airflow DAGs (customer_transactions_pipeline)
data/                # source dataset (customer_transactions.csv)
dbt/ebury/           # dbt project: models (staging/intermediate/marts), tests, macros
db/init/             # warehouse bootstrap SQL (schemas)
docker/airflow/      # custom Airflow image (Cosmos + isolated dbt venv)
docs/adr/            # architecture decision records
docs/data-quality.md # DQ profiling report + coerce/quarantine/flag rules
include/             # reusable pipeline code (ingestion package, profiling SQL)
tests/               # unit + integration tests
docker-compose.yml   # the full local stack
```
