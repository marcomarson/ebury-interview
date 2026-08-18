"""Pure data-quality evaluation logic (no IO, easy to unit test).

The DAG queries the warehouse and passes the numbers here; this decides which alert
events to raise. Keeping the decision pure separates policy from plumbing.
"""
from __future__ import annotations

DEFAULT_QUARANTINE_ALERT_PCT = 40.0


def evaluate_dq(
    rows_received: int,
    rows_modelled: int,
    rows_quarantined: int,
    quarantine_pct: float,
    threshold_pct: float = DEFAULT_QUARANTINE_ALERT_PCT,
) -> list[str]:
    """Return the alert event codes warranted by the DQ numbers (empty = all good)."""
    events: list[str] = []
    if rows_modelled + rows_quarantined != rows_received:
        events.append("dq_reconcile_failed")
    if quarantine_pct > threshold_pct:
        events.append("dq_quarantine_high")
    return events
