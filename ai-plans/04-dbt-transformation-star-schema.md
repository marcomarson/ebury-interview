# 04 — dbt Transformation & Star Schema

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-17 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | In progress — decisions confirmed 2026-08-17 |

## Summary

Transform `raw.customer_transactions` into a governed dimensional model with dbt,
implementing the plan-03 ruleset: a **staging** layer that coerces and classifies, a
**clean/quarantine split**, a **star schema** (`dim_product`, `dim_date`, `dim_customer`,
`fct_transactions`), and **aggregate marts** (monthly / by customer / by product). The dbt
project is wired into Airflow via **Cosmos** (per-model tasks), replacing the plan-01
skeleton DAG. Framed for a *platform* role: layering conventions, tests, model contracts,
documentation, and lineage are first-class, not afterthoughts.

## Scope & Boundaries

**In Scope:**
- dbt layering: `staging/` → `intermediate/` → `marts/` with naming conventions
  (`stg_`, `int_`, `dim_`, `fct_`, `agg_`).
- `raw` declared as a dbt **source** (with source tests / freshness).
- `stg_customer_transactions`: coerce (strip `T`/`P`, float→int, parse both date formats,
  trim) + classify each row (`dq_reasons`, `is_valid`).
- Split: `int_transactions_valid` (clean) and `quarantine_customer_transactions`
  (rejected + `dq_reasons text[]`) + `dq_quarantine_reasons` unnest view.
- Star: `dim_product`, `dim_date`, `dim_customer` (with **unknown member**),
  `fct_transactions` (grain = transaction; measures `quantity`, `unit_price`, `subtotal`,
  `tax_amount`, `total_amount = subtotal + tax_amount`).
- Aggregates: `agg_monthly_sales`, `agg_sales_by_customer`, `agg_sales_by_product`.
- A **completeness metric** model (`dq_completeness`: received / modelled / quarantined).
- dbt **tests** (generic + singular) and the quarantine warn/error thresholds.
- **Cosmos** DbtTaskGroup wired into the pipeline DAG (`customer_transactions_pipeline`):
  ingest → dbt (staging → marts → tests). Retire `skeleton_healthcheck`.
- Model **documentation** (descriptions on models/columns) for `dbt docs`.

**Out of Scope:**
- Alerting channels / dashboards / full observability surface → **plan 05**.
- End-to-end clean-room verification & idempotency sign-off → **plan 06**.
- CI/CD (slim CI, state:modified), incremental fact → **plan 07** talking points.

## Critical platform / governance decisions (to confirm)

> These shape the build. Recommendation marked; **★ = I want to discuss before implementing.**

1. **★ Model contracts on marts.** Enforce column names/types (dbt `contract: enforced`)
   on `dim_*`/`fct_*` so downstream consumers have a stable, breaking-change-safe schema.
   *Rec: yes* — strong governance signal for a platform role.
2. **★ Schema layout.** Land `staging` models in a `staging` schema and marts in
   `analytics` (vs everything in one schema). *Rec: split* — separation of concerns,
   clearer grants/lineage.
3. **★ dbt packages.** Use `dbt_utils` (surrogate keys, extra generic tests) and possibly
   `dbt_expectations` (richer DQ tests). *Rec: dbt_utils yes* (standard, low risk);
   dbt_expectations optional.
4. **Keys.** Natural keys (`product_id`, `customer_id`, `date_key = YYYYMMDD`) with a
   `-1` unknown customer member. *Rec: natural keys* here (clean integer ids, readable);
   note surrogate-key hashing as the scale option.
5. **Materialization.** Views for staging/intermediate; **tables** for marts. Fact is
   full-refresh (100 rows). *Rec: as stated*; incremental fact = documented scale path.
6. **Literal `dim_table` / `fact_table`.** The brief names these exactly. *Rec:* build the
   proper star and add thin `dim_table`/`fact_table` **alias views** (→ `dim_product` /
   `fct_transactions`) so the deliverable maps to the brief's wording without polluting the
   model.

## Implementation Details

### Steps

