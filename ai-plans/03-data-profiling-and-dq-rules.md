# 03 — Data Profiling & DQ Rule Definition

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-17 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Draft — awaiting approval |

## Summary

Systematically **profile** the landed raw data, **quantify** every data-quality issue, and
**define the exact rules** the dbt layer will apply in plan 04 — which values to *coerce*
(recover), which rows to *quarantine* (reject with a reason), and which to keep but *flag*.
This is a design/analysis step: its output is a data-quality report + an agreed ruleset +
a decision record, backed by real counts from profiling queries. Little runtime code; the
rules get *implemented and tested* in plan 04.

## Scope & Boundaries

**In Scope:**
- Profiling SQL (`include/sql/profiling/`) run against `raw.customer_transactions` that
  quantifies each issue: null counts per column, prefixed-id counts, unparseable
  numerics, date-format split, product_id↔product_name consistency, duplicates, ranges.
- A **data-quality report** (`docs/data-quality.md`): the issue catalogue mapped to DQ
  dimensions (completeness, validity, consistency, uniqueness, accuracy), with counts.
- The **agreed ruleset** (coerce / quarantine / flag) per field, with rationale.
- The **quarantine design**: split the staging layer into a clean set and a
  `quarantine_customer_transactions` set carrying `dq_reasons`; shape of the reason data.
- An ADR (0005) recording the DQ strategy (esp. the two judgment calls below).

**Out of Scope:**
- Implementing the dbt staging / dim / fact / quarantine models → **plan 04**.
- dbt data tests & the observability/alerting surface → **plans 04/05**.
- Any change to ingestion (raw stays as-is, all TEXT).

## Data-quality issues (from the raw sample) & proposed rules

Grain: one transaction. Core measures: `quantity`, `price`, `tax` (needed to compute a
line total). Dimensions: customer, product, date.

| Field | Issue observed | DQ dimension | Proposed rule |
|-------|----------------|--------------|---------------|
| `transaction_id` | `T` prefix on some rows (`T1010`) | validity | **Coerce**: strip leading `T` → integer |
| `customer_id` | float form (`501.0`); some empty | validity, completeness | **Coerce** float→int; **empty → keep + flag** (unknown-customer member), *not* quarantine |
| `transaction_date` | mixed `YYYY-MM-DD` and `DD-MM-YYYY` | consistency, validity | **Coerce**: parse both → `date`; unparseable → quarantine |
| `product_id` | `P` prefix (`P100`) = same as `100` | consistency, validity | **Coerce**: strip leading `P` → integer |
| `product_name` | ok; possible whitespace/case | consistency | **Coerce**: trim/standardize |
| `quantity` | float (`1.0`); some empty | validity, completeness | **Coerce** float→int; **empty/invalid → quarantine** (measure unusable) |
| `price` | word values (`Two Hundred`) | validity, accuracy | **Quarantine** if not numeric (measure unrecoverable) |
| `tax` | word values (`Fifteen`) | validity, accuracy | **Quarantine** if not numeric (measure unrecoverable) |

Also profiled (checks, expected clean but verified): duplicate `transaction_id` after
de-prefixing; negative/zero `quantity`/`price`; `product_id`→`product_name` 1:1 mapping;
dates within the expected window.

### Two judgment calls to confirm

