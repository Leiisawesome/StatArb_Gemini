from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from l1_microstructure.production import OperationalLedger
from l1_microstructure.production.transparent_qualification import (
    TRANSPARENT_QUALIFICATION_SUCCESS_EXIT_CODE,
    TransparentCampaignEvaluator,
    TransparentCampaignPolicy,
    main,
)


def _record_session(
    ledger: OperationalLedger,
    session_date: str,
    *,
    fingerprint: str = "config-and-artifacts-v2",
    candidate_errors: int = 0,
) -> None:
    timestamp = datetime.fromisoformat(f"{session_date}T12:00:00").replace(
        tzinfo=ZoneInfo("America/New_York")
    ).astimezone(ZoneInfo("UTC")).isoformat()
    common = {
        "session_date": session_date,
        "mode": "paper",
        "engine_version": "v2",
        "routing_engine_version": "v1",
        "campaign_fingerprint": fingerprint,
        "promoted_run_ids": {"AAPL": "aapl-v2-approved"},
    }
    ledger.append_event("session", "started", common, timestamp=timestamp)
    ledger.append_event(
        "market",
        "framework_update",
        {"symbol": "AAPL", "submitted_client_order_ids": []},
        timestamp=timestamp,
    )
    ledger.append_event(
        "model",
        "transparent_shadow_summary",
        {
            "validation_passed": True,
            "engine_version": "v2",
            "routing_engine_version": "v1",
            "campaign_fingerprint": fingerprint,
            "promoted_run_ids": {"AAPL": "aapl-v2-approved"},
            "candidate_update_count": 100,
            "resolved_outcome_count": 25,
            "candidate_error_count": candidate_errors,
            "baseline_p95_latency_ns": 100.0,
            "candidate_p95_latency_ns": 110.0,
        },
        timestamp=timestamp,
    )
    ledger.append_event(
        "session",
        "closed",
        {**common, "session_phase": "closed", "positions": {}, "open_orders": []},
        timestamp=timestamp,
    )


def test_transparent_campaign_requires_consecutive_frozen_v2_sessions(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "ledger.sqlite3")
    try:
        _record_session(ledger, "2026-07-13")
        _record_session(ledger, "2026-07-14")
        evaluator = TransparentCampaignEvaluator(
            ledger,
            TransparentCampaignPolicy(required_consecutive_sessions=2),
        )
        evaluator.evaluate_and_record("2026-07-13")
        evaluator.evaluate_and_record("2026-07-14")

        report = evaluator.report()

        assert report.qualified
        assert report.trailing_passing_sessions == 2
        assert report.frozen_fingerprint == "config-and-artifacts-v2"
    finally:
        ledger.close()


def test_transparent_campaign_resets_streak_on_fingerprint_change_or_error(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "ledger.sqlite3")
    try:
        _record_session(ledger, "2026-07-10", fingerprint="old")
        _record_session(ledger, "2026-07-13", fingerprint="new")
        _record_session(ledger, "2026-07-14", fingerprint="new", candidate_errors=1)
        evaluator = TransparentCampaignEvaluator(
            ledger,
            TransparentCampaignPolicy(required_consecutive_sessions=2),
        )
        for day in ("2026-07-10", "2026-07-13", "2026-07-14"):
            evaluator.evaluate_and_record(day)

        report = evaluator.report()

        assert not report.qualified
        assert report.trailing_passing_sessions == 0
        assert not report.sessions[-1].passed
    finally:
        ledger.close()


def test_transparent_campaign_cli_reports_qualified_frozen_ledger(tmp_path, capsys) -> None:
    database = tmp_path / "ledger.sqlite3"
    ledger = OperationalLedger(database)
    try:
        evaluator = TransparentCampaignEvaluator(ledger)
        business_days = (
            "2026-06-26",
            "2026-06-29",
            "2026-06-30",
            "2026-07-01",
            "2026-07-02",
            "2026-07-06",
            "2026-07-07",
            "2026-07-08",
            "2026-07-09",
            "2026-07-10",
        )
        for session_date in business_days:
            _record_session(ledger, session_date)
            evaluator.evaluate_and_record(session_date)
    finally:
        ledger.close()

    exit_code = main(["--database", str(database)])

    assert exit_code == TRANSPARENT_QUALIFICATION_SUCCESS_EXIT_CODE
    assert '"qualified": true' in capsys.readouterr().out


def test_transparent_campaign_rejects_mid_session_shadow_restart(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "ledger.sqlite3")
    try:
        _record_session(ledger, "2026-07-14")
        ledger.append_event(
            "model",
            "transparent_shadow_restart",
            {"session_date": "2026-07-14", "campaign_fingerprint": "config-and-artifacts-v2"},
            timestamp="2026-07-14T17:00:00+00:00",
        )

        evaluation = TransparentCampaignEvaluator(ledger).evaluate("2026-07-14")

        assert not evaluation.passed
        assert not next(check for check in evaluation.checks if check.code == "shadow.uninterrupted").passed
    finally:
        ledger.close()


def test_unfinalized_started_session_breaks_a_qualified_streak(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "ledger.sqlite3")
    try:
        evaluator = TransparentCampaignEvaluator(
            ledger,
            TransparentCampaignPolicy(required_consecutive_sessions=2),
        )
        for session_date in ("2026-07-13", "2026-07-14"):
            _record_session(ledger, session_date)
            evaluator.evaluate_and_record(session_date)
        ledger.append_event(
            "session",
            "started",
            {
                "session_date": "2026-07-15",
                "mode": "paper",
                "engine_version": "v2",
                "routing_engine_version": "v1",
                "campaign_fingerprint": "config-and-artifacts-v2",
                "promoted_run_ids": {"AAPL": "aapl-v2-approved"},
            },
            timestamp="2026-07-15T16:00:00+00:00",
        )

        report = evaluator.report()

        assert not report.qualified
        assert report.trailing_passing_sessions == 0
        assert report.sessions[-1].session_date == "2026-07-15"
        assert not report.sessions[-1].passed
    finally:
        ledger.close()
