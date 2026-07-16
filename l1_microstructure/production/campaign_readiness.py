"""Fail-closed preparation gate for the ten-session paper campaign."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Sequence

from l1_microstructure.live.broker_models import IBKRConnectionConfig
from l1_microstructure.live.router_adapters import load_ibkr_connection_config

from .config import OperatingMode, ProductionConfig
from .preflight import ProductionPreflight, ProductionPreflightReport
from .secrets import get_secret

PAPER_READINESS_SUCCESS_EXIT_CODE = 0
PAPER_READINESS_FAILURE_EXIT_CODE = 2


@dataclass(frozen=True, slots=True)
class CampaignReadinessCheck:
    code: str
    passed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCampaignReadinessReport:
    checks: tuple[CampaignReadinessCheck, ...]
    frozen: dict[str, Any]
    schema_version: int = 1

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "frozen": dict(self.frozen),
        }


class PaperCampaignReadinessEvaluator:
    """Verify that counted paper trading can begin without mutating runtime state."""

    def __init__(
        self,
        production_config: ProductionConfig,
        drill_config: ProductionConfig,
        *,
        production_config_path: Path,
        drill_config_path: Path,
        preflight_report: ProductionPreflightReport,
        git_commit: str,
        git_clean: bool,
        broker_config_loader: Callable[[str | None], IBKRConnectionConfig] = load_ibkr_connection_config,
    ) -> None:
        self.production = production_config
        self.drill = drill_config
        self.production_path = production_config_path
        self.drill_path = drill_config_path
        self.preflight = preflight_report
        self.git_commit = git_commit
        self.git_clean = git_clean
        self.broker_config_loader = broker_config_loader

    def evaluate(self) -> PaperCampaignReadinessReport:
        paper_broker = self.broker_config_loader(self._broker_path(self.production))
        drill_broker = self.broker_config_loader(self._broker_path(self.drill))
        expected_session = {
            "timezone": "America/New_York",
            "market_open": "09:30",
            "stop_entries": "15:50",
            "flatten_at": "15:58",
            "market_close": "16:00",
        }
        production_risk = self.production.risk
        drill_risk = self.drill.risk
        pins_are_final = all(
            run_id and "replace-with" not in run_id.lower()
            for mapping in (
                self.production.promoted_run_ids,
                self.production.transparent_shadow_run_ids,
            )
            for run_id in mapping.values()
        )
        checks = (
            CampaignReadinessCheck(
                "git.clean",
                self.git_clean and bool(self.git_commit),
                {"commit": self.git_commit, "clean": self.git_clean},
            ),
            CampaignReadinessCheck(
                "preflight.passed",
                self.preflight.passed,
                {"failed_checks": [check.code for check in self.preflight.failed_checks]},
            ),
            CampaignReadinessCheck(
                "campaign.single_symbol",
                len(self.production.symbols) == 1,
                {"symbols": list(self.production.symbols)},
            ),
            CampaignReadinessCheck(
                "campaign.artifacts_pinned",
                pins_are_final
                and set(self.production.promoted_run_ids) == set(self.production.symbols)
                and set(self.production.transparent_shadow_run_ids) == set(self.production.symbols),
                {
                    "v1_run_ids": dict(self.production.promoted_run_ids),
                    "v2_run_ids": dict(self.production.transparent_shadow_run_ids),
                },
            ),
            CampaignReadinessCheck(
                "campaign.paper_only",
                self.production.mode is OperatingMode.PAPER
                and not production_risk.allow_leverage
                and not production_risk.allow_shorting,
                {
                    "mode": self.production.mode.value,
                    "allow_leverage": production_risk.allow_leverage,
                    "allow_shorting": production_risk.allow_shorting,
                },
            ),
            CampaignReadinessCheck(
                "campaign.conservative_risk",
                production_risk.daily_loss_fraction <= 0.01
                and production_risk.max_gross_exposure <= 0.25
                and production_risk.max_symbol_exposure <= 0.03
                and drill_risk.daily_loss_fraction <= production_risk.daily_loss_fraction
                and drill_risk.max_gross_exposure <= production_risk.max_gross_exposure
                and drill_risk.max_symbol_exposure <= production_risk.max_symbol_exposure,
                {
                    "production": asdict(production_risk),
                    "drill": asdict(drill_risk),
                },
            ),
            CampaignReadinessCheck(
                "campaign.regular_session",
                asdict(self.production.session) == expected_session,
                {"session": asdict(self.production.session)},
            ),
            CampaignReadinessCheck(
                "campaign.fresh_database",
                not self.production.database_path.exists(),
                {"path": str(self.production.database_path)},
            ),
            CampaignReadinessCheck(
                "drill.isolated",
                self.drill.mode is OperatingMode.PAPER
                and self.drill.database_path != self.production.database_path
                and self.drill.api_port != self.production.api_port
                and self.drill.broker_env_file != self.production.broker_env_file
                and self.drill.symbols == self.production.symbols
                and self.drill.promoted_run_ids == self.production.promoted_run_ids
                and self.drill.transparent_shadow_run_ids
                == self.production.transparent_shadow_run_ids,
                {
                    "production_database": str(self.production.database_path),
                    "drill_database": str(self.drill.database_path),
                    "production_api_port": self.production.api_port,
                    "drill_api_port": self.drill.api_port,
                },
            ),
            CampaignReadinessCheck(
                "broker.paper_account",
                bool(paper_broker.account_id)
                and paper_broker.account_id == drill_broker.account_id
                and paper_broker.paper_trading
                and drill_broker.paper_trading
                and not paper_broker.outside_regular_trading_hours
                and not drill_broker.outside_regular_trading_hours,
                {
                    "account_configured": bool(paper_broker.account_id),
                    "same_drill_account": bool(paper_broker.account_id)
                    and paper_broker.account_id == drill_broker.account_id,
                    "paper_mode": paper_broker.paper_trading and drill_broker.paper_trading,
                    "outside_rth": paper_broker.outside_regular_trading_hours
                    or drill_broker.outside_regular_trading_hours,
                },
            ),
            CampaignReadinessCheck(
                "broker.client_ids_isolated",
                paper_broker.client_id != drill_broker.client_id,
                {
                    "production_client_id": paper_broker.client_id,
                    "drill_client_id": drill_broker.client_id,
                },
            ),
        )
        return PaperCampaignReadinessReport(
            checks,
            {
                "git_commit": self.git_commit,
                "production_config_sha256": self._file_hash(self.production_path),
                "drill_config_sha256": self._file_hash(self.drill_path),
                "symbols": list(self.production.symbols),
                "promoted_run_ids": dict(self.production.promoted_run_ids),
                "transparent_shadow_run_ids": dict(self.production.transparent_shadow_run_ids),
                "paper_account_sha256": self._account_hash(paper_broker.account_id),
                "paper_client_id": paper_broker.client_id,
                "drill_client_id": drill_broker.client_id,
                "qualification_database": str(self.production.database_path),
            },
        )

    @staticmethod
    def _broker_path(config: ProductionConfig) -> str | None:
        return None if config.broker_env_file is None else str(config.broker_env_file)

    @staticmethod
    def _file_hash(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _account_hash(account_id: str | None) -> str | None:
        return None if not account_id else sha256(account_id.encode("utf-8")).hexdigest()


def _git_state(repository: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit, not status


def evaluate_campaign_readiness(
    production_path: Path,
    drill_path: Path,
    *,
    repository: Path,
) -> PaperCampaignReadinessReport:
    production = ProductionConfig.from_json(production_path)
    drill = ProductionConfig.from_json(drill_path)
    preflight = ProductionPreflight(production, secret_lookup=get_secret).run()
    git_commit, git_clean = _git_state(repository)
    return PaperCampaignReadinessEvaluator(
        production,
        drill,
        production_config_path=production_path,
        drill_config_path=drill_path,
        preflight_report=preflight,
        git_commit=git_commit,
        git_clean=git_clean,
    ).evaluate()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ten-session paper-campaign readiness")
    parser.add_argument("--config", type=Path, default=Path("config/production.json"))
    parser.add_argument("--drill-config", type=Path, default=Path("config/production.drill.json"))
    args = parser.parse_args(argv)
    try:
        report = evaluate_campaign_readiness(
            args.config,
            args.drill_config,
            repository=Path.cwd(),
        )
        payload = report.to_dict()
        exit_code = (
            PAPER_READINESS_SUCCESS_EXIT_CODE
            if report.passed
            else PAPER_READINESS_FAILURE_EXIT_CODE
        )
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "passed": False,
            "checks": [],
            "frozen": {},
            "error": {"code": "campaign_readiness.failed", "error_type": type(exc).__name__},
        }
        exit_code = PAPER_READINESS_FAILURE_EXIT_CODE
    print(json.dumps(payload, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
