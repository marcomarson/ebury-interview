# 08 — README & Submission Polish

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | 2026-08-19 |
| AI Tool/Model | Claude Opus 4.8 |
| Status | Draft — awaiting approval |

## Summary

Final pass to make the repo **submission-ready**: a README that takes a cold-clone reviewer
from zero to a running pipeline in minutes, an explicit **brief → delivery** traceability
table so the evaluator can tick every requirement, repo hygiene (no stray/secret/artefact
files), and a final **clean-room verification** to sign off. No new pipeline behaviour — this
plan closes out and packages what plans 01–07 built.

## Scope & Boundaries

**In Scope:**
- **README final review:** a tight top (what/why in two lines), a bulletproof quick-start,
  prominent links to the [presentation](../docs/presentation.html) and
  [architecture & trade-offs](../docs/architecture-and-tradeoffs.md), and a **compliance
  table** mapping each brief requirement to where it's delivered.
- **Repo hygiene:** confirm `.gitignore` covers all artefacts; no secrets, `target/`,
  `dbt_packages/`, `.user.yml`, or the case PDF committed; consistent naming; remove dead files.
- **Final clean-room verification:** `docker compose down -v` → `up -d --build` → trigger →
  acceptance (8/8), captured as the submission sign-off.
- A short **submission checklist** (in this plan) covering repo contents, deployability, docs.

**Out of Scope:**
- New pipeline features or model changes.
- Building the production enhancements (they stay as roadmap/talking points in plan 07).

## Decision (to confirm)

- **CI (GitHub Actions):** **keep as a documented talking point**, *don't* commit a workflow.
  *Rationale:* a correct CI needs the raw table seeded (our ingestion is Airflow-driven, not a
  dbt seed), so a naive `dbt build` workflow would fail — a red CI badge on the submission is
  worse than none. The CI story (lint → dbt build on throwaway Postgres → pytest → image per
  SHA) is already in the trade-offs doc. *Alternative:* invest in a real, green CI (adds a
  seeding step + a slim job) — more work, out of the brief's ask.

## Implementation Details

### Steps

1. Read the current README end-to-end as a first-time reviewer; fix any friction, stale
   command, or broken link.
2. Add a **brief → delivery** table near the top (the six brief requirements → where met).
3. Ensure the presentation + architecture doc are linked prominently.
4. Repo hygiene sweep: `git ls-files` review, `.gitignore` check, confirm no PDF/secrets/artefacts.
5. Run the **final clean-room**; record the result.
6. Add a submission checklist; mark plan 08 + roadmap done.

### Expected Outcomes

- A reviewer can clone, run `docker compose up -d --build`, trigger the pipeline, and verify —
  guided entirely by the README.
- Every brief requirement maps to a concrete file/section.
- Clean-room passes 8/8 acceptance; repo contains no secrets or build artefacts.

### Verification Methods

- **Automated:** final clean-room (`down -v` → `up --build` → pipeline → `pytest -m acceptance`
  = 8/8); `pytest tests -q -m 'not acceptance'` green.
- **Manual:** README read-through; click every link; `git ls-files` shows only intended files.
- **Data checks:** the acceptance suite (partition sizes, reconciliation, integrity).

### Unit Tests

No new code. The gate is the existing test + acceptance suites passing from a clean room, and
a documentation/link review.

## Submission checklist

- [ ] `docker compose up -d --build` brings the stack up healthy from a clean machine.
- [ ] `customer_transactions_pipeline` runs green end-to-end.
- [ ] `pytest tests` (unit + integration) and `-m acceptance` all pass.
- [ ] README: setup, run, verify, architecture summary, links to deeper docs.
- [ ] Brief → delivery table present and accurate.
- [ ] No secrets, `target/`, `dbt_packages/`, `.user.yml`, or case PDF in git.
- [ ] All ADRs + plans + roadmap up to date.
- [ ] GitHub repo private; link ready to share.

## Risks & Considerations

- **Over-polishing** — stop when a reviewer can succeed unaided; don't gold-plate.
- **Link rot** — the presentation is a private Artifact URL; the README should describe it,
  not depend on the reviewer having access (the markdown docs are the in-repo source of truth).
- **Rollback:** documentation-only; no behaviour changes.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-19 | Initial version |
