"""Tests for raw ingestion (plan 02).

Pure-helper tests need no database. Integration tests use the running warehouse via the
`warehouse` Airflow connection and a throwaway table, so they clean up after themselves.

    docker compose run --rm --entrypoint bash airflow-scheduler -lc "cd /opt/airflow && pytest tests -q"
"""
from __future__ import annotations

import uuid

import pytest

from ingestion.load_raw import (
    count_data_rows,
    expected_columns,
    load_csv,
    reconcile,
    validate_header,
)

DATA = "/opt/airflow/data/customer_transactions.csv"
HEADER = ",".join(expected_columns())


# --------------------------- pure helper (no DB) ---------------------------

def _write_csv(path, rows):
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return str(path)


def test_count_data_rows_excludes_header(tmp_path):
    p = _write_csv(tmp_path / "t.csv", ["1001,501,2023-07-11,101,Product A,1,10.0,1.0"])
    assert count_data_rows(p) == 1


def test_header_only_file_has_zero_rows(tmp_path):
    p = _write_csv(tmp_path / "h.csv", [])
    assert count_data_rows(p) == 0


def test_validate_header_accepts_expected(tmp_path):
    p = _write_csv(tmp_path / "ok.csv", [])
    validate_header(p)  # should not raise


def test_validate_header_rejects_mismatch(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_header(p)


def test_missing_file_fails_loudly():
    with pytest.raises(FileNotFoundError):
        load_csv(None, "/opt/airflow/data/does_not_exist.csv", "raw.nope")


# --------------------------- integration (DB) ---------------------------

@pytest.fixture
def temp_table():
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    hook = PostgresHook(postgres_conn_id="warehouse")
    name = f"raw.test_ingest_{uuid.uuid4().hex[:8]}"
    hook.run(
        f"""CREATE TABLE {name} (
            transaction_id text, customer_id text, transaction_date text,
            product_id text, product_name text, quantity text, price text, tax text,
            _ingested_at timestamptz NOT NULL DEFAULT now(), _source_file text
        )"""
    )
    try:
        yield hook, name
    finally:
        hook.run(f"DROP TABLE IF EXISTS {name}")


def test_load_counts_and_is_idempotent(temp_table):
    hook, name = temp_table
    assert load_csv(hook, DATA, name) == 100
    assert load_csv(hook, DATA, name) == 100  # re-run: no duplicates
    assert reconcile(hook, DATA, name) == 100


def test_dirty_values_land_verbatim(temp_table):
    hook, name = temp_table
    load_csv(hook, DATA, name)
    prices = {r[0] for r in hook.get_records(f"SELECT price FROM {name}")}
    tx_ids = {r[0] for r in hook.get_records(f"SELECT transaction_id FROM {name}")}
    product_ids = {r[0] for r in hook.get_records(f"SELECT product_id FROM {name}")}
    assert "Two Hundred" in prices              # word-valued number preserved
    assert "T1010" in tx_ids                     # prefixed id preserved
    assert "P100" in product_ids                 # prefixed id preserved


def test_nulls_and_source_file_metadata(temp_table):
    hook, name = temp_table
    load_csv(hook, DATA, name)
    # empty customer_id lands as NULL, not dropped
    null_customers = hook.get_first(f"SELECT count(*) FROM {name} WHERE customer_id IS NULL")[0]
    assert int(null_customers) > 0
    # lineage metadata populated
    src = hook.get_first(f"SELECT DISTINCT _source_file FROM {name}")[0]
    assert src == "customer_transactions.csv"


def test_reconcile_detects_mismatch(temp_table, tmp_path):
    hook, name = temp_table
    load_csv(hook, DATA, name)  # 100 rows loaded
    smaller = _write_csv(tmp_path / "small.csv", ["1001,501,2023-07-11,101,Product A,1,10,1"])
    with pytest.raises(ValueError):
        reconcile(hook, smaller, name)  # file has 1 row, table has 100
