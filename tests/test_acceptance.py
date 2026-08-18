"""Acceptance criteria (plan 06) — asserts the post-pipeline warehouse end-state.

Requires the pipeline to have run (marts populated). Run via:
    make verify
    # or:
    docker compose run --rm --entrypoint bash airflow-scheduler -lc \
        "cd /opt/airflow && pytest tests -q -m acceptance"
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.acceptance


@pytest.fixture(scope="module")
def hook():
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    return PostgresHook(postgres_conn_id="warehouse")


def _scalar(hook, sql):
    return hook.get_first(sql)[0]


def test_partition_sizes(hook):
    assert _scalar(hook, "SELECT count(*) FROM raw.customer_transactions") == 100
    assert _scalar(hook, "SELECT count(*) FROM analytics.fct_transactions") == 71
    assert _scalar(hook, "SELECT count(*) FROM analytics.quarantine_customer_transactions") == 29


def test_partitions_reconcile(hook):
    assert _scalar(hook, "SELECT reconciles FROM analytics.dq_completeness") is True


def test_no_duplicate_fact_pk(hook):
    dupes = _scalar(
        hook,
        "SELECT count(*) FROM (SELECT transaction_id FROM analytics.fct_transactions "
        "GROUP BY 1 HAVING count(*) > 1) d",
    )
    assert dupes == 0


def test_total_amount_formula(hook):
    violations = _scalar(
        hook,
        "SELECT count(*) FROM analytics.fct_transactions "
        "WHERE total_amount <> quantity * unit_price + tax_amount",
    )
    assert violations == 0


def test_referential_integrity(hook):
    for dim, key in [("dim_product", "product_id"), ("dim_customer", "customer_id"), ("dim_date", "date_key")]:
        orphans = _scalar(
            hook,
            f"SELECT count(*) FROM analytics.fct_transactions f "
            f"LEFT JOIN analytics.{dim} d USING ({key}) WHERE d.{key} IS NULL",
        )
        assert orphans == 0, f"{dim}: {orphans} orphan fact rows"


def test_dimension_counts(hook):
    assert _scalar(hook, "SELECT count(*) FROM analytics.dim_product") == 5
    assert _scalar(hook, "SELECT count(*) FROM analytics.dim_customer") == 11
    assert _scalar(hook, "SELECT count(*) FROM analytics.dim_customer WHERE is_unknown") == 1


def test_audit_present(hook):
    assert _scalar(hook, "SELECT count(*) FROM analytics.dq_run_audit") >= 1


def test_revenue_shares_sum_to_100(hook):
    total = _scalar(hook, "SELECT round(sum(revenue_share_pct), 1) FROM analytics.agg_sales_by_product")
    assert abs(float(total) - 100.0) < 0.5, f"revenue shares sum to {total}, expected ~100"
