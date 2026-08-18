"""Customer transactions pipeline (plan 04).

    acquire_source -> create_raw_table -> load_raw -> reconcile_rowcount
        -> [dbt_transform: staging -> intermediate -> marts -> tests]  (via Cosmos)

One DAG that ingests the raw CSV and then triggers dbt to build the dimensional model,
per the brief. dbt runs from its isolated venv; Cosmos renders each dbt model/test as its
own Airflow task (ADR 0001).
"""
from __future__ import annotations

import logging
import os
from datetime import timedelta

import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import ExecutionMode, LoadMode

from ingestion.load_raw import count_data_rows, load_csv, reconcile, validate_header
from observability.dq import evaluate_dq
from observability.notifications import (
    on_failure_callback,
    on_retry_callback,
    send_alert,
    sla_miss_callback,
)

SOURCE_FILE = "/opt/airflow/data/customer_transactions.csv"
DDL_FILE = "/opt/airflow/include/sql/create_raw_customer_transactions.sql"
RAW_TABLE = "raw.customer_transactions"
CONN_ID = "warehouse"

DBT_PROJECT_DIR = "/opt/airflow/dbt/ebury"
DBT_EXECUTABLE = "/opt/dbt-venv/bin/dbt"

log = logging.getLogger(__name__)


default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
    "on_failure_callback": on_failure_callback,
    "on_retry_callback": on_retry_callback,
}


def _acquire_source() -> None:
    validate_header(SOURCE_FILE)
    log.info("Source acquired: %s (%d data rows)", SOURCE_FILE, count_data_rows(SOURCE_FILE))


def _create_raw_table() -> None:
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    with open(DDL_FILE, "r", encoding="utf-8") as f:
        hook.run(f.read())


def _load_raw() -> None:
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    log.info("Loaded %d rows into %s", load_csv(hook, SOURCE_FILE, RAW_TABLE), RAW_TABLE)


def _reconcile() -> None:
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    log.info("Reconciliation OK: %d rows", reconcile(hook, SOURCE_FILE, RAW_TABLE))


def _dq_report() -> None:
    """Log a DQ summary after dbt, and alert if the quarantine rate exceeds a threshold."""
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    received, modelled, quarantined, pct, reconciles = hook.get_first(
        "SELECT rows_received, rows_modelled, rows_quarantined, quarantine_pct, reconciles "
        "FROM analytics.dq_completeness"
    )
    log.info(
        "DQ report: received=%s modelled=%s quarantined=%s (%s%%) reconciles=%s",
        received, modelled, quarantined, pct, reconciles,
    )
    for reason, n in hook.get_records(
        "SELECT dq_reason, count(*) FROM analytics.dq_quarantine_reasons GROUP BY 1 ORDER BY 2 DESC"
    ):
        log.info("  quarantine reason %s: %s", reason, n)

    threshold = float(os.environ.get("DQ_QUARANTINE_ALERT_PCT", "40"))
    for event in evaluate_dq(int(received), int(modelled), int(quarantined), float(pct), threshold):
        send_alert(
            {
                "event": event,
                "dag_id": "customer_transactions_pipeline",
                "task_id": "dq_report",
                "run_id": None,
                "try_number": None,
                "exception": f"quarantine_pct={pct} threshold={threshold}",
                "log_url": None,
            }
        )


# --- Cosmos config: run dbt from the isolated venv; packages are baked (no deps at parse) ---
profile_config = ProfileConfig(
    profile_name="ebury",
    target_name="dev",
    profiles_yml_filepath=f"{DBT_PROJECT_DIR}/profiles.yml",
)
project_config = ProjectConfig(dbt_project_path=DBT_PROJECT_DIR)
execution_config = ExecutionConfig(
    dbt_executable_path=DBT_EXECUTABLE,
    execution_mode=ExecutionMode.LOCAL,
)
render_config = RenderConfig(
    dbt_executable_path=DBT_EXECUTABLE,
    load_method=LoadMode.DBT_LS,
    # Cosmos runs `dbt ls` in an isolated tmp copy that lacks the baked dbt_packages,
    # so it installs deps at render (and at execution via operator_args below).
    dbt_deps=True,
)


with DAG(
    dag_id="customer_transactions_pipeline",
    schedule=None,
    start_date=pendulum.datetime(2023, 7, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=sla_miss_callback,
    tags=["pipeline", "plan-04", "plan-05"],
    doc_md=__doc__,
) as dag:
    acquire_source = PythonOperator(task_id="acquire_source", python_callable=_acquire_source)
    create_raw_table = PythonOperator(task_id="create_raw_table", python_callable=_create_raw_table)
    load_raw = PythonOperator(
        task_id="load_raw", python_callable=_load_raw, sla=timedelta(minutes=30)
    )
    reconcile_rowcount = PythonOperator(task_id="reconcile_rowcount", python_callable=_reconcile)

    dbt_transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=project_config,
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=render_config,
        # No per-task `dbt deps`: LOCAL execution runs in the project dir where packages
        # are baked (Dockerfile `dbt deps`). Only the render step installs deps (once).
    )

    dq_report = PythonOperator(task_id="dq_report", python_callable=_dq_report)

    acquire_source >> create_raw_table >> load_raw >> reconcile_rowcount >> dbt_transform >> dq_report
