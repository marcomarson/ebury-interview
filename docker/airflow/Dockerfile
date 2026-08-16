# Custom Airflow image for the Ebury pipeline.
#
# Design point (ADR 0001): dbt runs from an ISOLATED virtualenv so its dependencies
# never collide with Airflow's. Cosmos — which renders dbt models as Airflow tasks —
# is installed into the Airflow environment and invokes the dbt executable from that
# separate venv (/opt/dbt-venv).
ARG AIRFLOW_VERSION=2.9.3
ARG PYTHON_VERSION=3.11
FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

# Re-declare after FROM so they're usable in the build below.
ARG AIRFLOW_VERSION
ARG PYTHON_VERSION

# --- Cosmos + test tooling in the Airflow environment (constraint-pinned) ---
# Installed as the default `airflow` user, into Airflow's own site-packages.
RUN pip install --no-cache-dir \
      "astronomer-cosmos==1.7.1" \
      "apache-airflow-providers-postgres" \
      "pytest" \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# --- dbt in a dedicated, isolated virtualenv (root to create /opt, then drop back) ---
# NOTE: dbt-core is pinned EXPLICITLY to a stable classic release. Without this pin,
# dbt-postgres resolves dbt-core to the 2.0 "Fusion" pre-release, which does not support
# the Postgres adapter. We deliberately stay on the classic (Python) dbt engine.
ENV DBT_VENV=/opt/dbt-venv
USER root
# git is used by dbt (e.g. `dbt deps` for packages) and checked by `dbt debug`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*
RUN python -m venv "${DBT_VENV}" \
 && "${DBT_VENV}/bin/pip" install --no-cache-dir --upgrade pip \
 && "${DBT_VENV}/bin/pip" install --no-cache-dir \
      "dbt-core==1.9.11" \
      "dbt-postgres==1.9.1"
USER airflow

# Reusable code (ingestion package, SQL) importable from anywhere via PYTHONPATH.
ENV PYTHONPATH=/opt/airflow/include

# Bake the project into the image so it's a self-contained, prod-ready artifact
# (ADR 0004). In LOCAL dev the docker-compose bind mounts override these paths for
# fast iteration (edit -> rerun, no rebuild); the baked copy is what ships to prod.
COPY --chown=airflow:0 dags/ /opt/airflow/dags/
COPY --chown=airflow:0 dbt/ /opt/airflow/dbt/
COPY --chown=airflow:0 include/ /opt/airflow/include/