1. **No word→number parsing.** `Two Hundred` / `Fifteen` are treated as **invalid → the row
   is quarantined**, not decoded to 200/15. Rationale: word-to-number recovery is fragile
   and not generalizable (we can't enumerate every possible spelling), and silently
   inventing a monetary value is worse than quarantining it for review. *(Senior call —
   worth stating explicitly on the review.)*
2. **Missing `customer_id` is kept, not quarantined.** The transaction's *measures* are
   still valid, so we keep the row, attach it to an **"unknown" customer member**, and
   **flag** it (`missing_customer`). We don't drop revenue just because the customer key is
   absent. Contrast with a broken *measure* (price/tax/quantity), which makes the row's
   amount uncomputable → quarantine.

### Quarantine vs flag — the principle

- **Quarantine** (reject, with reason): the row's **core amount cannot be computed** —
  non-numeric `price`/`tax`, missing/invalid `quantity`, unparseable `transaction_date`,
  or unusable `transaction_id`.
- **Flag** (keep, annotate): the row is usable but imperfect — e.g. `missing_customer`.
- Both clean and quarantined rows are **persisted** (nothing silently dropped);
  quarantined rows carry a `dq_reasons` list so issues are auditable and fixable.

### Open question for plan 04

- Is `tax` an **absolute amount** or a **rate**? Values (~5–30) alongside prices (~50–300)
  are ambiguous. Profiling will report the distribution; the net/gross formula in the fact
  table (plan 04) depends on the answer. Flag for decision, don't block plan 03.

## Implementation Details

### Steps

1. Write profiling queries in `include/sql/profiling/` (one concern per query, commented).
2. Run them against the loaded `raw` table; capture the counts.
3. Author `docs/data-quality.md`: issue catalogue + counts + DQ-dimension mapping + the
   agreed rules + the quarantine reason schema.
4. Record the DQ strategy + the two judgment calls as **ADR 0005**.
5. Confirm the ruleset with reviewer before plan 04 implements it.

### Expected Outcomes

- A reproducible profiling script and a concrete, numbers-backed DQ report.
- An agreed, unambiguous ruleset (coerce/quarantine/flag per field) ready to implement.
- A documented quarantine model shape + `dq_reasons` schema.

### Verification Methods

- **Automated:** profiling queries run clean and return the documented counts; a small
  check that re-running profiling on the loaded data reproduces the same numbers (baseline).
- **Manual:** spot-check a handful of rows per rule (e.g. every quarantine reason has at
  least one real example in the data).
- **Data checks:** counts in the report reconcile to `raw` totals (clean + quarantined +
  flagged partitions account for all 100 rows).

### Unit Tests

Tests to be written. **Include edge cases explicitly.** (Plan 03 defines the assertions;
most become dbt data tests implemented in plan 04.)

| Test | What it verifies | Type |
|------|------------------|------|
| profiling: numeric classifier counts | count of non-numeric `price`/`tax` matches the report | happy path |
| profiling: null-completeness counts | null `customer_id`/`quantity` counts match the report | happy path |
| profiling: date-format split | rows split into ISO vs `DD-MM-YYYY` sum to 100 | edge case |
| profiling: id de-prefix uniqueness | `transaction_id` unique after stripping `T` | edge case |
| profiling: product map 1:1 | each `product_id` (post de-prefix) maps to exactly one `product_name` | edge case |
| partition completeness | clean + quarantined + flagged = 100 rows (nothing lost) | edge case |
| classifier: `"Two Hundred"` | classified non-numeric → quarantine candidate | failure case |
| classifier: empty `quantity` | classified invalid → quarantine candidate | failure case |
| classifier: empty `customer_id` | classified flag (kept), not quarantine | edge case |

Edge cases: empty string vs NULL, whitespace-only, `P100` vs `100`, `T`-prefixed ids,
both date formats, duplicate ids, zero/negative measures.

## Risks & Considerations

- **Over-aggressive quarantine** would discard usable revenue; mitigated by quarantining
  only on broken *measures*, keeping dimension gaps as flags.
- **Word→number parsing** is deliberately rejected (fragile); documented as a decision.
- **Rules must stay in sync with plan 04** — this report is the single source the dbt
  models implement against; changes here trigger a plan-04 update.
- **The dataset is small (100 rows)** — profiling is exhaustive here; at scale the same
  queries become sampled/materialized checks (noted for the plan 07 writeup).

## Change Log

| Date | Change |
|------|--------|
| 2026-08-17 | Initial version |
