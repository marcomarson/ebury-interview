# 05 — Data Quality, Observability & Exception Handling

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-18 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Done — built & verified 2026-08-18 |

## Summary

Make the pipeline's health and data quality **observable and actionable**, the way a
platform team would run it: a reusable **alerting framework** (Airflow failure / retry /
SLA callbacks, webhook-ready), a **persisted DQ run-audit history** (trends over runs, not
just current state), native **dbt `store_failures`** so failing test rows are inspectable,
and an **active DQ report** task that surfaces/flags issues even when they only *warn*.
Covers the brief's §4 ("log or flag issues and address them") beyond the quarantine already
built in plans 03–04.

## Scope & Boundaries

**In Scope:**
- **Alerting framework** (`include/observability/notifications.py`): builds a structured
  alert (dag, task, run_id, try, exception, log url) and sends it — POST to
  `ALERT_WEBHOOK_URL` (Slack/Teams-compatible incoming webhook) when set, else a structured
  log line. Exposed as `on_failure_callback`, `on_retry_callback`, `sla_miss_callback`.
- **SLAs + retry policy**: task/DAG SLAs; retries with exponential backoff.
- **DQ run-audit history** (`dq_run_audit`, incremental): one row per run with
  `invocation_id`, `run_started_at`, received / modelled / quarantined, quarantine %, and
  per-reason counts — a trend table, not a snapshot.
- **dbt `store_failures`**: failing test rows persisted to an audit schema for debugging.
- **Active DQ report task**: after dbt, log a structured DQ summary and **alert if the
  quarantine rate exceeds a threshold** (so a warn-level signal still pages someone).
- Env-configurable thresholds/webhook; documentation of how to wire real Slack/email.
- Tests for the notifier, the report/threshold logic, and the audit append.

**Out of Scope:**
- Wiring a *real* Slack/email account (framework + docs only — no live secret to test).
- A full metrics stack (Prometheus/Grafana) or `elementary-data` report UI → plan 07
  talking points.
- Clean-room end-to-end verification & idempotency sign-off → plan 06.

## Critical platform decisions (to confirm)

> Recommendation marked; **★ = discuss before implementing.**

1. **★ Alert transport.** A **pluggable notifier**: structured log by default, POST to
   `ALERT_WEBHOOK_URL` when set (Slack/Teams incoming-webhook shape), with real Slack/email
   documented. *Rec: this* — works offline/in-review, trivially swapped for a real channel;
   avoids committing secrets or failing without them.
2. **★ DQ observability depth.** **Lightweight, self-contained**: a `dq_run_audit` history
   table + dbt `store_failures`. *Rec: this* over `elementary-data` (rich but heavy
   dependency + its own models/UI) — elementary noted as the scale option. Minimal
   (logs-only) rejected: no history.
3. **Audit implementation.** `dq_run_audit` as a **dbt incremental model** (append per run
   via `invocation_id`) rather than an Airflow-side insert — keeps the logic in dbt, tested
   and lineage-tracked. *Rec: dbt incremental.*
4. **Quarantine alert threshold.** Warn always (dbt test, plan 04) **and** an Airflow-side
   alert when quarantine % > a configurable threshold (default e.g. 40%). *Rec: as stated*
   — the current 29% warns but doesn't page; a spike would.

## Implementation Details

### Steps

1. `include/observability/notifications.py`: `build_alert(context)`, `send_alert(payload)`
   (webhook or log), and `on_failure_callback` / `on_retry_callback` / `sla_miss_callback`.
2. Wire callbacks + SLAs + exponential backoff into `customer_transactions_pipeline`.
3. `dq_run_audit` incremental dbt model (marts) + docs/tests; enable `+store_failures` and a
   test-audit schema in `dbt_project.yml`.
4. `dq_report` Airflow task (after `dbt_transform`): log the DQ summary; alert if
   quarantine % > threshold (env `DQ_QUARANTINE_ALERT_PCT`).
