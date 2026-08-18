# 06 — End-to-End Verification & Idempotency

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-18 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Done — built & verified 2026-08-18 |

## Summary

Prove the pipeline deploys and runs **flawlessly from scratch** and is **idempotent** —
the way a platform team gates a release. Codify the acceptance criteria as an automated
**acceptance test**, run a **clean-room deploy** (`docker compose down -v` → `up --build` →
trigger → assert), and verify **idempotency** (re-running yields identical marts, no
duplicates; only the append-only DQ audit grows). This directly evidences the brief's
"deployable with `docker-compose up`" requirement.

## Scope & Boundaries

**In Scope:**
- **Acceptance test** (`tests/test_acceptance.py`): asserts the post-pipeline warehouse
  end-state — raw=100, fact=71, quarantine=29, `reconciles=true`, no duplicate PKs,
  `total = qty*price + tax`, referential integrity (fact→dims), dim counts, audit present,
  aggregate revenue shares sum to ~100.
- **Verification harness**: a `make verify` target (+ documented `docker compose` commands)
  that triggers the pipeline, waits for success, and runs the acceptance test — CI-ready.
- **Clean-room run**: full `down -v` → `up -d --build` → trigger → acceptance, executed and
  documented (from an empty machine state).
- **Idempotency check**: run the pipeline twice; assert `fct`/dims/quarantine/aggregate
  counts are identical and no duplicate `transaction_id`, while `dq_run_audit` grows by one
  row per run (intended history, not drift).
- README **Verification** section update.

**Out of Scope:**
- Real CI wiring (GitHub Actions workflow) — a sample is a plan 07 talking point.
- Performance/load testing (dataset is 100 rows).
- New pipeline behaviour — this plan only *verifies* what plans 01–05 built.

## Critical decision (to confirm)

- **★ Harness form.** A **pytest acceptance test** (`tests/test_acceptance.py`) run against
  the live warehouse, wrapped by a `make verify` target that triggers + waits + asserts.
  *Rec: this* — structured, reusable, CI-friendly, cross-platform (runs in-container), and
  consistent with the existing pytest suite. A pure shell script is the alternative (simple
  but Windows/again-cross-platform-awkward and less structured).

## Implementation Details

### Steps

1. Write `tests/test_acceptance.py` with the end-state assertions (uses `PostgresHook`,
   like the integration tests). Keep it independent of unit tests (it needs a populated
   warehouse).
2. Add a `verify` flow: `make verify` = trigger `customer_transactions_pipeline`, wait for
   success, then `pytest tests/test_acceptance.py`. Document the raw commands too.
3. Run the **clean-room**: `docker compose down -v` → `up -d --build` → wait healthy →
   trigger → acceptance. Capture the result in the plan Change Log / README.
4. Run **idempotency**: trigger a 2nd time; assert marts identical + `dq_run_audit` +1.
5. Update README Verification section.

### Expected Outcomes

- From an empty machine (`down -v`), `docker compose up -d --build` brings the stack up
  healthy and the pipeline runs green — no manual steps.
- The acceptance test passes: every end-state assertion holds.
- Second run: identical fact/dim/quarantine/aggregate counts, zero duplicate PKs; audit
  grows by exactly one row.

### Verification Methods

- **Automated:** `make verify` (trigger + wait + acceptance) exits 0; `pytest tests -q`
  (unit + integration + acceptance) green.
- **Manual:** inspect the marts in DBeaver after a clean-room run.
- **Data checks:** the acceptance assertions are themselves the data checks.

### Unit Tests

The plan-06 deliverable *is* the acceptance test; edge cases are the assertions.

| Assertion | What it verifies | Type |
|-----------|------------------|------|
| raw=100, fact=71, quarantine=29 | partition sizes | happy path |
| `dq_completeness.reconciles` true | nothing lost | edge case |
| no duplicate `transaction_id` in fact | grain integrity | edge case |
| `total = qty*price + tax` (0 violations) | measure formula | edge case |
| fact→dim_product/customer/date all resolve | referential integrity | edge case |
| dim_product=5, dim_customer=11 (incl. unknown) | dimension completeness | edge case |
| `dq_run_audit` ≥ 1 row | observability wired | happy path |
| revenue_share_pct sums to ~100 | aggregate correctness | edge case |
| idempotency: 2nd run stable, audit +1 | reproducibility | edge case |

## Risks & Considerations

- **Idempotency nuance:** marts are full-refresh (stable); `dq_run_audit` is append-only by
  design — the check must expect it to grow, not treat that as drift.
- **Clean-room timing:** first `up --build` is slow (image build, dbt deps); the harness
  waits on health/state, not fixed sleeps.
- **Cross-platform:** the acceptance test runs in-container (no host Python needed); the
  `make verify` wrapper documents the raw `docker compose` equivalents for Windows.
- **Rollback:** verification-only; no schema/behaviour changes.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-18 | Initial version |
| 2026-08-18 | **Built & verified.** Added `tests/test_acceptance.py` (8 acceptance checks, `acceptance` marker) + `make verify` + `make test` now excludes acceptance. **Clean-room** (`down -v` → `up -d --build`): stack healthy in ~24s, pipeline success, **acceptance 8/8**. **Idempotency:** 2nd run → `fct`=71 stable, no duplicate PKs, `dq_run_audit` +1 (append-only history, as designed). **Perf fix found during verification:** removed Cosmos per-task `install_deps` (LOCAL execution runs in the project dir with baked packages) → pipeline **5 min → 36 s**. |
