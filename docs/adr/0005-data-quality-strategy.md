# ADR 0005 — Data-quality strategy (coerce / quarantine / flag)

- **Status:** Accepted
- **Date:** 2026-08-17
- **Deciders:** Marco Marson (with Claude)
- **Context tags:** data-quality, dbt, modelling, governance

## Context

`raw.customer_transactions` is deliberately dirty (profiled in
[`docs/data-quality.md`](../data-quality.md)): prefixed IDs, float-form integers, mixed
date formats, missing values, and word-valued numbers. The case asks us to *handle* these
issues and document the approach, not silently drop or blindly coerce them.

## Decision

A three-way disposition per row, driven by whether the row's **core amount** (quantity ×
price + tax) can be computed:

1. **Coerce** recoverable formatting issues — strip `T`/`P` prefixes, parse float-form
   integers, parse both date formats, trim strings.
2. **Quarantine** rows whose core measure is unusable — non-numeric `price`/`tax`, missing
   or invalid `quantity`, unparseable date, or unusable `transaction_id`. Quarantined rows
   are **persisted** in `quarantine_customer_transactions` with a `dq_reasons` list (never
   dropped), so issues are auditable and fixable.
3. **Flag** rows that are usable but imperfect — a missing `customer_id` is kept, mapped to
   an unknown-customer member, and flagged `missing_customer`.

Two explicit judgment calls:

- **No word→number parsing.** `Two Hundred`/`Fifteen` → quarantine, not 200/15. Word-to-
  number recovery is fragile and not generalizable; inventing a monetary value is worse
  than segregating it.
- **Missing `customer_id` is a flag, not a quarantine.** We don't discard valid revenue
  over a missing dimension key; a broken *measure* is what triggers quarantine.

- **`tax` is an absolute amount** (not a rate) — evidenced by near-zero correlation with
  price and continuous, non-round values. `total = quantity × price + tax`.

- **Quarantine-first, tests as backstop.** A detectable-but-unexpected problem (implausible
  value, duplicate grain) is **quarantined with a reason and the run stays green**, not
  hard-failed — at that moment we don't know if it's serious, so we segregate and review.
  The staging classifier owns this (reasons: `price_non_positive`, `tax_negative`,
  `quantity_non_positive`, `duplicate_transaction_id`, plus the originals); the dbt tests
  (`unique`, `relationships`, range checks) remain a last-resort net. Extending is a
  localized change: one `case` in `stg_customer_transactions` + the code in
  `assert_dq_reasons_known`.

## Consequences

**Positive**
- Nothing is silently lost: every row is clean, flagged, or quarantined-with-reason
  (61 / 10 / 29 on the current data), and the partitions reconcile to 100.
- The rule set is explicit, testable (dbt data tests in plan 04), and auditable.
- Revenue isn't distorted by invented values or dropped over missing dimensions.

**Negative / risks**
- Quarantining on missing `quantity` segregates 16 rows; acceptable because their amount
  is uncomputable. Revisit if the business prefers imputation.
- The rules are dataset-specific; new dirty patterns need new rules (and a report update).

## Quarantine mechanics (decided 2026-08-17)

- **Storage:** one table `analytics.quarantine_customer_transactions`, one row per rejected
  record, with `dq_reasons text[]` (all failed rules) + lineage timestamps; a companion
  view unnests reasons for per-reason counts.
- **Pipeline behaviour:** quarantining does **not** fail the run — a dbt test *warns* with
  the count/rate every run and *errors* only in the extreme (empty clean set / very high
  rate, configurable).
- **Fact/dims from clean rows only**, with a completeness metric (received / modelled /
  quarantined) so coverage is visible.
- **Remediation:** fix source + re-run; idempotent truncate+load reprocesses everything.

See [`docs/data-quality.md`](../data-quality.md) for the full mechanics.

## Follow-ups

- Implement the split (clean vs quarantine), the star schema, and the dbt tests in plan 04.
- Surface quarantine counts/reasons as an observability signal in plan 05.