5. Add `ALERT_WEBHOOK_URL` / `DQ_QUARANTINE_ALERT_PCT` to compose (documented, safe defaults).
6. Tests (Python for notifier/report; dbt for the audit model); run end-to-end; verify.

### Expected Outcomes

- A task failure (or SLA miss) produces a structured alert — logged locally, POSTed if a
  webhook is configured.
- `dq_run_audit` gains a row per pipeline run (history of received/modelled/quarantined +
  reasons); re-running appends, not overwrites.
- Failing dbt tests persist their offending rows to an audit schema (`store_failures`).
- The `dq_report` task logs a readable DQ summary each run and pages only past threshold.
- Nothing added breaks the green pipeline; the quarantine warn still doesn't fail the run.

### Verification Methods

- **Automated:** `pytest` (notifier payload, webhook-vs-log path, threshold logic);
  `dbt build` incl. the audit model; a forced-failure task to confirm the alert fires.
- **Manual:** trigger the pipeline; inspect `dq_run_audit` (a new row), the `dq_report`
  logs, and (optionally) set `ALERT_WEBHOOK_URL` to a request-bin to see a POST.
- **Data checks:** `dq_run_audit` row count increments by one per run; reason counts match
  `dq_quarantine_reasons`.

### Unit Tests

**Include edge cases explicitly.**

| Test | What it verifies | Type |
|------|------------------|------|
| `build_alert` shape | payload has dag/task/run_id/try/exception fields | happy path |
| notifier logs when no webhook | `ALERT_WEBHOOK_URL` unset → structured log, no HTTP | edge case |
| notifier POSTs when webhook set | webhook set → single POST with payload (mocked) | happy path |
| notifier swallows webhook errors | a failing webhook doesn't crash the task | failure case |
| dq_report under threshold | quarantine % below threshold → no alert, logs summary | edge case |
| dq_report over threshold | quarantine % above threshold → alert fired | failure case |
| audit appends per run | `dq_run_audit` grows by one row per invocation | edge case |
| audit reason counts | per-reason counts reconcile with `dq_quarantine_reasons` | edge case |

### Alerting note (real channels)

`ALERT_WEBHOOK_URL` accepts a Slack/Teams **incoming webhook** URL; in production it comes
from a secrets backend (ADR 0002), never committed. Email would use Airflow's SMTP config.
The notifier is the seam — the transport is swappable without touching DAG logic.

## Risks & Considerations

- **No live alert channel in review** — mitigated by the log-by-default notifier and a
  documented webhook; the framework is what's assessed, not a specific Slack.
- **Incremental audit** must stay idempotent per `invocation_id` (no dup rows on retry).
- **store_failures** adds audit tables/schema — kept small; documented.
- **Alert fatigue** — thresholds are configurable so warns don't page unless meaningful.
- **Rollback:** additive; audit/test-failure tables are rebuildable; `down -v` resets.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-18 | Initial version |
| 2026-08-18 | Decisions confirmed: (1) **pluggable notifier** (log by default / webhook when set); (2) **lightweight self-contained** DQ observability (`dq_run_audit` + `store_failures`) — **note:** `elementary-data` would be the better choice for larger projects (persisted test history, anomaly detection, report UI); (3) `dq_run_audit` as a **dbt incremental** model. |
| 2026-08-18 | **Implemented & verified.** Added `include/observability/` (notifications + pure `evaluate_dq`), wired failure/retry/SLA callbacks + exponential backoff into the pipeline, added `dq_report` task, `dq_run_audit` incremental model, and `store_failures` → `dq_audit` schema. Results: `dbt build` PASS=40 WARN=1 ERROR=0; **18/18 pytest**; pipeline run success with `dq_report`; `dq_run_audit` appends per run (1→2); `dq_audit` schema holds persisted test results. Alert fires only above `DQ_QUARANTINE_ALERT_PCT` (29% < 40% → no page). |
