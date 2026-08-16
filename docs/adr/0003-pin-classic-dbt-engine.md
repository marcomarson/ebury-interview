# ADR 0003 — Pin the classic dbt engine (not dbt Fusion 2.0)

- **Status:** Accepted
- **Date:** 2026-08-16
- **Deciders:** Marco Marson (with Claude)
- **Context tags:** dbt, dependencies, reproducibility

## Context

While building the Plan 01 image, installing `dbt-postgres==1.8.2` silently resolved its
`dbt-core` dependency to the **pre-release `dbt-core==2.0.0b1`** — the new **"dbt Fusion"**
(Rust) engine. `dbt debug` then failed:

> The 'postgres' adapter is not yet supported by dbt Fusion. Supported adapters:
> snowflake, bigquery, databricks, redshift, duckdb, salesforce, clickhouse.

Our entire stack is Postgres-based, so Fusion is a non-starter today. The classic
(Python) dbt engine remains fully maintained (stable `dbt-core` up to 1.12.2,
`dbt-postgres` up to 1.11.0) and supports Postgres.

## Decision

**Pin `dbt-core` explicitly to a stable classic release** in the image so the resolver
can never substitute the Fusion pre-release:

```dockerfile
"${DBT_VENV}/bin/pip" install "dbt-core==1.9.11" "dbt-postgres==1.9.1"
```

Note: a range like `dbt-core<2.0` is **not** sufficient — by PEP 440, `2.0.0b1 < 2.0.0`,
so the beta would still satisfy `<2.0`. An explicit stable pin is required.

## Consequences

**Positive**
- Reproducible, Postgres-supporting dbt builds; `dbt debug` passes.
- Deterministic image — no surprise pre-release pulls on rebuild.

**Negative / risks**
- We're on classic dbt, not the newer Fusion engine (faster, Rust-based). Acceptable:
  Fusion doesn't support Postgres yet, and classic dbt is stable and fully featured.
- The pin must be revisited when Fusion gains a stable Postgres adapter, or if we move
  the warehouse to a Fusion-supported platform (Snowflake/BigQuery/Redshift/DuckDB).

## Follow-ups

- Revisit in the plan 07 trade-offs writeup as a "future migration" note (Fusion + a
  cloud warehouse) alongside the orchestration scaling path.
