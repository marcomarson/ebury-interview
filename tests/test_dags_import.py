"""Unit tests for DAG integrity (plan 01).

Run inside the Airflow image (which has Airflow installed):
    docker compose run --rm airflow-scheduler bash -c "cd /opt/airflow && pytest tests -q"
"""
import os

from airflow.models import DagBag

DAGS_FOLDER = os.environ.get("AIRFLOW__CORE__DAGS_FOLDER", "/opt/airflow/dags")


def _dagbag() -> DagBag:
    return DagBag(dag_folder=DAGS_FOLDER, include_examples=False)


def test_dagbag_imports_without_errors():
    """All DAGs parse with zero import errors."""
    dagbag = _dagbag()
    assert dagbag.import_errors == {}, f"DAG import errors: {dagbag.import_errors}"


def test_skeleton_dag_present_and_structured():
    """The walking-skeleton DAG exists with the expected tasks."""
    dag = _dagbag().get_dag("skeleton_healthcheck")
    assert dag is not None, "skeleton_healthcheck DAG not found"
    expected = {"start", "check_cosmos_available", "dbt_debug", "end"}
    assert expected.issubset(set(dag.task_ids)), (
        f"missing tasks: {expected - set(dag.task_ids)}"
    )
