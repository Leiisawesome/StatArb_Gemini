from __future__ import annotations

import json
from datetime import date, datetime, timezone

from l1_microstructure.production.ledger import OperationalLedger
from l1_microstructure.production.paper_qualification import (
    PAPER_QUALIFICATION_FAILURE_EXIT_CODE,
    PAPER_QUALIFICATION_SUCCESS_EXIT_CODE,
    PaperQualificationPolicy,
    PaperSessionEvaluator,
    main,
)


def _timestamp(day: date, hour: int, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc).isoformat()


def _seed_session(
    ledger: OperationalLedger,
    day: date,
    *,
    submitted_ids: list[str] | None = None,
    incident: bool = False,
    positions: dict[str, float] | None = None,
) -> None:
    session_date = day.isoformat()
    ledger.append_event(
        "session",
        "started",
        {"session_date": session_date, "mode": "paper", "symbols": ["AAPL"]},
        timestamp=_timestamp(day, 13),
    )
    ledger.append_event(
        "market",
        "framework_update",
        {
            "symbol": "AAPL",
            "timestamp_ns": 1,
            "state": "state",
            "regime": "neutral",
            "intent": None,
            "submitted_client_order_ids": list(submitted_ids or []),
        },
        timestamp=_timestamp(day, 14),
    )
    if incident:
        ledger.append_event(
            "incident",
            "runtime_halted",
            {"reason": "qualification failure", "alert": {"code": "runtime_halted"}},
            timestamp=_timestamp(day, 15),
        )
    ledger.append_event(
        "session",
        "closed",
        {
            "session_date": session_date,
            "timestamp_ns": 2,
            "session_phase": "closed",
            "mode": "paper",
            "symbols": ["AAPL"],
            "positions": dict(positions or {}),
            "open_orders": [],
        },
        timestamp=_timestamp(day, 20),
    )


def _business_days() -> list[date]:
    return [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),
        date(2026, 6, 8),
        date(2026, 6, 9),
        date(2026, 6, 10),
        date(2026, 6, 11),
        date(2026, 6, 12),
    ]


