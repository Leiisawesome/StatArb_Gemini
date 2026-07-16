from __future__ import annotations

import json

from l1_microstructure.live.broker_models import IBKRConnectionConfig
from l1_microstructure.production.campaign_readiness import PaperCampaignReadinessEvaluator
from l1_microstructure.production.config import ProductionConfig, RiskLimits
from l1_microstructure.production.preflight import (
    PreflightCheck,
    PreflightStatus,
    ProductionPreflightReport,
)


def _config(tmp_path, *, drill: bool = False) -> ProductionConfig:
    return ProductionConfig(
        symbols=("AAPL",),
        artifact_root=tmp_path / "artifacts",
        promoted_run_ids={"AAPL": "aapl-v1-approved"},
        transparent_shadow_run_ids={"AAPL": "aapl-v2-approved"},
        database_path=tmp_path / ("paper-drills.sqlite3" if drill else "trading.sqlite3"),
        broker_env_file=tmp_path / ("broker.drill.env" if drill else "broker.paper.env"),
        api_port=8766 if drill else 8765,
        risk=(
            RiskLimits(0.005, 0.10, 0.01, False, False)
            if drill
            else RiskLimits()
        ),
    )


def _preflight(status: PreflightStatus = PreflightStatus.PASSED) -> ProductionPreflightReport:
    return ProductionPreflightReport(
        (PreflightCheck("test.preflight", status, "safe", {}),)
    )


def _evaluate(tmp_path, **overrides):
    production_path = tmp_path / "production.json"
    drill_path = tmp_path / "production.drill.json"
    production_path.write_text("{}", encoding="utf-8")
    drill_path.write_text("{}", encoding="utf-8")
    values = {
        "production_config": _config(tmp_path),
        "drill_config": _config(tmp_path, drill=True),
        "production_config_path": production_path,
        "drill_config_path": drill_path,
        "preflight_report": _preflight(),
        "git_commit": "abc123",
        "git_clean": True,
        "broker_config_loader": lambda path: IBKRConnectionConfig(
            client_id=2 if path and "drill" in path else 1,
            account_id="DU123456",
            paper_trading=True,
            outside_regular_trading_hours=False,
        ),
    }
    values.update(overrides)
    return PaperCampaignReadinessEvaluator(**values).evaluate()


def test_campaign_readiness_freezes_only_redacted_passing_evidence(tmp_path) -> None:
    report = _evaluate(tmp_path)

    assert report.passed
    assert report.frozen["git_commit"] == "abc123"
    assert report.frozen["paper_account_sha256"]
    payload = json.dumps(report.to_dict())
    assert "DU123456" not in payload
    assert all(check.passed for check in report.checks)


def test_campaign_readiness_fails_dirty_git_existing_ledger_and_unsafe_broker(tmp_path) -> None:
    production = _config(tmp_path)
    production.database_path.write_bytes(b"existing campaign")
    report = _evaluate(
        tmp_path,
        production_config=production,
        git_clean=False,
        preflight_report=_preflight(PreflightStatus.FAILED),
        broker_config_loader=lambda path: IBKRConnectionConfig(
            client_id=1,
            account_id=None,
            paper_trading=True,
            outside_regular_trading_hours=True,
        ),
    )

    failed = {check.code for check in report.checks if not check.passed}
    assert not report.passed
    assert failed >= {
        "git.clean",
        "preflight.passed",
        "campaign.fresh_database",
        "broker.paper_account",
        "broker.client_ids_isolated",
    }


def test_campaign_readiness_rejects_placeholder_artifacts_and_shared_drill_boundary(tmp_path) -> None:
    production = _config(tmp_path)
    production = ProductionConfig(
        symbols=production.symbols,
        artifact_root=production.artifact_root,
        promoted_run_ids={"AAPL": "replace-with-validation-approved-v1-run-id"},
        transparent_shadow_run_ids={"AAPL": "replace-with-validation-approved-v2-run-id"},
        database_path=production.database_path,
        broker_env_file=production.broker_env_file,
    )
    report = _evaluate(
        tmp_path,
        production_config=production,
        drill_config=production,
    )

    failed = {check.code for check in report.checks if not check.passed}
    assert failed >= {"campaign.artifacts_pinned", "drill.isolated"}
