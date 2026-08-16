"""Walking-skeleton DAG (plan 01).

Proves the infrastructure works end-to-end before any real logic exists:

    start -> check_cosmos_available -> dbt_debug -> end

- check_cosmos_available: imports Cosmos to confirm it's installed in Airflow's env.
- dbt_debug: runs dbt from its ISOLATED venv against the warehouse, proving the
  scheduler can invoke dbt and dbt can reach Postgres.

Replaced in plan 04 by a Cosmos-rendered dbt task group.
"""
from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

DBT_DIR = "/opt/airflow/dbt/ebury"
DBT_BIN = "/opt/dbt-venv/bin/dbt"


def _check_cosmos_available() -> str:
    """Fail loudly if Cosmos isn't importable in the Airflow environment."""
    import cosmos  # noqa: F401

    return getattr(cosmos, "__version__", "unknown")


with DAG(
    dag_id="skeleton_healthcheck",
    schedule=None,
    start_date=pendulum.datetime(2023, 7, 1, tz="UTC"),
    catchup=False,
    tags=["skeleton", "plan-01"],
    doc_md=__doc__,
) as dag:
    start = EmptyOperator(task_id="start")

    check_cosmos = PythonOperator(
        task_id="check_cosmos_available",
        python_callable=_check_cosmos_available,
    )

    dbt_debug = BashOperator(
        task_id="dbt_debug",
        bash_command=f"{DBT_BIN} debug --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    end = EmptyOperator(task_id="end")

    start >> check_cosmos >> dbt_debug >> end
