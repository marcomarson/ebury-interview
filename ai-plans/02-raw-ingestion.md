# 02 — Raw Ingestion

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-16 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Done — built & verified 2026-08-16 |

## Summary

Land `customer_transactions.csv` into the warehouse `raw` schema via an Airflow DAG,
**as-is and text-tolerant**, so none of the deliberately-dirty values are lost before dbt
cleans them (plans 03–04). Loading is done with a streaming Postgres `COPY` (not row-by-row
inserts) so it stays memory-flat and fast regardless of file size, and the load is
**idempotent** (re-running yields the same result, no duplicates).

## Scope & Boundaries

**In Scope:**
- Make the dataset available to the pipeline: `data/customer_transactions.csv`, mounted
  read-only into the containers at `/opt/airflow/data`.
- A warehouse **Airflow Connection** injected via `AIRFLOW_CONN_WAREHOUSE` env (no manual
  UI step) so `PostgresHook` works out of the box; ensure the Postgres provider is in the image.
- Idempotent DDL for `raw.customer_transactions`: **every source column as `TEXT`**, plus
  ingestion metadata columns (`_ingested_at`, `_source_file`).
- Efficient load: `PostgresHook.copy_expert` streaming `COPY ... FROM STDIN (FORMAT csv,
  HEADER true)`; wrapped in `TRUNCATE + COPY` in a single transaction (idempotent).
- Reusable ingestion code in an `include/` package (kept out of the DAG file per Airflow
  best practice), imported by the DAG and by tests.
- An ingestion DAG: `acquire_source` → `create_raw_table` → `load_raw` → `reconcile_rowcount`.
- `default_args` with `retries` / `retry_delay`; an `on_failure_callback` stub (full
  alerting/observability lands in plan 05).
- Unit tests (pure helpers) + an integration test that loads a fixture into a throwaway
  table and asserts counts and that a dirty value lands verbatim.

**Out of Scope:**
- Any cleaning, type-casting, date/id standardization → **plan 04** (dbt).
- Quarantine of bad records → **plans 03/05**.
- Cosmos / dbt task group in the DAG → **plan 04**.
- Full observability, alerting channels, run metadata surfacing → **plan 05**.
- Incremental / CDC loading (this is a full-snapshot load) → noted as a future step.

**Assumptions:**
- The provided CSV is a single full-snapshot extract (100 data rows). In prod the
  `acquire_source` step would fetch from object storage/an API instead of a mounted file.
- The `raw` schema already exists (plan 01); DDL still uses `IF NOT EXISTS` to be self-standing.

## Implementation Details

### Steps

1. Copy the dataset to `data/customer_transactions.csv`; add a read-only mount
   `./data:/opt/airflow/data:ro` to the airflow services in `docker-compose.yml`.
2. Add `AIRFLOW_CONN_WAREHOUSE=postgresql://<user>:<pass>@warehouse:5432/<db>` to the
   airflow env (built from the existing `${WAREHOUSE_*}` vars); confirm
   `apache-airflow-providers-postgres` is installed in the image (add to the pinned
   install if missing).
3. Create `include/` (added to `PYTHONPATH` and baked into the image per ADR 0004):
   - `include/sql/create_raw_customer_transactions.sql` — idempotent all-`TEXT` DDL + metadata.
   - `include/ingestion/load_raw.py` — helpers: `expected_columns()`, `count_data_rows(path)`,
     `load_csv(hook, path, table)` using `copy_expert`, `reconcile(hook, path, table)`.
4. Write the ingestion DAG (`dags/customer_transactions_ingestion.py`) wiring the four
   tasks with `default_args` (retries=2, retry_delay=5m) and an `on_failure_callback` stub.
5. Bake `include/` into the image (`COPY include/ ...`) and set `PYTHONPATH`.
6. Write tests (see below) and a `make ingest` / documented `docker compose` command.
7. Retire the plan-01 `skeleton_healthcheck` DAG once the real pipeline DAG is in place
   (or keep it as a pure smoke test — decide at review; default: keep until plan 04).

### Expected Outcomes

- Triggering the DAG loads **exactly 100 rows** into `raw.customer_transactions`.
- Every column is `TEXT`; dirty values are preserved **verbatim** (e.g. `Two Hundred`,
  `T1010`, `P100`, `18-07-2023`, empty strings/NULLs all land untouched).
