# Ebury — Data Engineering Case Study

A containerized data pipeline that ingests `customer_transactions.csv` into PostgreSQL,
transforms it with **dbt** into a dimensional model with data-quality checks, and
orchestrates the flow with **Airflow** — all runnable via `docker-compose up`.

> Take-home for the Senior Data Engineer (Platform) role. Work in progress.

## Stack

- **PostgreSQL** — raw and processed storage
- **dbt** — cleaning, dimensional modelling, data-quality tests
- **Airflow** — orchestration (ingest → transform → test)
- **Docker Compose** — one-command local deployment

## Approach (high level)

The source data is intentionally messy (mixed date formats, prefixed IDs, word-valued
numbers, nulls). The pipeline follows an **ELT** pattern: land the raw CSV as-is, then
clean, coerce, and validate inside dbt. Records that cannot be safely repaired are
routed to a **quarantine** table with a reason rather than silently dropped, and the
model exposes a star schema plus aggregate summaries for downstream use.

Detailed, per-change plans live in [`ai-plans/`](ai-plans/) (see [`AGENTS.md`](AGENTS.md)
for the working conventions).

## Repository layout

```
ai-plans/       # design plans (one per change) + template
ebury-docs/     # case brief and source dataset
AGENTS.md       # working rules / conventions for this repo
```

## Status

Scaffolding stage — architecture and plans being defined. Setup instructions will be
added here as the pipeline is built.
