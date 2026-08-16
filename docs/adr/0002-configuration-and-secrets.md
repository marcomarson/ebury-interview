# ADR 0002 — Configuration & secrets management

- **Status:** Accepted
- **Date:** 2026-08-16
- **Deciders:** Marco Marson (with Claude)
- **Context tags:** configuration, secrets, security, docker-compose

## Context

The stack needs configuration values — Postgres credentials/db name, Airflow admin
login, Airflow Fernet/secret keys, and host ports. For a `docker-compose up` take-home
the priorities are: (a) it runs with **zero setup steps**, and (b) we don't bake real
secrets into committed files. These two pull in opposite directions.

## Decision

For **local development**, inline **non-sensitive defaults directly in
`docker-compose.yml`** using `${VAR:-default}` syntax, e.g.:

```yaml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
  POSTGRES_DB: ${POSTGRES_DB:-ebury}
ports:
  - "${POSTGRES_PORT:-5432}:5432"
```

- The stack runs immediately — **no `.env` file is required**.
- A small, committed **`.env.example`** documents which values are overridable; the real
  `.env` remains gitignored. Nothing here is a real credential — they are throwaway local
  dev values.
- If a reviewer needs to override (e.g. a port clash), they create a `.env`; otherwise the
  defaults apply.

**This is explicitly a local-development convenience, not a production pattern.**

## In a real application (production path)

The credentials above must **never** be committed or defaulted in source. In production
they would come from a dedicated secret store, injected at runtime, e.g.:

- A `.env` / env vars supplied by the deployment platform (not committed), or
- A managed secrets service: **AWS Secrets Manager / SSM Parameter Store**,
  **GCP Secret Manager**, **Azure Key Vault**, or **HashiCorp Vault**, or
- Kubernetes **Secrets** (ideally backed by an external secrets operator),

with **rotation**, least-privilege access, and audit logging. Airflow connections/
variables would likewise be sourced from a secrets backend rather than plaintext.

## Consequences

**Positive**
- Frictionless first run (`docker-compose up`) — no "copy the env file" failure mode.
- No real secrets in the repo; `.env.example` signals the intended externalization.
- Clear, documented seam to swap local defaults for a secrets manager in production.

**Negative / risks**
- Default credentials live in committed YAML — acceptable **only** because they are
  local, throwaway values. This must not be mistaken for a deployable config.
- Slightly more `${VAR:-default}` verbosity in the compose file.

## Follow-ups

- Reference this local-vs-prod split in the plan 07 trade-offs writeup.
