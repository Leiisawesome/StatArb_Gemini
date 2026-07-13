from __future__ import annotations

import json

import pytest

from l1_microstructure.artifacts import LocalArtifactStore
from l1_microstructure.live.broker_models import IBKRConnectionConfig
from l1_microstructure.production.config import OperatingMode, ProductionConfig
from l1_microstructure.production.daemon import main
from l1_microstructure.production.preflight import (
    PreflightStatus,
    ProductionPreflight,
    ProductionPreflightError,
)


def _config(tmp_path, **overrides) -> ProductionConfig:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(exist_ok=True)
    values = {
        "symbols": ("AAPL",),
        "artifact_root": artifact_root,
        "promoted_run_ids": {"AAPL": "aapl-v1"},
        "database_path": tmp_path / "runtime.sqlite3",
        "broker_env_file": None,
        "warmup_seconds": 0.0,
    }
    values.update(overrides)
    return ProductionConfig(**values)


def _secrets(**overrides):
    values = {
        "MASSIVE_API_KEY": "massive-secret-value",
        "TRADING_CONSOLE_TOKEN": "console-secret-value",
    }
    values.update(overrides)
    return values.get


def _paper_broker(_env_file):
    return IBKRConnectionConfig(paper_trading=True)


def test_artifact_store_read_only_mode_never_creates_root(tmp_path) -> None:
    missing = tmp_path / "missing-artifacts"

    with pytest.raises(ValueError, match="artifact root"):
        LocalArtifactStore(missing, create=False)

    assert missing.exists() is False


def test_production_preflight_returns_typed_passing_diagnostics(tmp_path) -> None:
    validated: list[tuple[str, str]] = []
    report = ProductionPreflight(
        _config(tmp_path),
        secret_lookup=_secrets(),
        artifact_validator=lambda symbol, run_id: validated.append((symbol, run_id)),
        broker_config_loader=_paper_broker,
    ).run()

    assert report.passed is True
    assert report.failed_checks == ()
    assert validated == [("AAPL", "aapl-v1")]
    assert all(check.status is PreflightStatus.PASSED for check in report.checks)
    assert {check.code for check in report.checks} >= {
        "credential.massive_api_key",
        "credential.trading_console_token",
        "artifact.promoted.aapl",
        "broker.mode",
        "filesystem.database",
        "runtime.retry_policies",
    }


def test_production_preflight_uses_runtime_artifact_quality_gate(tmp_path, monkeypatch) -> None:
    calls = []

    def resolve(self, *, symbol, run_id, quality_gate):
        calls.append((symbol, run_id, quality_gate))
        return object()

    monkeypatch.setattr(
        "l1_microstructure.production.preflight.ArtifactBundleSelector.resolve_passing_by_run_id",
        resolve,
    )
    report = ProductionPreflight(
        _config(tmp_path),
        secret_lookup=_secrets(),
        broker_config_loader=_paper_broker,
    ).run()

    assert report.passed is True
    assert calls[0][0:2] == ("AAPL", "aapl-v1")
    assert calls[0][2].minimum_fill_rate is None


def test_production_preflight_reports_missing_credentials_without_values(tmp_path) -> None:
    report = ProductionPreflight(
        _config(tmp_path),
        secret_lookup=_secrets(MASSIVE_API_KEY=None),
        artifact_validator=lambda _symbol, _run_id: None,
        broker_config_loader=_paper_broker,
    ).run()

    payload = json.dumps(report.to_dict())
    assert report.passed is False
    assert "MASSIVE_API_KEY is not configured" in payload
    assert "console-secret-value" not in payload


def test_production_preflight_hides_secret_provider_exception_text(tmp_path) -> None:
    def lookup(name):
        if name == "MASSIVE_API_KEY":
            raise RuntimeError("provider accidentally included unknown-secret-value")
        return "console-secret-value"

    report = ProductionPreflight(
        _config(tmp_path),
        secret_lookup=lookup,
        artifact_validator=lambda _symbol, _run_id: None,
        broker_config_loader=_paper_broker,
    ).run()

    payload = json.dumps(report.to_dict())
    assert "unknown-secret-value" not in payload
    assert "MASSIVE_API_KEY lookup failed" in payload
    assert "RuntimeError" in payload


def test_production_preflight_redacts_secret_from_failure_and_exception(tmp_path) -> None:
    def reject_artifact(_symbol, _run_id):
        raise ValueError("artifact request included massive-secret-value")

    report = ProductionPreflight(
        _config(tmp_path),
        secret_lookup=_secrets(),
        artifact_validator=reject_artifact,
        broker_config_loader=_paper_broker,
    ).run()

    payload = json.dumps(report.to_dict())
    assert "massive-secret-value" not in payload
    assert "[REDACTED]" in payload
    with pytest.raises(ProductionPreflightError, match=r"\[REDACTED\]") as exc_info:
        report.raise_for_failure()
    assert "massive-secret-value" not in str(exc_info.value)


def test_production_preflight_rejects_broker_mode_mismatch(tmp_path) -> None:
    config = _config(
        tmp_path,
        mode=OperatingMode.LIVE,
        live_risk_acknowledgement="I_ACCEPT_LIVE_CAPITAL_RISK",
    )
    report = ProductionPreflight(
        config,
        secret_lookup=_secrets(),
        artifact_validator=lambda _symbol, _run_id: None,
        broker_config_loader=lambda _env_file: IBKRConnectionConfig(paper_trading=True),
    ).run()

    broker_check = next(check for check in report.checks if check.code == "broker.mode")
    assert broker_check.status is PreflightStatus.FAILED
    assert broker_check.metadata == {"production_mode": "live", "broker_mode": "paper"}


def test_production_preflight_fails_missing_explicit_broker_environment(tmp_path) -> None:
    report = ProductionPreflight(
        _config(tmp_path, broker_env_file=tmp_path / "missing.env"),
        secret_lookup=_secrets(),
        artifact_validator=lambda _symbol, _run_id: None,
        broker_config_loader=lambda _env_file: pytest.fail("loader must not run"),
    ).run()

    environment = next(check for check in report.checks if check.code == "broker.environment")
    mode = next(check for check in report.checks if check.code == "broker.mode")
    assert environment.status is PreflightStatus.FAILED
    assert mode.status is PreflightStatus.SKIPPED


def test_daemon_failed_preflight_does_not_construct_infrastructure(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "production.json"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "symbols": ["AAPL"],
                "artifact_root": str(artifact_root),
                "promoted_run_ids": {"AAPL": "missing-run"},
                "database_path": str(tmp_path / "runtime.sqlite3"),
                "broker_env_file": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("l1_microstructure.production.daemon.get_secret", lambda _name: None)
    monkeypatch.setattr(
        "l1_microstructure.production.daemon.MassiveWebSocketDataSource",
        lambda *_args, **_kwargs: pytest.fail("market-data source must not be constructed"),
    )
    monkeypatch.setattr(
        "l1_microstructure.production.daemon.IBKRBrokerOrderRouter.from_env",
        lambda *_args, **_kwargs: pytest.fail("broker router must not be constructed"),
    )

    with pytest.raises(ProductionPreflightError):
        main(["--config", str(config_path)])
