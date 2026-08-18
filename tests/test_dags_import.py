"""Unit tests for DAG integrity.

Run inside the Airflow image (which has Airflow + Cosmos installed):
    docker compose run --rm --entrypoint bash airflow-scheduler -lc "cd /opt/airflow && pytest tests -q"
"""
import os

from airflow.models import DagBag

DAGS_FOLDER = os.environ.get("AIRFLOW__CORE__DAGS_FOLDER", "/opt/airflow/dags")


def _dagbag() -> DagBag:
    return DagBag(dag_folder=DAGS_FOLDER, include_examples=False)


def test_dagbag_imports_without_errors():
    """All DAGs import with zero errors (includes Cosmos rendering)."""
    dagbag = _dagbag()
    assert dagbag.import_errors == {}, f"DAG import errors: {dagbag.import_errors}"


def test_pipeline_dag_present_and_structured():
    """The pipeline DAG exists with the ingestion tasks and a rendered dbt task group."""
    dag = _dagbag().get_dag("customer_transactions_pipeline")
    assert dag is not None, "customer_transactions_pipeline DAG not found"
    task_ids = set(dag.task_ids)
    ingestion = {"acquire_source", "create_raw_table", "load_raw", "reconcile_rowcount"}
    assert ingestion.issubset(task_ids), f"missing ingestion tasks: {ingestion - task_ids}"
    # Cosmos renders each dbt model/test as a task under the dbt_transform group.
    assert any(t.startswith("dbt_transform.") for t in task_ids), "no dbt_transform tasks rendered"
