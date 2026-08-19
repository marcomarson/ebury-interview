# 07 — Trade-offs & Enhancements Writeup

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-19 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Done — written & presentation built 2026-08-19 |

## Summary

Consolidate every design decision into one **architecture-and-trade-offs narrative** for
the interview: what was built and why, what was **deliberately kept simple** (and the
reasoning), and **how it scales to production** — the enhancement roadmap. This is the
document that carries the platform conversation; it pulls together ADRs 0001–0005 and the
"scale to prod" talking points accumulated across the plans, with a system diagram.

## Scope & Boundaries

**In Scope:**
- `docs/architecture-and-tradeoffs.md` with:
  1. **System overview** + a diagram (component/data-flow) of ingest → dbt (Cosmos) →
     star + quarantine → observability.
  2. **Decisions & trade-offs** — a consolidated table/narrative from ADRs 0001–0005
     (decision · why · trade-off · when to revisit).
  3. **Deliberately kept simple** — LocalExecutor, single-node Postgres, full-refresh,
     log-based alerting, targeted dev mounts, classic dbt — each with the rationale.
  4. **Production scaling roadmap** grouped by area (orchestration, warehouse/modelling,
     CI/CD, observability, governance, security), each item = what + why + rough effort.
  5. A **prioritized enhancement table** (impact × effort).
- A diagram rendered as **Mermaid in the markdown** (renders on GitHub, version-controlled).
- Link the doc from the README and the ADR index.

**Out of Scope:**
- Implementing any of the enhancements (this is a design/writeup step).
- Final README polish / submission checklist → **plan 08**.

## Critical decisions (to confirm)

> Recommendation marked; **★ = discuss.**

1. **★ Diagram form.** **Mermaid embedded in the markdown** — renders on GitHub, lives in
   git, no binary. *Rec: this.* (A polished Artifact/PNG is a nice extra but not the
   source of truth.)
2. **Emphasis.** Balance the three audiences: *reviewer skim* (diagram + summary table),
   *platform depth* (trade-offs + scaling), *pragmatism* (what we kept simple & why).
   *Rec: lead with the diagram + a one-screen decision table, then depth.*

## The scaling roadmap (content outline — to be written up)

- **Orchestration:** Cosmos `LoadMode.DBT_MANIFEST` (bake manifest → no `dbt deps` at
  parse); `KubernetesPodOperator` / Cosmos k8s mode for isolated per-run pods; Celery/K8s
  executor beyond LocalExecutor; DockerOperator/dbt Cloud (ADR 0001).
- **Warehouse & modelling:** cloud warehouse (Snowflake/BigQuery/Redshift) → unlocks dbt
  Fusion (ADR 0003); **incremental** fact/audit models with `unique_key`; snapshots for
  SCD; partitioning/clustering.
- **CI/CD:** GitHub Actions — lint (`sqlfluff`), `dbt build` on a throwaway Postgres, slim
  CI (`state:modified`), build & tag the image per git SHA (ADR 0004); dbt unit tests
  (1.8+).
- **Observability:** `elementary-data` (test history, anomaly detection, report) over the
  lightweight audit (plan 05); Airflow metrics → Prometheus/Grafana; real Slack/email
  transport for the notifier.
- **Governance:** data catalog + lineage (dbt docs/exposures), access controls/grants per
  schema, PII tagging & masking, data contracts already enforced — extend with
  `dbt_expectations` distributions.
- **Security:** secrets from a manager (ADR 0002); least-privilege DB roles; image scanning.

## Implementation Details

### Steps

1. Draft `docs/architecture-and-tradeoffs.md` (sections above); build the Mermaid diagram.
2. Consolidate ADRs 0001–0005 into the decisions table (don't duplicate — summarize + link).
3. Write the "kept simple" and "scaling roadmap" sections; add the prioritized table.
4. Link from README + `docs/adr/README.md`.
5. Review for accuracy against the actual repo (no aspirational claims).

### Expected Outcomes

- One self-contained document a reviewer can read to understand the whole system, the
  reasoning, and the path to production — without reading the code.
- Diagram renders on GitHub; all claims trace to something real in the repo.

### Verification Methods

- **Automated:** none (documentation); Mermaid syntax renders (checked in the GitHub
  preview / a Mermaid linter).
- **Manual:** read-through for accuracy; every "we did X" maps to a file/plan; every
  "we'd do Y" is clearly future.
- **Data checks:** n/a.

### Unit Tests

No code. The "test" is an accuracy review: each decision links to its ADR/plan, and the
diagram matches the implemented DAG/model graph.

## Risks & Considerations

- **Aspirational drift** — keep a hard line between *built* and *future*; label clearly.
- **Duplication** — summarize ADRs, link rather than copy, to avoid divergence.
- **Diagram staleness** — keep it high-level (components/flow) so it doesn't rot with
  small model changes.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-19 | Initial version |
| 2026-08-19 | Confirmed: Mermaid-in-markdown diagram; make it **didactic + presentable**. Wrote [`docs/architecture-and-tradeoffs.md`](../docs/architecture-and-tradeoffs.md) (big picture, follow-the-data, decisions, kept-simple, scaling roadmap, prioritized table, call cheat-sheet) and a visual **presentation Artifact** ([`docs/presentation.html`](../docs/presentation.html)) for screen-sharing in the interview. Linked from README + ADR index. |
