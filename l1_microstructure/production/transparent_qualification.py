"""Qualification gate for a frozen v2 transparent-engine shadow campaign."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from .ledger import OperationalLedger
from .paper_qualification import PaperSessionEvaluator

TRANSPARENT_QUALIFICATION_SUCCESS_EXIT_CODE = 0
TRANSPARENT_QUALIFICATION_FAILURE_EXIT_CODE = 2


@dataclass(frozen=True, slots=True)
class TransparentCampaignPolicy:
    required_consecutive_sessions: int = 10
    maximum_latency_ratio: float = 1.20
    timezone: str = "America/New_York"

    def __post_init__(self) -> None:
        if self.required_consecutive_sessions <= 0 or self.maximum_latency_ratio <= 0.0:
            raise ValueError("transparent campaign policy bounds must be positive")
        ZoneInfo(self.timezone)


@dataclass(frozen=True, slots=True)
class TransparentCampaignCheck:
    code: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TransparentCampaignCheck:
        return cls(str(payload["code"]), bool(payload["passed"]), dict(payload.get("details", {})))


@dataclass(frozen=True, slots=True)
class TransparentCampaignSession:
    session_date: str
    fingerprint: str
    checks: tuple[TransparentCampaignCheck, ...]
    metrics: dict[str, Any]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "fingerprint": self.fingerprint,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TransparentCampaignSession:
        return cls(
            str(payload["session_date"]),
            str(payload.get("fingerprint", "")),
            tuple(TransparentCampaignCheck.from_dict(item) for item in payload.get("checks", ())),
            dict(payload.get("metrics", {})),
        )


@dataclass(frozen=True, slots=True)
class TransparentCampaignReport:
    required_consecutive_sessions: int
    trailing_passing_sessions: int
    frozen_fingerprint: str | None
    sessions: tuple[TransparentCampaignSession, ...]
    error: dict[str, Any] | None = None
    schema_version: int = 1

    @property
    def qualified(self) -> bool:
        return self.error is None and self.trailing_passing_sessions >= self.required_consecutive_sessions

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "qualified": self.qualified,
            "status": "qualified" if self.qualified else "not_qualified",
            "required_consecutive_sessions": self.required_consecutive_sessions,
            "trailing_passing_sessions": self.trailing_passing_sessions,
            "frozen_fingerprint": self.frozen_fingerprint,
            "sessions": [session.to_dict() for session in self.sessions],
            **({} if self.error is None else {"error": dict(self.error)}),
        }


class TransparentCampaignEvaluator:
    """Accept only v2, validation-approved, error-free, version-frozen sessions."""

    def __init__(self, ledger: OperationalLedger, policy: TransparentCampaignPolicy | None = None) -> None:
        self.ledger = ledger
        self.policy = policy or TransparentCampaignPolicy()

    def evaluate_and_record(self, session_date: str | date) -> TransparentCampaignSession:
        result = self.evaluate(session_date)
        self.ledger.append_event("qualification", "transparent_paper_session", result.to_dict())
        return result

    def evaluate(self, session_date: str | date) -> TransparentCampaignSession:
        day = date.fromisoformat(session_date) if isinstance(session_date, str) else session_date
        start, end = self._utc_bounds(day)
        events = self.ledger.events_between(start, end)
        starts = self._events(events, "session", "started", day)
        closes = self._events(events, "session", "closed", day)
        summaries = [
            event for event in events
            if event["category"] == "model" and event["event_type"] == "transparent_shadow_summary"
        ]
        restart_events = [
            event for event in events
            if event["category"] == "model"
            and event["event_type"] == "transparent_shadow_restart"
            and event["payload"].get("session_date") == day.isoformat()
        ]
        start_payload = dict(starts[0]["payload"]) if starts else {}
        close_payload = dict(closes[-1]["payload"]) if closes else {}
        summary = dict(summaries[-1]["payload"]) if summaries else {}
        paper_safety = PaperSessionEvaluator(self.ledger).evaluate(day)
        fingerprint = str(start_payload.get("campaign_fingerprint", ""))
        baseline_latency = float(summary.get("baseline_p95_latency_ns", 0.0))
        candidate_latency = float(summary.get("candidate_p95_latency_ns", 0.0))
        checks = (
            TransparentCampaignCheck(
                "session.start_marker",
                len(starts) == 1,
                {"count": len(starts)},
            ),
            TransparentCampaignCheck(
                "session.close_marker",
                len(closes) == 1,
                {"count": len(closes)},
            ),
            TransparentCampaignCheck(
                "session.paper_mode",
                start_payload.get("mode") == close_payload.get("mode") == "paper",
            ),
            TransparentCampaignCheck("session.trading_day", day.weekday() < 5),
            TransparentCampaignCheck(
                "session.regular_close_phase",
                close_payload.get("session_phase") in {"flatten", "closed"},
            ),
            TransparentCampaignCheck(
                "session.paper_safety",
                paper_safety.passed,
                {"failed_checks": [check.code for check in paper_safety.checks if not check.passed]},
            ),
            TransparentCampaignCheck(
                "engine.v2_frozen",
                start_payload.get("engine_version") == close_payload.get("engine_version") == "v2"
                and bool(fingerprint)
                and fingerprint == close_payload.get("campaign_fingerprint"),
                {"campaign_fingerprint": fingerprint},
            ),
            TransparentCampaignCheck(
                "engine.run_ids_frozen",
                bool(start_payload.get("promoted_run_ids"))
                and start_payload.get("promoted_run_ids") == close_payload.get("promoted_run_ids"),
            ),
            TransparentCampaignCheck("promotion.validation_passed", summary.get("validation_passed") is True),
            TransparentCampaignCheck(
                "shadow.routing_isolated",
                start_payload.get("routing_engine_version") == "v1"
                and close_payload.get("routing_engine_version") == "v1"
                and summary.get("routing_engine_version") == "v1"
                and summary.get("engine_version") == "v2",
            ),
            TransparentCampaignCheck(
                "shadow.evidence_frozen",
                summary.get("campaign_fingerprint") == fingerprint
                and summary.get("promoted_run_ids") == start_payload.get("promoted_run_ids"),
            ),
            TransparentCampaignCheck(
                "shadow.summary_present",
                len(summaries) == 1,
                {"count": len(summaries)},
            ),
            TransparentCampaignCheck(
                "shadow.activity",
                int(summary.get("candidate_update_count", 0)) > 0,
                {"candidate_update_count": int(summary.get("candidate_update_count", 0))},
            ),
            TransparentCampaignCheck(
                "shadow.outcomes_resolved",
                int(summary.get("resolved_outcome_count", 0)) > 0,
                {"resolved_outcome_count": int(summary.get("resolved_outcome_count", 0))},
            ),
            TransparentCampaignCheck(
                "shadow.uninterrupted",
                not restart_events,
                {"restart_count": len(restart_events)},
            ),
            TransparentCampaignCheck(
                "shadow.errors",
                int(summary.get("candidate_error_count", -1)) == 0,
                {"candidate_error_count": int(summary.get("candidate_error_count", -1))},
            ),
            TransparentCampaignCheck(
                "shadow.no_late_events",
                int(summary.get("candidate_late_event_count", -1)) == 0,
                {"candidate_late_event_count": int(summary.get("candidate_late_event_count", -1))},
            ),
            TransparentCampaignCheck(
                "shadow.latency",
                baseline_latency > 0.0
                and candidate_latency <= baseline_latency * self.policy.maximum_latency_ratio,
                {
                    "baseline_p95_latency_ns": baseline_latency,
                    "candidate_p95_latency_ns": candidate_latency,
                    "maximum_ratio": self.policy.maximum_latency_ratio,
                },
            ),
        )
        return TransparentCampaignSession(
            day.isoformat(),
            fingerprint,
            checks,
            {
                "shadow_summary_count": len(summaries),
                "candidate_update_count": int(summary.get("candidate_update_count", 0)),
                "candidate_error_count": int(summary.get("candidate_error_count", -1)),
                "candidate_late_event_count": int(summary.get("candidate_late_event_count", -1)),
                "resolved_outcome_count": int(summary.get("resolved_outcome_count", 0)),
                "restart_count": len(restart_events),
                "paper_safety_passed": paper_safety.passed,
            },
        )

    def report(self) -> TransparentCampaignReport:
        events = self.ledger.recent_events(
            max(self.ledger.event_count(category="qualification", event_type="transparent_paper_session"), 1),
            category="qualification",
            event_type="transparent_paper_session",
        )
        latest: dict[str, TransparentCampaignSession] = {}
        for event in events:
            try:
                session = TransparentCampaignSession.from_dict(event["payload"])
                date.fromisoformat(session.session_date)
            except (KeyError, TypeError, ValueError):
                continue
            latest.setdefault(session.session_date, session)
        started_events = self.ledger.recent_events(
            max(self.ledger.event_count(category="session", event_type="started"), 1),
            category="session",
            event_type="started",
        )
        for event in started_events:
            session_date = event["payload"].get("session_date")
            if not isinstance(session_date, str) or session_date in latest:
                continue
            try:
                date.fromisoformat(session_date)
                latest[session_date] = self.evaluate(session_date)
            except (TypeError, ValueError):
                continue
        sessions = tuple(latest[key] for key in sorted(latest))
        frozen = sessions[-1].fingerprint if sessions else None
        trailing = 0
        for session in reversed(sessions):
            if not session.passed or not frozen or session.fingerprint != frozen:
                break
            trailing += 1
        return TransparentCampaignReport(
            self.policy.required_consecutive_sessions,
            trailing,
            frozen,
            sessions,
        )

    @staticmethod
    def _events(events, category: str, event_type: str, day: date):
        return [
            event for event in events
            if event["category"] == category
            and event["event_type"] == event_type
            and event["payload"].get("session_date") == day.isoformat()
        ]

    def _utc_bounds(self, day: date) -> tuple[str, str]:
        zone = ZoneInfo(self.policy.timezone)
        local_start = datetime.combine(day, time.min, zone)
        local_end = local_start + timedelta(days=1)
        return local_start.astimezone(timezone.utc).isoformat(), local_end.astimezone(timezone.utc).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a frozen transparent-engine paper campaign")
    parser.add_argument("--database", type=Path, default=Path("var/trading.sqlite3"))
    parser.add_argument("--finalize", metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)
    ledger: OperationalLedger | None = None
    try:
        ledger = OperationalLedger(args.database)
        evaluator = TransparentCampaignEvaluator(ledger)
        if args.finalize:
            evaluator.evaluate_and_record(args.finalize)
        report = evaluator.report()
    except Exception as exc:
        report = TransparentCampaignReport(10, 0, None, (), {"error_type": type(exc).__name__})
    finally:
        if ledger is not None:
            ledger.close()
    print(json.dumps(report.to_dict(), sort_keys=True))
    return TRANSPARENT_QUALIFICATION_SUCCESS_EXIT_CODE if report.qualified else TRANSPARENT_QUALIFICATION_FAILURE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
