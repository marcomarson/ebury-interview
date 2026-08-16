# Ebury — Data Engineering Case Study

A containerized data pipeline that ingests `customer_transactions.csv` into PostgreSQL,
transforms it with **dbt** into a dimensional model with data-quality checks, and
orchestrates the flow with **Airflow** — all runnable via `docker compose up`.

> Take-home for the Senior Data Engineer (Platform) role. **Status: Plans 01–02 complete** —
> infrastructure walking skeleton + raw ingestion are built and verified (see
> [Roadmap](ai-plans/ROADMAP.md)). Modelling and data quality land in the following plans.

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

Unpause and run the skeleton DAG from the UI, or from the CLI:

```bash
docker compose exec airflow-scheduler airflow dags unpause skeleton_healthcheck
docker compose exec airflow-scheduler airflow dags trigger skeleton_healthcheck
```

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

# 2. DAG-integrity unit tests (expect: "2 passed")
docker compose run --rm --entrypoint bash airflow-scheduler -lc "cd /opt/airflow && pytest tests -q"

# 3. Warehouse schemas exist (expect: raw, analytics)
docker compose exec warehouse psql -U ebury -d ebury -c "\dn"
```

### Run raw ingestion

Trigger the ingestion DAG, then confirm 100 rows landed in `raw` (dirty values preserved
as text — cleaning happens in dbt later):

```bash
docker compose exec airflow-scheduler airflow dags trigger customer_transactions_ingestion
docker compose exec warehouse psql -U ebury -d ebury -c "SELECT count(*) FROM raw.customer_transactions;"
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

Design decisions are recorded as [ADRs](docs/adr/README.md); each change is planned in
[`ai-plans/`](ai-plans/) before implementation (see [AGENTS.md](AGENTS.md)).

## Repository layout

```
ai-plans/            # design plans (one per change) + template + roadmap
dags/                # Airflow DAGs
data/                # source dataset (customer_transactions.csv)
dbt/ebury/           # dbt project (profiles, models, tests)
db/init/             # warehouse bootstrap SQL (schemas)
docker/airflow/      # custom Airflow image (Cosmos + isolated dbt venv)
docs/adr/            # architecture decision records
include/             # reusable pipeline code (ingestion package, SQL)
tests/               # unit + integration tests
docker-compose.yml   # the full local stack
```
