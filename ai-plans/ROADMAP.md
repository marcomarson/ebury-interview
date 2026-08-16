# Roadmap

The build is split into sequential plans. **Each plan is drafted, reviewed, and approved
before its implementation begins** (per [`AGENTS.md`](../AGENTS.md)). Detailed plans are
written just-in-time so they reflect what the previous step actually produced.

| # | Plan | File | Status |
|---|------|------|--------|
| 01 | Infra & walking skeleton (Postgres + Airflow + dbt via docker-compose) | [01-infra-scaffold.md](01-infra-scaffold.md) | ✅ Done — built & verified |
| 02 | Raw ingestion — land `customer_transactions.csv` into Postgres `raw` | [02-raw-ingestion.md](02-raw-ingestion.md) | ✅ Done — built & verified |
| 03 | Data profiling & DQ rule definition | _tbd_ | Not started |
| 04 | dbt transform & star schema (staging → dims/fact → aggregates) via Cosmos | _tbd_ | Not started |
| 05 | Data quality, observability & exception handling | _tbd_ | Not started |
| 06 | End-to-end verification (clean-room deploy, reconciliation, idempotency) | _tbd_ | Not started |
| 07 | Trade-offs & enhancements writeup — **consolidates all [ADRs](../docs/adr/README.md) into one architecture-and-decisions narrative** | _tbd_ | Not started |
| 08 | README & submission polish | _tbd_ | Not started |

## Key decisions (locked)

- **Orchestration of dbt:** Astronomer **Cosmos** (per-model Airflow tasks) as primary,
  with **BashOperator + isolated dbt venv** as a tested fallback. Rationale: decouple
  dbt's runtime from Airflow's, gain per-model observability, stay on the community
  standard. Full trade-off record: [ADR 0001](../docs/adr/0001-dbt-orchestration.md).
  See plan 04.
  - _Deliberately **not** built:_ DockerOperator, KubernetesPodOperator, and dbt Cloud.
    These are kept as **"how this scales to prod" talking points** for the call, not part
    of the deliverable — the Cosmos + isolated-venv design is a drop-in on-ramp to them
    (a change of execution mode, not a re-architecture). Expanded in plan 07.
- **Configuration & secrets:** inline `${VAR:-default}` defaults in `docker-compose.yml`
  for zero-setup local runs (no `.env` required); production would use `.env` / a cloud
  secrets manager. Full record: [ADR 0002](../docs/adr/0002-configuration-and-secrets.md).
- **Bad records:** coerce/repair what's safe; route unrecoverable rows to a **quarantine**
  table with a reason, keep the clean set flowing. See plans 03–05.
- **Dimensional model:** pragmatic star — `dim_product` + `dim_date` + `fact_transactions`
  + aggregate marts (also mapped to the brief's `dim_table`/`fact_table` wording). See plan 04.
