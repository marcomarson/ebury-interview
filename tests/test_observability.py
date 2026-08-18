"""Tests for the observability framework (plan 05)."""
from __future__ import annotations

import json

import pytest

from observability import notifications
from observability.dq import evaluate_dq


# --------------------------- alert payload ---------------------------

class _TI:
    dag_id = "d"
    task_id = "t"
    try_number = 2
    log_url = "http://logs/1"


def test_build_alert_shape():
    payload = notifications.build_alert(
        {"task_instance": _TI(), "run_id": "r1", "exception": ValueError("boom")}
    )
    assert payload["dag_id"] == "d"
    assert payload["task_id"] == "t"
    assert payload["run_id"] == "r1"
    assert payload["try_number"] == 2
    assert "boom" in payload["exception"]
    assert payload["event"] == "task_failed"


# --------------------------- transport ---------------------------

def test_send_alert_logs_when_no_webhook(monkeypatch, caplog):
    monkeypatch.delenv(notifications.WEBHOOK_ENV, raising=False)
    with caplog.at_level("WARNING"):
        notifications.send_alert({"event": "task_failed", "dag_id": "d"})
    assert any("ALERT" in r.message for r in caplog.records)


def test_send_alert_posts_when_webhook_set(monkeypatch):
    monkeypatch.setenv(notifications.WEBHOOK_ENV, "http://hook.local/x")
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return _Resp()

    monkeypatch.setattr(notifications.urllib.request, "urlopen", fake_urlopen)
    notifications.send_alert({"event": "task_failed", "dag_id": "d", "task_id": "t"})
    assert captured["url"] == "http://hook.local/x"
    assert "task_failed" in captured["body"]["text"]


def test_send_alert_swallows_webhook_errors(monkeypatch):
    monkeypatch.setenv(notifications.WEBHOOK_ENV, "http://hook.local/x")

    def boom(req, timeout=0):
        raise OSError("network down")

    monkeypatch.setattr(notifications.urllib.request, "urlopen", boom)
    # must not raise
    notifications.send_alert({"event": "task_failed"})


# --------------------------- DQ evaluation ---------------------------

def test_evaluate_dq_clean_under_threshold():
    assert evaluate_dq(100, 71, 29, 29.0, threshold_pct=40) == []


def test_evaluate_dq_over_threshold():
    assert "dq_quarantine_high" in evaluate_dq(100, 40, 60, 60.0, threshold_pct=40)


def test_evaluate_dq_reconcile_failure():
    # modelled + quarantined != received
    assert "dq_reconcile_failed" in evaluate_dq(100, 71, 20, 20.0, threshold_pct=40)
