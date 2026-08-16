"""Raw ingestion helpers for customer_transactions.

Design: land the CSV as-is (all TEXT) using a streaming Postgres COPY, so it stays
memory-flat regardless of file size and no dirty rows are lost. The load is idempotent
(TRUNCATE + COPY in one transaction). All logic lives here (not in the DAG) so it is
unit-testable and reusable.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

# The exact source columns, in order (metadata columns are populated separately).
EXPECTED_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "customer_id",
    "transaction_date",
    "product_id",
    "product_name",
    "quantity",
    "price",
    "tax",
)

DEFAULT_TABLE = "raw.customer_transactions"


def expected_columns() -> list[str]:
    return list(EXPECTED_COLUMNS)


def count_data_rows(path: str | Path) -> int:
    """Number of data rows (excludes the header). 0 for a header-only file."""
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        if next(reader, None) is None:
            return 0  # empty file, no header
        return sum(1 for _ in reader)


def validate_header(path: str | Path) -> None:
    """Raise if the file is missing, empty, or its header != EXPECTED_COLUMNS."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Source file not found: {p}")
    with p.open("r", encoding="utf-8", newline="") as f:
        header = next(csv.reader(f), None)
    if header is None:
        raise ValueError(f"Source file is empty (no header): {p}")
    normalized = [h.strip() for h in header]
    if normalized != list(EXPECTED_COLUMNS):
        raise ValueError(
            f"Header mismatch in {p}: expected {list(EXPECTED_COLUMNS)}, got {normalized}"
        )


def count_rows(hook, table: str = DEFAULT_TABLE) -> int:
    return int(hook.get_first(f"SELECT count(*) FROM {table}")[0])


def load_csv(hook, path: str | Path, table: str = DEFAULT_TABLE) -> int:
    """Idempotent streaming load: TRUNCATE + COPY + tag source file, in one transaction.

    Returns the number of rows in the table after loading.
    """
    p = Path(path)
    validate_header(p)  # also checks existence
    cols = ", ".join(EXPECTED_COLUMNS)
    copy_sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"

    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE {table}")
            with p.open("r", encoding="utf-8", newline="") as f:
                cur.copy_expert(copy_sql, f)
            cur.execute(
                f"UPDATE {table} SET _source_file = %s WHERE _source_file IS NULL",
                (p.name,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return count_rows(hook, table)


def reconcile(hook, path: str | Path, table: str = DEFAULT_TABLE) -> int:
    """Assert loaded row count == file data-row count. Returns the reconciled count."""
    expected = count_data_rows(path)
    loaded = count_rows(hook, table)
    if expected != loaded:
        raise ValueError(
            f"Reconciliation failed for {table}: file has {expected} data rows, "
            f"loaded {loaded}"
        )
    return loaded
