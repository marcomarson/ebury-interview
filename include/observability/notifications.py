"""Alerting framework.

A pluggable notifier: builds a structured alert and sends it to a webhook when
`ALERT_WEBHOOK_URL` is set (Slack/Teams incoming-webhook shape), otherwise logs a
structured line. Alerting must NEVER crash the task, so all transport errors are swallowed.
The transport is the only swappable part — DAG code just wires the callbacks.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

log = logging.getLogger(__name__)

WEBHOOK_ENV = "ALERT_WEBHOOK_URL"


def build_alert(context: dict) -> dict:
    """Extract a structured alert payload from an Airflow callback context."""
    ti = context.get("task_instance")
    dag = context.get("dag")
    exc = context.get("exception")
    return {
        "event": context.get("_alert_event", "task_failed"),
        "dag_id": getattr(ti, "dag_id", None) or getattr(dag, "dag_id", None),
        "task_id": getattr(ti, "task_id", None),
        "run_id": context.get("run_id"),
        "try_number": getattr(ti, "try_number", None),
        "exception": str(exc) if exc else None,
        "log_url": getattr(ti, "log_url", None),
    }


def _format_text(payload: dict) -> str:
    return (
        f":rotating_light: *{payload.get('event')}* "
        f"dag=`{payload.get('dag_id')}` task=`{payload.get('task_id')}` "
        f"run=`{payload.get('run_id')}` try={payload.get('try_number')}"
        + (f"\n{payload['exception']}" if payload.get("exception") else "")
    )


def send_alert(payload: dict) -> None:
    """POST to the webhook if configured, else log. Never raises."""
    webhook = os.environ.get(WEBHOOK_ENV, "").strip()
    if not webhook:
        log.warning("ALERT %s", json.dumps(payload))
        return
    body = json.dumps({"text": _format_text(payload)}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)  # noqa: S310 (trusted, operator-provided URL)
        log.info("Alert posted to webhook: event=%s", payload.get("event"))
    except Exception as exc:  # noqa: BLE001 — alerting must never crash the task
        log.error("Failed to POST alert (%s); payload=%s", exc, json.dumps(payload))


# --- Airflow callbacks -------------------------------------------------------

def on_failure_callback(context: dict) -> None:
    send_alert(build_alert({**context, "_alert_event": "task_failed"}))


def on_retry_callback(context: dict) -> None:
    send_alert(build_alert({**context, "_alert_event": "task_retry"}))


def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    send_alert(
        {
            "event": "sla_miss",
            "dag_id": getattr(dag, "dag_id", None),
            "task_id": ",".join(sorted({getattr(s, "task_id", "") for s in slas})),
            "run_id": None,
            "try_number": None,
            "exception": None,
            "log_url": None,
        }
    )