def test_paper_qualification_requires_ten_trailing_passing_sessions(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    evaluator = PaperSessionEvaluator(ledger)
    for day in _business_days():
        _seed_session(ledger, day)
        evaluation = evaluator.evaluate_and_record(day)
        assert evaluation.passed is True

    report = evaluator.report()

    assert report.qualified is True
    assert report.trailing_passing_sessions == 10
    assert report.to_dict()["status"] == "qualified"
    ledger.close()


def test_paper_qualification_counts_batched_and_legacy_framework_evidence(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    day = _business_days()[0]
    _seed_session(ledger, day)
    ledger.append_event(
        "market",
        "framework_update",
        {
            "symbol": "AAPL",
            "timestamp_ns": 2,
            "state": "state",
            "regime": "neutral",
            "intent": None,
            "submitted_client_order_ids": [],
            "update_count": 249,
        },
        timestamp=_timestamp(day, 14, 1),
    )

    evaluation = PaperSessionEvaluator(ledger).evaluate_and_record(day)

    assert evaluation.passed is True
    assert evaluation.metrics["framework_update_count"] == 250
    activity_check = {check.code: check for check in evaluation.checks}["market.activity_recorded"]
    assert activity_check.details["framework_update_count"] == 250
    ledger.close()


def test_failed_or_unfinalized_attempt_breaks_trailing_streak(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    evaluator = PaperSessionEvaluator(ledger, PaperQualificationPolicy(required_consecutive_sessions=2))
    days = _business_days()[:4]
    _seed_session(ledger, days[0])
    evaluator.evaluate_and_record(days[0])
    _seed_session(ledger, days[1], incident=True)
    evaluator.evaluate_and_record(days[1])
    _seed_session(ledger, days[2])
    evaluator.evaluate_and_record(days[2])
    ledger.append_event(
        "session",
        "started",
        {"session_date": days[3].isoformat(), "mode": "paper", "symbols": ["AAPL"]},
        timestamp=_timestamp(days[3], 13),
    )

    report = evaluator.report()

    assert report.qualified is False
    assert report.trailing_passing_sessions == 0
    assert report.sessions[-1].session_date == days[3].isoformat()
    assert {check.code: check for check in report.sessions[-1].checks}["session.close_marker"].passed is False
    ledger.close()


def test_paper_session_reconciles_complete_order_audit_chain(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    day = _business_days()[0]
    _seed_session(ledger, day, submitted_ids=["client-1"])
    ledger.record_order_intent({"symbol": "AAPL"}, "client-1", timestamp=_timestamp(day, 14, 1))
    ledger.update_order(
        "client-1",
        "filled",
        external_order_id="external-1",
        timestamp=_timestamp(day, 14, 2),
    )
    ledger.append_event(
        "order",
        "route_acknowledgement",
        {"client_order_id": "client-1", "external_order_id": "external-1", "status": "accepted"},
        timestamp=_timestamp(day, 14, 2),
    )
    ledger.append_event(
        "order",
        "execution_report",
        {"client_order_id": "client-1", "external_order_id": "external-1", "status": "filled"},
        timestamp=_timestamp(day, 14, 3),
    )

    evaluation = PaperSessionEvaluator(ledger).evaluate(day)

    assert evaluation.passed is True
    checks = {check.code: check for check in evaluation.checks}
    assert checks["audit.decisions_complete"].passed is True
    assert checks["audit.acknowledgements_complete"].passed is True
    assert checks["fills.reconciled"].passed is True
    ledger.close()


def test_paper_session_detects_order_audit_and_position_failures(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    day = _business_days()[0]
    _seed_session(ledger, day, submitted_ids=["client-1", "missing-client"], positions={"AAPL": 1.0})
    for client_id in ("client-1", "client-2"):
        ledger.record_order_intent({"symbol": "AAPL"}, client_id, timestamp=_timestamp(day, 14, 1))
        ledger.update_order(
            client_id,
            "filled" if client_id == "client-1" else "accepted",
            external_order_id="duplicate-external",
            timestamp=_timestamp(day, 14, 2),
        )
    ledger.append_event(
        "order",
        "execution_report",
        {"client_order_id": None, "external_order_id": "duplicate-external", "status": "filled"},
        timestamp=_timestamp(day, 14, 3),
    )

    evaluation = PaperSessionEvaluator(ledger).evaluate(day)
    checks = {check.code: check for check in evaluation.checks}

    assert evaluation.passed is False
    assert checks["orders.unique_external_ids"].passed is False
    assert checks["orders.all_terminal"].passed is False
    assert checks["fills.reconciled"].passed is False
    assert checks["positions.flat_at_close"].passed is False
    assert checks["audit.decisions_complete"].details["unresolved_client_order_ids"] == ["missing-client"]
    ledger.close()


def test_paper_qualification_cli_reports_qualified_ledger(tmp_path, capsys) -> None:
    path = tmp_path / "runtime.sqlite3"
    ledger = OperationalLedger(path)
    evaluator = PaperSessionEvaluator(ledger)
    for day in _business_days():
        _seed_session(ledger, day)
        evaluator.evaluate_and_record(day)
    ledger.close()

    exit_code = main(["--database", str(path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == PAPER_QUALIFICATION_SUCCESS_EXIT_CODE
    assert payload["qualified"] is True
    assert payload["trailing_passing_sessions"] == 10


def test_paper_qualification_cli_finalizes_fail_closed_and_redacts_errors(tmp_path, capsys) -> None:
    path = tmp_path / "runtime.sqlite3"

    exit_code = main(["--database", str(path), "--finalize", "2026-06-01"])
    first_output = capsys.readouterr().out
    first_payload = json.loads(first_output)
    assert exit_code == PAPER_QUALIFICATION_FAILURE_EXIT_CODE
    assert first_payload["sessions"][0]["status"] == "failed"

    exit_code = main(["--database", str(path), "--finalize", "not-a-date"])
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == PAPER_QUALIFICATION_FAILURE_EXIT_CODE
    assert payload["error"]["error_type"] == "ValueError"
    assert "Invalid isoformat" not in output
