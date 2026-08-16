# ADR 0004 — Bake project code into the image (mount-override for dev)

- **Status:** Accepted
- **Date:** 2026-08-16
- **Deciders:** Marco Marson (with Claude)
- **Context tags:** packaging, reproducibility, docker, dbt, airflow

## Context

The dbt models and Airflow DAGs are **source code** — they live in git (the source of
truth and the graded deliverable). A separate question is **how that code reaches the
running container at runtime**: bind-mounted from the host, or baked into the image.

- **Bind mount** — fast dev iteration (edit → rerun, no rebuild), but the container
  depends on host files; the image alone is not a complete, shippable artifact.
- **Baked in (`COPY`)** — the image is immutable, self-contained, and reproducible
  (tied to a git SHA); but every change needs a rebuild.

## Decision

**Do both.** `COPY dags/` and `COPY dbt/` into the Airflow image so the image is a
self-contained, prod-ready artifact. In **local development**, `docker-compose.yml`
bind-mounts `./dags` and `./dbt` over those paths — the mount *shadows* the baked copy,
preserving the fast edit-rerun loop.

Net effect:
- **Local dev:** the mount wins → instant iteration, no rebuild.
- **Prod/CI:** run the image with no mounts → the baked code runs, immutable and versioned.

A `.dockerignore` keeps the build context lean (excludes `.git`, docs, `ebury-docs/`,
runtime artifacts like `target/`, `logs/`, `.user.yml`).

`db/init/*.sql` (warehouse bootstrap) stays in git and is mounted into the Postgres
`docker-entrypoint-initdb.d`; it could likewise be baked into a custom warehouse image if
we ever need that fully self-contained.

## Consequences

**Positive**
- The image is a complete deployable artifact — no host-file dependency in prod.
- Dev speed is unchanged (mount override).
- Clear separation: git = source of truth; image = immutable runtime artifact.

**Negative / risks**
- Two delivery paths to keep in mind (mounted vs baked). Mitigated by documenting the
  override behaviour here and in the README.
- The image must be rebuilt to ship code changes (expected for an immutable-artifact model).

## Follow-ups

- When CI is added (plan 07 talking point), build and tag the image per git SHA so the
  deployed artifact is traceable.