1. Configure `dbt_project.yml`: layer paths, per-layer `+schema`/`+materialized`, naming.
2. `packages.yml` + `dbt deps` (if packages approved); bake into image.
3. `staging/_sources.yml` (raw source + tests) and `stg_customer_transactions.sql`
   (coerce + classify with `dq_reasons`).
4. `intermediate/`: `int_transactions_valid`, and quarantine feed.
5. `marts/`: dims (+ unknown member), `fct_transactions`, `quarantine_customer_transactions`,
   `dq_quarantine_reasons`, `dq_completeness`, and the three `agg_` models.
6. `_marts.yml`: docs + tests (+ contracts if approved) + alias views.
7. Wire **Cosmos** DbtTaskGroup into the pipeline DAG (execution against the isolated dbt
   venv); retire the skeleton DAG.
8. Tests (dbt + Python DAG-render); run end-to-end; verify counts and measures.

### Expected Outcomes

- `fct_transactions` has **61 clean + 10 flagged = 71 rows**; `quarantine_customer_transactions`
  has **29 rows** with reasons; the three partitions reconcile to 100.
- Dims populated (`dim_product` = 5, `dim_date` covers 07-10…07-20, `dim_customer` = 10 +
  unknown member). Aggregates compute correctly against the fact.
- `total_amount = quantity*unit_price + tax` across the fact.
- Cosmos renders each dbt model/test as its own Airflow task; DAG runs green end-to-end.
- `dbt test` passes; quarantine test warns (not errors) at ~29%.

### Verification Methods

- **Automated:** `dbt build` (run + test) green; `pytest` for DAG render/import; a
  reconciliation query (clean + flagged + quarantined = 100).
- **Manual:** trigger `customer_transactions_pipeline`; inspect fact/dim/quarantine in
  DBeaver; spot-check `total_amount` on a known row.
- **Data checks:** row-count reconciliation; measure spot-checks; referential integrity
  (every fact `product_id`/`customer_id` exists in its dim).

### Unit Tests

**dbt data tests** (schema tests + singular). **Edge cases explicit.**

| Test | What it verifies | Type |
|------|------------------|------|
| `unique` / `not_null` on `dim_product.product_id` | product PK integrity | happy path |
| `unique` / `not_null` on `fct_transactions.transaction_id` | fact grain | happy path |
| `relationships` fact→dim_product / dim_customer / dim_date | referential integrity | edge case |
| `accepted_values` product_id ∈ {100..104} | product domain | edge case |
| `not_null` measures on fact (quantity, unit_price, tax, total) | no clean row missing a measure | edge case |
| singular: `total_amount = quantity*unit_price + tax_amount` | measure formula correct | edge case |
| singular: partitions reconcile to raw count (clean+flagged+quarantine=100) | nothing lost | edge case |
| singular: unknown-customer member exists and flagged rows map to it | flag handling | edge case |
| quarantine-rate test (warn/error thresholds) | DQ observability behaves | failure case |
| every `dq_reasons` value ∈ known reason codes | reason vocabulary controlled | edge case |

**Python tests:** the pipeline DAG imports and the Cosmos task group renders the expected
model tasks.

## Risks & Considerations

- **Cosmos rendering/profile wiring** is the main integration risk (profiles/adapter/venv);
  verified end-to-end before sign-off, with BashOperator fallback (ADR 0001) if needed.
- **Contracts add rigidity** — a schema change now requires an explicit contract update;
  that's the point (governance), but noted.
- **Full-refresh** is fine at 100 rows; incremental is the scale path (plan 07).
- **Aggregates on clean rows only** — quarantined revenue is excluded by design; the
  completeness metric makes that visible.
- **Rollback:** models are rebuilt from `raw`; `dbt build` is idempotent; `down -v` resets.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-17 | Initial version |
| 2026-08-17 | Critical decisions confirmed: (1) **model contracts enforced** on marts (dim_*/fct_*); (2) **separate schemas** — staging models → `staging`, marts → `analytics`; (3) packages **dbt_utils + dbt_expectations**. Natural keys + `-1` unknown customer; views for staging, tables for marts (full-refresh); thin `dim_table`/`fact_table` alias views for the brief's literal names. |
