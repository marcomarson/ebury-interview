# ADR 0001 — Orchestrating dbt from Airflow

- **Status:** Accepted
- **Date:** 2026-08-16
- **Deciders:** Marco Marson (with Claude)
- **Context tags:** orchestration, dbt, airflow, platform

## Context

The pipeline uses Airflow to orchestrate dbt transformations on Postgres, all inside
`docker-compose`. We must decide **how Airflow invokes dbt**. The guiding principle is
that Airflow is an *orchestrator*, not an *execution environment*: the main risk to
design against is `dbt-core` and `apache-airflow` fighting over shared transitive
dependencies in one Python environment. Secondary goals: per-model observability,
scalability, and — for a take-home — reliably running on the reviewer's machine.

## Decision

Use **Astronomer Cosmos** to render the dbt project as Airflow tasks, running dbt in an
**isolated virtualenv** (Cosmos `ExecutionMode.VIRTUALENV`, or a dedicated venv baked into
a custom Airflow image) so dbt's dependencies never collide with Airflow's core.

Keep a **BashOperator + isolated dbt venv** approach as a documented, tested fallback in
case Cosmos proves brittle under time constraints — it tells the same "decoupled dbt +
observability" story, just with coarser granularity.

## Options considered

| # | Option | Isolation | Observability | Self-contained in compose | Verdict |
|---|--------|-----------|---------------|---------------------------|---------|
| 1 | BashOperator / PythonOperator (dbt CLI) | Only if you add a venv/container | dbt = one opaque task | ✅ | Fallback |
| 2 | **Astronomer Cosmos** | ✅ via execution modes | **Per-model tasks, retries, lineage** | ✅ | **Chosen** |
| 3 | DockerOperator (dbt in own container) | ✅ strong | Per-run container | ⚠️ needs Docker socket in Airflow (DinD) | Rejected here |
| 4 | KubernetesPodOperator | ✅ strong | Per-pod | ❌ needs a K8s cluster | Prod pattern, not here |
| 5 | dbt Cloud provider (`DbtCloudRunJobOperator`) | ✅ (managed) | dbt Cloud UI | ❌ external SaaS + token | Out of scope (brief wants dbt-core) |
| 6 | Legacy `airflow-dbt` package | — | — | ✅ | Deprecated — don't use |

### Why not the others (short form)

- **BashOperator (1):** boringly reliable but the whole dbt project is a single green/red
  box — no model-level retries or lineage. Retained only as fallback.
- **DockerOperator (3):** cleanest prod-like isolation, but inside compose it requires
  mounting the Docker socket into the Airflow scheduler (Docker-in-Docker) — friction,
  a mild security smell, and slower feedback. Wrong cost/benefit for a laptop take-home.
- **KubernetesPodOperator (4):** the production-grade answer (container-per-run, horizontal
  scale) but needs a cluster — outside a docker-compose deliverable.
- **dbt Cloud (5):** offloads execution to SaaS; not self-contained and contradicts the
  brief's dbt-core requirement.
- **`airflow-dbt` (6):** superseded by Cosmos; effectively deprecated.

## Consequences

**Positive**
- Each dbt model/test surfaces as its own Airflow task → granular retries, clearer
  failure isolation, and lineage visible in the Airflow graph.
- dbt runtime is decoupled from Airflow's dependency tree (isolation), the specific
  production failure mode we set out to avoid.
- Cosmos is the community standard, so the pattern scales from 3 models to hundreds
  without changing shape.

**Negative / risks**
- Cosmos adds a dependency and some configuration surface (profiles/adapter wiring);
  it can be finicky. Mitigation: pin versions, verify end-to-end in the compose stack
  before submission, and keep the BashOperator fallback ready.
- For only a handful of models it is arguably over-engineered; justified here because the
  role explicitly values platform best practices and scalability signals.

## Deliberately out of the build — production talking points

Options **3–5 (DockerOperator, KubernetesPodOperator, dbt Cloud)** are intentionally
**not built** in this take-home. They are excellent talking points for the call — *"here's
how this scales to production"* — without adding cost or fragility to a laptop-first,
`docker-compose up` deliverable:

- **DockerOperator** → the first step toward container-per-run isolation once we're off a
  single compose host.
- **KubernetesPodOperator** (or Cosmos' Kubernetes execution mode) → the production
  scaling path: each dbt run as an isolated, horizontally scalable pod.
- **dbt Cloud** → the "buy vs. build" option — offload execution, scheduling, and docs to
  a managed service if the team prefers.

The chosen design (Cosmos + isolated venv) is deliberately a **drop-in on-ramp** to these:
moving to option 3 or 4 later is a change of Cosmos execution mode, not a re-architecture.

## Follow-ups

- Pin compatible Airflow ↔ Cosmos ↔ dbt-postgres versions (plan 01).
- Wire the Cosmos-rendered dbt task group into the DAG (plan 04).
- Revisit `KubernetesPodOperator` / Cosmos k8s mode as the production scaling path
  (plan 07 trade-offs writeup).
