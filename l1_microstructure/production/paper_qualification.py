"""Ledger-backed regular-hours paper-session qualification."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from .ledger import OperationalLedger

PAPER_QUALIFICATION_SUCCESS_EXIT_CODE = 0
PAPER_QUALIFICATION_FAILURE_EXIT_CODE = 2
_TERMINAL_ORDER_STATUSES = {"filled", "cancelled", "rejected"}


@dataclass(frozen=True, slots=True)
class PaperQualificationPolicy:
    required_consecutive_sessions: int = 10
    timezone: str = "America/New_York"

    def __post_init__(self) -> None:
        if self.required_consecutive_sessions <= 0:
            raise ValueError("required consecutive paper sessions must be positive")
        ZoneInfo(self.timezone)


@dataclass(frozen=True, slots=True)
class PaperSessionCheck:
    code: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "passed": self.passed,
            "message": self.message,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PaperSessionCheck:
        return cls(
            code=str(payload["code"]),
            passed=bool(payload["passed"]),
            message=str(payload["message"]),
            details=dict(payload.get("details", {})),
        )


@dataclass(frozen=True, slots=True)
class PaperSessionEvaluation:
    session_date: str
    checks: tuple[PaperSessionCheck, ...]
    metrics: dict[str, Any]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "status": "passed" if self.passed else "failed",
            "checks": [check.to_dict() for check in self.checks],
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PaperSessionEvaluation:
        return cls(
            session_date=str(payload["session_date"]),
            checks=tuple(PaperSessionCheck.from_dict(item) for item in payload.get("checks", [])),
            metrics=dict(payload.get("metrics", {})),
        )


@dataclass(frozen=True, slots=True)
class PaperQualificationReport:
    required_consecutive_sessions: int
    trailing_passing_sessions: int
    sessions: tuple[PaperSessionEvaluation, ...]
    schema_version: int = 1
    error: dict[str, Any] | None = None

    @property
    def qualified(self) -> bool:
        return self.error is None and self.trailing_passing_sessions >= self.required_consecutive_sessions

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": "qualified" if self.qualified else "not_qualified",
            "qualified": self.qualified,
            "required_consecutive_sessions": self.required_consecutive_sessions,
            "trailing_passing_sessions": self.trailing_passing_sessions,
            "session_count": len(self.sessions),
            "sessions": [session.to_dict() for session in self.sessions],
        }
        if self.error is not None:
            payload["error"] = dict(self.error)
        return payload


class PaperSessionEvaluator:
    def __init__(self, ledger: OperationalLedger, policy: PaperQualificationPolicy | None = None) -> None:
        self.ledger = ledger
        self.policy = policy or PaperQualificationPolicy()

    def evaluate_and_record(self, session_date: str | date) -> PaperSessionEvaluation:
        evaluation = self.evaluate(session_date)
        self.ledger.append_event("qualification", "paper_session", evaluation.to_dict())
        return evaluation

    def evaluate(self, session_date: str | date) -> PaperSessionEvaluation:
        day = date.fromisoformat(session_date) if isinstance(session_date, str) else session_date
        start, end = self._utc_bounds(day)
        events = self.ledger.events_between(start, end)
        orders = self.ledger.orders_between(start, end)
        close_events = [
            event
            for event in events
            if event["category"] == "session"
            and event["event_type"] == "closed"
            and event["payload"].get("session_date") == day.isoformat()
        ]
        start_events = [
            event
            for event in events
            if event["category"] == "session"
            and event["event_type"] == "started"
            and event["payload"].get("session_date") == day.isoformat()
        ]
        start_payload = dict(start_events[0]["payload"]) if start_events else {}
        close_payload = dict(close_events[-1]["payload"]) if close_events else {}
        framework_events = [
            event for event in events if event["category"] == "market" and event["event_type"] == "framework_update"
        ]
        blocked_events = [
            event for event in events if event["category"] == "risk" and event["event_type"] == "order_blocked"
        ]
        acknowledgement_events = [
            event for event in events if event["category"] == "order" and event["event_type"] == "route_acknowledgement"
        ]
        report_events = [
            event for event in events if event["category"] == "order" and event["event_type"] == "execution_report"
        ]
        incident_events = [
            event for event in events if event["category"] == "incident" and event["event_type"] == "runtime_halted"
        ]
        client_ids = [str(order["client_order_id"]) for order in orders]
        external_ids = [str(order["external_order_id"]) for order in orders if order.get("external_order_id")]
        submitted_ids = {
            str(client_order_id)
            for event in framework_events
            for client_order_id in event["payload"].get("submitted_client_order_ids", [])
        }
        blocked_ids = {
            str(event["payload"]["client_order_id"])
            for event in blocked_events
            if event["payload"].get("client_order_id")
        }
        known_ids = set(client_ids)
        acknowledgement_ids = {
            str(event["payload"]["client_order_id"])
            for event in acknowledgement_events
            if event["payload"].get("client_order_id")
        }
        report_ids = {
            str(event["payload"]["client_order_id"])
            for event in report_events
            if event["payload"].get("client_order_id")
        }
        unresolved_decisions = sorted(submitted_ids - known_ids - blocked_ids)
        unknown_acknowledgements = sorted(acknowledgement_ids - known_ids)
        unknown_reports = sorted(report_ids - known_ids)
        reports_without_client_id = sum(1 for event in report_events if not event["payload"].get("client_order_id"))
        nonterminal_orders = sorted(
            order["client_order_id"] for order in orders if order["status"] not in _TERMINAL_ORDER_STATUSES
        )
        close_positions = {symbol: float(quantity) for symbol, quantity in close_payload.get("positions", {}).items()}
        nonzero_positions = {symbol: quantity for symbol, quantity in close_positions.items() if quantity != 0.0}
        close_open_orders = list(close_payload.get("open_orders", []))
        checks = (
            PaperSessionCheck(
                "session.start_marker",
                bool(start_events),
                "authoritative session-start evidence is present"
                if start_events
                else "session-start evidence is missing",
            ),
            PaperSessionCheck(
                "session.close_marker",
                bool(close_events),
                "authoritative session-close evidence is present"
                if close_events
                else "session-close evidence is missing",
            ),
            PaperSessionCheck(
                "session.paper_mode",
                start_payload.get("mode") == "paper" and close_payload.get("mode") == "paper",
                "session ran in paper mode"
                if start_payload.get("mode") == "paper" and close_payload.get("mode") == "paper"
                else "session was not started and closed in paper mode",
            ),
            PaperSessionCheck(
                "session.regular_close_phase",
                close_payload.get("session_phase") in {"flatten", "closed"},
                "session closed during the flatten or closed phase",
                {"session_phase": close_payload.get("session_phase")},
            ),
            PaperSessionCheck(
                "market.activity_recorded",
                bool(framework_events),
                "market framework activity is recorded"
                if framework_events
                else "no market framework activity is recorded",
                {"framework_update_count": len(framework_events)},
            ),
            PaperSessionCheck(
                "orders.unique_client_ids",
                len(client_ids) == len(set(client_ids)),
                "client order ids are unique",
                {"order_count": len(client_ids)},
            ),
            PaperSessionCheck(
                "orders.unique_external_ids",
                len(external_ids) == len(set(external_ids)),
                "external order ids are unique",
                {"external_order_count": len(external_ids)},
            ),
            PaperSessionCheck(
                "orders.all_terminal",
                not nonterminal_orders and not close_open_orders,
                "all orders are terminal and none remain open",
                {"nonterminal_client_order_ids": nonterminal_orders, "close_open_order_count": len(close_open_orders)},
            ),
            PaperSessionCheck(
                "fills.reconciled",
                not unknown_reports and reports_without_client_id == 0,
                "every execution report reconciles to a durable order intent",
                {
                    "unknown_client_order_ids": unknown_reports,
                    "reports_without_client_order_id": reports_without_client_id,
                },
            ),
            PaperSessionCheck(
                "positions.flat_at_close",
                not nonzero_positions,
                "no strategy positions remain at session close",
                {"nonzero_positions": nonzero_positions},
            ),
            PaperSessionCheck(
                "audit.decisions_complete",
                not unresolved_decisions,
                "every submitted decision is routed or durably blocked",
                {"unresolved_client_order_ids": unresolved_decisions},
            ),
            PaperSessionCheck(
                "audit.acknowledgements_complete",
                not unknown_acknowledgements,
                "every route acknowledgement maps to a durable order intent",
                {"unknown_client_order_ids": unknown_acknowledgements},
            ),
            PaperSessionCheck(
                "incidents.none",
                not incident_events,
                "no runtime halt incidents occurred" if not incident_events else "runtime halt incidents occurred",
                {"incident_count": len(incident_events)},
            ),
        )
        metrics = {
            "audit_event_count": len(events),
            "framework_update_count": len(framework_events),
            "order_count": len(orders),
            "acknowledgement_count": len(acknowledgement_events),
            "execution_report_count": len(report_events),
            "blocked_order_count": len(blocked_events),
            "incident_count": len(incident_events),
            "start_marker_count": len(start_events),
            "close_marker_count": len(close_events),
        }
        return PaperSessionEvaluation(day.isoformat(), checks, metrics)

    def report(self) -> PaperQualificationReport:
        count = self.ledger.event_count(category="qualification", event_type="paper_session")
        events = self.ledger.recent_events(
            max(count, 1),
            category="qualification",
            event_type="paper_session",
        )
        latest_by_date: dict[str, PaperSessionEvaluation] = {}
        for event in events:
            try:
                evaluation = PaperSessionEvaluation.from_dict(event["payload"])
                date.fromisoformat(evaluation.session_date)
            except (KeyError, TypeError, ValueError):
                continue
            if not evaluation.checks:
                continue
            latest_by_date.setdefault(evaluation.session_date, evaluation)
        started_count = self.ledger.event_count(category="session", event_type="started")
        started_events = self.ledger.recent_events(
            max(started_count, 1),
            category="session",
            event_type="started",
        )
        for event in started_events:
            session_date = event["payload"].get("session_date")
            if not isinstance(session_date, str) or session_date in latest_by_date:
                continue
            try:
                latest_by_date[session_date] = self.evaluate(session_date)
            except (TypeError, ValueError):
                continue
        sessions = tuple(latest_by_date[key] for key in sorted(latest_by_date))
        trailing = 0
        for session in reversed(sessions):
            if not session.passed:
                break
            trailing += 1
        return PaperQualificationReport(
            required_consecutive_sessions=self.policy.required_consecutive_sessions,
            trailing_passing_sessions=trailing,
            sessions=sessions,
        )

    def _utc_bounds(self, day: date) -> tuple[str, str]:
        zone = ZoneInfo(self.policy.timezone)
        local_start = datetime.combine(day, time.min, zone)
        local_end = local_start + timedelta(days=1)
        return local_start.astimezone(timezone.utc).isoformat(), local_end.astimezone(timezone.utc).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate durable regular-hours paper-session evidence")
    parser.add_argument("--database", type=Path, default=Path("var/trading.sqlite3"))
    parser.add_argument("--finalize", metavar="YYYY-MM-DD", help="Evaluate and append evidence for one closed session")
    args = parser.parse_args(argv)
    ledger: OperationalLedger | None = None
    try:
        ledger = OperationalLedger(args.database)
        evaluator = PaperSessionEvaluator(ledger)
        if args.finalize:
            evaluator.evaluate_and_record(args.finalize)
        report = evaluator.report()
    except Exception as exc:
        report = PaperQualificationReport(
            required_consecutive_sessions=10,
            trailing_passing_sessions=0,
            sessions=(),
            error={"code": "paper_qualification.failed", "error_type": type(exc).__name__},
        )
    finally:
        if ledger is not None:
            ledger.close()
    print(json.dumps(report.to_dict(), sort_keys=True))
    return PAPER_QUALIFICATION_SUCCESS_EXIT_CODE if report.qualified else PAPER_QUALIFICATION_FAILURE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