- `_ingested_at` and `_source_file` are populated for lineage.
- Re-running the DAG keeps the count at 100 (idempotent — truncate+load), no duplicates.
- Memory stays flat during load (streaming COPY, not a DataFrame / row inserts).

### Verification Methods

- **Automated:** `pytest` (unit + integration) inside the Airflow image; DAG-import test
  extended to the new DAG.
- **Manual:** trigger the DAG; then
  - `SELECT count(*) FROM raw.customer_transactions;` → 100
  - `SELECT price FROM raw.customer_transactions WHERE price !~ '^[0-9.]+$';` → shows
    `Two Hundred` etc. landed as text
  - `\d raw.customer_transactions` → all columns `text` + metadata columns
- **Data checks:** row-count reconciliation (file data-lines == rows loaded); spot-check a
  known dirty value is present unchanged.

### Unit Tests

Tests to be written. **Include edge cases explicitly.**

| Test | What it verifies | Type |
|------|------------------|------|
| `test_count_data_rows` | line counter returns 100 for the dataset (excludes header) | happy path |
| `test_load_happy_path` | fixture load inserts N rows into a throwaway table | happy path |
| `test_dirty_values_land_verbatim` | `Two Hundred`, `T1010`, `P100`, `18-07-2023` stored unchanged as text | edge case |
| `test_nulls_and_empties_preserved` | empty `customer_id` / `quantity` land as NULL/empty, not dropped | edge case |
| `test_header_only_file` | a header-only CSV loads 0 rows and reconciliation passes (0==0) | edge case |
| `test_idempotent_reload` | loading twice yields the same row count (truncate+load), no dupes | edge case |
| `test_missing_file_fails_loudly` | absent source file raises a clear error (task fails, not silently) | failure case |
| `test_column_mismatch_detected` | a CSV whose header ≠ expected columns is rejected with a clear error | failure case |
| `test_reconcile_mismatch_flags` | reconciliation raises when loaded rows ≠ file data rows | failure case |
| `test_dag_imports` | the ingestion DAG parses with no import errors and has the 4 expected tasks | happy path |

Edge cases to cover: header-only file, embedded quotes/commas in a field, trailing newline,
NULL vs empty-string, duplicate `transaction_id`, re-run idempotency.

## Risks & Considerations

- **Choosing TEXT over typed columns** is deliberate (ELT): typing at load would reject
  dirty rows prematurely and lose data the case wants us to *handle*, not drop. dbt owns
  casting/validation downstream.
- **`COPY` vs pandas `to_sql`:** COPY is chosen for memory/performance (the brief's explicit
  ask). `to_sql` would load the file into a DataFrame — fine for 100 rows, wrong at scale.
- **Load strategy:** truncate+load gives idempotency for a single snapshot file. The
  trade-off (no history) is acceptable here; an append + `batch_id`/`_ingested_at` model is
  the path for incremental/auditable loads — documented as a future step.
- **Data not baked into the image:** the dataset is *input*, not code, so it's mounted, not
  `COPY`'d. In prod `acquire_source` fetches from object storage; the mount simulates that.
- **Secrets:** the warehouse connection URI uses the same local-default creds (ADR 0002);
  prod sources it from a secrets backend / Airflow secrets backend.
- **Rollback:** ingestion only writes to `raw.customer_transactions`; `TRUNCATE` or
  `docker compose down -v` fully resets it.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-16 | Initial version |
| 2026-08-16 | Approved: dataset in tracked `data/` mounted read-only; keep `skeleton_healthcheck` DAG until plan 04. |
| 2026-08-16 | **Implemented & verified.** Added `AIRFLOW_CONN_WAREHOUSE`, `apache-airflow-providers-postgres`, `include/` package (baked + mounted, on `PYTHONPATH`), ingestion DAG, and tests. Results: DAG run = success; `raw.customer_transactions` = 100 rows, all-`text` + metadata; dirty values (`T1010`, `Two Hundred`, `P100`, NULL `customer_id`) landed verbatim; **11/11 tests pass** (5 unit + 4 integration + 2 DAG-import). |
