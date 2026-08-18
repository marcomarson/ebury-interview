# Data Quality Report — `customer_transactions`

Profiling of the landed raw data and the agreed rules the dbt layer implements (plan 04).
Numbers below come from `include/sql/profiling/` run against `raw.customer_transactions`
(100 rows). Reproduce with:

```bash
docker compose exec -T warehouse psql -U ebury -d ebury < include/sql/profiling/profile_customer_transactions.sql
docker compose exec -T warehouse psql -U ebury -d ebury < include/sql/profiling/analyze_tax.sql
```

## Partition summary

| Partition | Rows | Meaning |
|-----------|------|---------|
| Fully clean | 61 | pass every rule |
| Clean + flagged | 10 | usable, but missing customer |
| Quarantined | 29 | a core measure is unusable |
| **Total** | **100** | nothing dropped silently |

## Issue catalogue (by DQ dimension)

| Field | Issue | Count | DQ dimension |
|-------|-------|------:|--------------|
| `transaction_id` | `T` prefix (e.g. `T1010`) | 10 | validity |
| `customer_id` | float form (`501.0`) | 86 | validity |
| `customer_id` | missing (empty) | 14 | completeness |
| `transaction_date` | `DD-MM-YYYY` (vs ISO) | 12 | consistency |
| `product_id` | `P` prefix (`P100`) | 6 | consistency |
| `quantity` | float form (`1.0`) | 84 | validity |
| `quantity` | missing (empty) | 16 | completeness |
| `price` | non-numeric (`Two Hundred`) | 11 | validity / accuracy |
| `tax` | non-numeric (`Fifteen`) | 9 | validity / accuracy |

Verified-clean checks: `transaction_id` unique after de-prefixing (100 distinct, 0 dupes);
`product_id`→`product_name` mapping is **1:1** (100=E, 101=A, 102=B, 103=C, 104=D — 20 each);
all dates fall in 2023-07-10 … 2023-07-20; no zero/negative quantities.

## Rules

### Coerce (recover the value)

| Field | Transformation |
|-------|----------------|
| `transaction_id` | strip leading `T` → integer |
| `customer_id` | parse float form → integer; empty → unknown-customer member + flag |
| `transaction_date` | parse `YYYY-MM-DD` **or** `DD-MM-YYYY` → `date` |
| `product_id` | strip leading `P` → integer |
| `product_name` | trim / standardize |
| `quantity` | parse float form → integer |
| `price`, `tax` | cast to numeric when numeric |

### Quarantine (reject → `quarantine_customer_transactions` with `dq_reasons`)

The row's **core amount cannot be computed**:

| Reason | Trigger | Rows |
|--------|---------|-----:|
| `price_not_numeric` | `price` not numeric (`Two Hundred`) | 11 |
| `tax_not_numeric` | `tax` not numeric (`Fifteen`) | 9 |
| `quantity_missing_or_invalid` | `quantity` empty / not numeric | 16 |
| `date_unparseable` | date matches neither format | 0* |
| `transaction_id_invalid` | empty / non-numeric after strip | 0* |

\* No occurrences in this dataset, but the rule stays for robustness. Rows can trigger
multiple reasons (overlap): 29 distinct rows quarantined.

### Flag (keep + annotate)

| Flag | Trigger | Rows |
|------|---------|-----:|
| `missing_customer` | `customer_id` empty → mapped to unknown-customer member | 14† |

† 14 rows have a missing customer; 10 land in the clean set (flagged), the other 4 are
also quarantined for a broken measure.

### Two judgment calls (decided)

1. **No word→number parsing.** `Two Hundred` / `Fifteen` are treated as invalid → quarantine,
   not decoded to 200/15. Rationale: fragile, not generalizable, and inventing a monetary
   value is worse than segregating it for review.
2. **Missing `customer_id` is kept, not quarantined.** The measures are valid; we keep the
   row, map it to an unknown-customer member, and flag it — we don't drop revenue over a
   missing dimension key. A broken *measure*, by contrast, is quarantined.

## `tax` semantics — absolute amount (not a rate)

Evidence (`analyze_tax.sql`):

- `corr(tax, price) = 0.179`, `corr(tax, qty×price) = 0.149` → essentially **uncorrelated**;
  a percentage of price would correlate strongly.
- Values are continuous (5.43–29.80, stddev 7.43) with **1/91 whole numbers** — not the
  round, repeated values a standard rate would show.
- `tax/price` spreads 5%–45% (no single-rate cluster).

**Decision:** `tax` is an absolute per-transaction amount →
`total_amount = quantity × price + tax`, with `subtotal = quantity × price` as pre-tax
revenue. (Implemented in plan 04.)

## Downstream shape (plan 04)

- **Staging** splits `raw` into the clean/typed set and `quarantine_customer_transactions`
  (+ `dq_reasons`), plus per-row flags.
- **Star:** `dim_product`, `dim_date`, `dim_customer` (with unknown member), and
  `fact_transactions` at transaction grain with the measures above.
- **Aggregates:** monthly totals, totals by customer, totals by product.
- dbt data tests enforce these rules (uniqueness, not-null, accepted values/ranges,
  relationships).
