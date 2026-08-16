"""Raw ingestion DAG (plan 02).

    acquire_source -> create_raw_table -> load_raw -> reconcile_rowcount

Lands customer_transactions.csv into raw.customer_transactions as-is (all TEXT) via a
streaming COPY. Cleaning/modelling happen later in dbt (plans 03-04, wired via Cosmos).
"""
from __future__ import annotations

import logging
from datetime import timedelta

import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from ingestion.load_raw import count_data_rows, load_csv, reconcile, validate_header

SOURCE_FILE = "/opt/airflow/data/customer_transactions.csv"
DDL_FILE = "/opt/airflow/include/sql/create_raw_customer_transactions.sql"
RAW_TABLE = "raw.customer_transactions"
CONN_ID = "warehouse"

log = logging.getLogger(__name__)


def _notify_failure(context) -> None:
    """Failure hook stub. Full alerting (Slack/email) lands in plan 05."""
    ti = context.get("task_instance")
    log.error(
        "Ingestion task failed: task=%s run=%s",
        getattr(ti, "task_id", "?"),
        context.get("run_id"),
    )


default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": _notify_failure,
}


def _acquire_source() -> None:
    validate_header(SOURCE_FILE)  # confirms existence + header shape
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


with DAG(
    dag_id="customer_transactions_ingestion",
    schedule=None,
    start_date=pendulum.datetime(2023, 7, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    tags=["ingestion", "plan-02"],
    doc_md=__doc__,
) as dag:
    acquire_source = PythonOperator(task_id="acquire_source", python_callable=_acquire_source)
    create_raw_table = PythonOperator(task_id="create_raw_table", python_callable=_create_raw_table)
    load_raw = PythonOperator(task_id="load_raw", python_callable=_load_raw)
    reconcile_rowcount = PythonOperator(task_id="reconcile_rowcount", python_callable=_reconcile)

    acquire_source >> create_raw_table >> load_raw >> reconcile_rowcount
