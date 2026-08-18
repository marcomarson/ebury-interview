# Architecture Decision Records (ADRs)

Each ADR captures one significant decision — the context, the options considered, the
choice made, and its consequences/trade-offs. They are immutable once accepted (superseded
rather than edited). This index is the running list; the **plan 07 trade-offs writeup**
consolidates them into a single architecture-and-decisions narrative for submission.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-dbt-orchestration.md) | Orchestrating dbt from Airflow → **Astronomer Cosmos** (isolated venv); Docker/K8s/dbt-Cloud kept as prod talking points | Accepted |
| [0002](0002-configuration-and-secrets.md) | Configuration & secrets → inline `${VAR:-default}` for local dev; **.env / cloud secrets manager** for real deployments | Accepted |
| [0003](0003-pin-classic-dbt-engine.md) | Pin **classic `dbt-core`** (Postgres-supporting) instead of the dbt Fusion 2.0 pre-release | Accepted |
| [0004](0004-project-code-baked-into-image.md) | **Bake dags/dbt into the image** (self-contained artifact); bind mounts override for local dev | Accepted |
| [0005](0005-data-quality-strategy.md) | **Data-quality strategy**: coerce / quarantine (broken measure) / flag; no word→number; `tax` is absolute | Accepted |
