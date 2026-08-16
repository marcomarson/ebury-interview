# 01 — Infra & Walking Skeleton

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-16 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Draft — awaiting approval |

## Summary

Stand up the containerized foundation — **PostgreSQL + Airflow + dbt** — via
`docker-compose`, producing a healthy **walking skeleton**: all services start, connect,
and a trivial end-to-end DAG runs green **before any real data or business logic exists**.
The goal of this step is a boring, reliable base that `docker-compose up` brings to life,
so every later step builds on proven infrastructure.

## Scope & Boundaries

**In Scope:**
- `docker-compose.yml` orchestrating: `postgres`, `airflow-init`, `airflow-webserver`,
  `airflow-scheduler` (Airflow **LocalExecutor** — simpler than Celery, sufficient here).
- Pinned versions (e.g. Airflow 2.9.x, dbt-core + dbt-postgres 1.7/1.8, Postgres 16,
  astronomer-cosmos) recorded in a `requirements`/Dockerfile.
- **dbt runtime isolation**: dbt installed in a dedicated virtualenv inside a custom
  Airflow image (or a separate dbt build stage) so dbt's deps never collide with
  Airflow's core deps.
- Postgres bootstrap: an init script creating schemas (`raw`, `analytics`) and a
  dedicated application role.
- Minimal dbt project scaffold (`dbt_project.yml`, `profiles.yml` templated from env
  vars pointing at the `postgres` service) such that `dbt debug` passes.
- A **placeholder Airflow DAG** that imports Cosmos cleanly and runs one `EmptyOperator`
  (or a `dbt debug` smoke task) to prove the wiring.
- **Configuration via `${VAR:-default}` defaults inlined in `docker-compose.yml`** so the
  stack runs with **zero setup** (no `.env` required). A small committed `.env.example`
  documents overridable values (ports/creds); the real `.env` stays gitignored. Local
  throwaway defaults only — production would use `.env` / a cloud secrets manager
  (see [ADR 0002](../docs/adr/0002-configuration-and-secrets.md)).
- Healthchecks + `depends_on` conditions so services start in the right order.
- A `Makefile` (or documented commands) for `up` / `down` / `logs` / `test`.

**Out of Scope:**
- Loading the real `customer_transactions.csv` → **plan 02**.
- Any real dbt staging/dim/fact models or aggregates → **plan 04**.
- The DQ framework, quarantine, tests, alerting → **plans 03 / 05**.
- The full Cosmos-rendered dbt task group (only a stub/smoke task here) → **plan 04**.

**Assumptions:**
- Reviewer has Docker Desktop; ports 5432/8080 are free (overridable via `.env`).
- Dataset already present at `ebury-docs/customer_transactions.csv`.

## Implementation Details

### Steps

1. Pin the stack: choose and record exact image/package versions; confirm Cosmos ↔ Airflow
   compatibility.
2. Write a custom Airflow `Dockerfile` that installs dbt-core + dbt-postgres + cosmos into
   an **isolated virtualenv** (documenting the isolation rationale).
3. Author `docker-compose.yml`: `postgres` (named volume, healthcheck, mounts init SQL),
   `airflow-init` (db migrate + admin user), `airflow-webserver`, `airflow-scheduler`;
   mount `./dags`, `./dbt`, `./data`.
4. Postgres init SQL: create `raw` and `analytics` schemas + application role/grants.
5. Scaffold the dbt project (`dbt/`) with `profiles.yml` fed by env vars; verify
   `dbt debug` is green against the `postgres` service.
6. Add a placeholder DAG (`dags/`) importing Cosmos and running one no-op / `dbt debug`
   task to prove the DAG parses and executes.
7. Inline `${VAR:-default}` config in `docker-compose.yml`; add a documentation-only
   `.env.example`, a `Makefile`, and a quickstart snippet (README evolves in plan 08).

### Expected Outcomes

- `docker-compose up` brings **all services healthy**; Airflow UI reachable at
  `localhost:8080` (admin login works).
- `dbt debug` reports all checks **OK** against Postgres.
- The placeholder DAG appears in the UI with **zero import errors** and runs to `success`.
- Postgres contains the `raw` and `analytics` schemas and the app role.
- Bringing the stack down and up again reproduces the same healthy state.

### Verification Methods

- **Automated:**
  - `pytest` DAG-import test — `DagBag` reports **0 import errors**.
  - `make test-infra` — waits for Airflow health endpoint `/health` to be healthy and
    runs `dbt debug` (exit 0).
  - Compose `healthcheck` states report `healthy` for postgres and airflow.
- **Manual:** open Airflow UI, log in, trigger the placeholder DAG, confirm success;
  `psql` into Postgres and `\dn` shows the schemas.
- **Data checks:** none this step (no data loaded yet).

### Unit Tests

Tests to be written. **Include edge cases explicitly.**

| Test | What it verifies | Type |
|------|------------------|------|
| `test_dagbag_imports` | all DAGs import with zero errors | happy path |
| `test_placeholder_dag_structure` | placeholder DAG exists with the expected task(s) | happy path |
| `test_dbt_debug_ok` | `dbt debug` exits 0 against Postgres (smoke) | happy path |
| `test_required_env_missing` | compose/profiles fail **loudly** when a required env var is absent | failure case |
| `test_postgres_gating` | Airflow does not start tasks until Postgres healthcheck passes | edge case |

Edge cases to cover: missing/empty required env vars, port already in use, first-run vs
re-run (`airflow-init` idempotency), stack restart reproducibility.

## Risks & Considerations

- **Airflow ↔ dbt dependency conflicts** — mitigated by the isolated dbt virtualenv;
  this is the core reason we don't `pip install dbt` into Airflow's env.
- **Cosmos ↔ Airflow version mismatch** — pin and verify early.
- **Port clashes (5432 / 8080)** — made configurable via `.env`.
- **Windows/Docker Desktop volume perms & CRLF line endings** — note `.gitattributes` /
  entrypoint expectations so the reviewer isn't bitten.
- **Rollback:** this step is purely additive; `docker-compose down -v` fully resets state.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-16 | Initial version |
| 2026-08-16 | Config decision: inline `${VAR:-default}` defaults in `docker-compose.yml` (no `.env` required to run); `.env.example` becomes documentation-only. Local defaults only — production uses `.env` / cloud secrets manager. See [ADR 0002](../docs/adr/0002-configuration-and-secrets.md). |
