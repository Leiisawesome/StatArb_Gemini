"""Read-only, redacted production startup preflight."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from typing import Any, Callable

from l1_microstructure.artifacts import ArtifactBundleSelector, LocalArtifactStore, RunQualityGate
from l1_microstructure.live.broker_models import IBKRConnectionConfig
from l1_microstructure.live.router_adapters import load_ibkr_connection_config
from l1_microstructure.transparent.artifacts import TransparentArtifactSelector

from .config import OperatingMode, ProductionConfig


class PreflightStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    code: str
    status: PreflightStatus
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "status": self.status.value,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ProductionPreflightReport:
    checks: tuple[PreflightCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.status is not PreflightStatus.FAILED for check in self.checks)

    @property
    def failed_checks(self) -> tuple[PreflightCheck, ...]:
        return tuple(check for check in self.checks if check.status is PreflightStatus.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }

    def raise_for_failure(self) -> None:
        if not self.passed:
            raise ProductionPreflightError(self)


class ProductionPreflightError(RuntimeError):
    def __init__(self, report: ProductionPreflightReport) -> None:
        summary = "; ".join(f"{check.code}: {check.message}" for check in report.failed_checks)
        super().__init__(f"production preflight failed: {summary}")
        self.report = report


ArtifactValidator = Callable[[str, str], None]
BrokerConfigLoader = Callable[[str | None], IBKRConnectionConfig]
SecretLookup = Callable[[str], str | None]


class ProductionPreflight:
    REQUIRED_SECRETS = ("MASSIVE_API_KEY", "TRADING_CONSOLE_TOKEN")

    def __init__(
        self,
        config: ProductionConfig,
        *,
        secret_lookup: SecretLookup,
        artifact_validator: ArtifactValidator | None = None,
        broker_config_loader: BrokerConfigLoader = load_ibkr_connection_config,
    ) -> None:
        self.config = config
        self.secret_lookup = secret_lookup
        self.artifact_validator = artifact_validator or self._validate_artifact
        self.broker_config_loader = broker_config_loader
        self._secret_values: set[str] = set()

    def run(self) -> ProductionPreflightReport:
        self._secret_values.clear()
        checks: list[PreflightCheck] = []
        self._check_credentials(checks)
        self._check_runtime_configuration(checks)
        artifact_root_ready = self._check_artifact_root(checks)
        self._check_artifacts(checks, artifact_root_ready)
        self._check_database_path(checks)
        self._check_broker_configuration(checks)
        self._check_retry_policies(checks)
        return ProductionPreflightReport(tuple(checks))

    def _check_credentials(self, checks: list[PreflightCheck]) -> None:
        resolved: dict[str, str | None] = {}
        errors: dict[str, Exception] = {}
        for name in self.REQUIRED_SECRETS:
            try:
                resolved[name] = self.secret_lookup(name)
            except Exception as exc:
                errors[name] = exc
        self._secret_values.update(value for value in resolved.values() if isinstance(value, str) and value)

        for name in self.REQUIRED_SECRETS:
            if name in errors:
                checks.append(
                    PreflightCheck(
                        code=f"credential.{name.lower()}",
                        status=PreflightStatus.FAILED,
                        message=f"{name} lookup failed",
                        metadata={"configured": False, "error_type": type(errors[name]).__name__},
                    )
                )
                continue
            value = resolved.get(name)
            if isinstance(value, str) and value.strip():
                checks.append(
                    PreflightCheck(
                        code=f"credential.{name.lower()}",
                        status=PreflightStatus.PASSED,
                        message=f"{name} is configured",
                        metadata={"configured": True},
                    )
                )
            else:
                checks.append(
                    PreflightCheck(
                        code=f"credential.{name.lower()}",
                        status=PreflightStatus.FAILED,
                        message=f"{name} is not configured",
                        metadata={"configured": False},
                    )
                )

    def _check_runtime_configuration(self, checks: list[PreflightCheck]) -> None:
        checks.append(
            PreflightCheck(
                code="runtime.configuration",
                status=PreflightStatus.PASSED,
                message="production configuration is structurally valid",
                metadata={
                    "mode": self.config.mode.value,
                    "symbol_count": len(self.config.symbols),
                    "api_host": self.config.api_host,
                    "api_port": self.config.api_port,
                },
            )
        )

    def _check_artifact_root(self, checks: list[PreflightCheck]) -> bool:
        root = self.config.artifact_root
        ready = root.exists() and root.is_dir() and os.access(root, os.R_OK)
        checks.append(
            PreflightCheck(
                code="artifact.root",
                status=PreflightStatus.PASSED if ready else PreflightStatus.FAILED,
                message="artifact root is readable" if ready else "artifact root does not exist or is not a directory",
                metadata={"path": str(root)},
            )
        )
        return ready

    def _check_artifacts(self, checks: list[PreflightCheck], artifact_root_ready: bool) -> None:
        for symbol in self.config.symbols:
            code = f"artifact.promoted.{symbol.lower()}"
            run_id = self.config.promoted_run_ids[symbol]
            if not artifact_root_ready:
                checks.append(
                    PreflightCheck(
                        code=code,
                        status=PreflightStatus.SKIPPED,
                        message="artifact validation skipped because the artifact root is unavailable",
                        metadata={"symbol": symbol, "run_id": run_id},
                    )
                )
                continue
            try:
                self.artifact_validator(symbol, run_id)
            except Exception as exc:
                self._append_failure(checks, code, exc, {"symbol": symbol, "run_id": run_id})
            else:
                checks.append(
                    PreflightCheck(
                        code=code,
                        status=PreflightStatus.PASSED,
                        message="promoted artifact bundle is committed and validation-approved",
                        metadata={"symbol": symbol, "run_id": run_id},
                    )
                )
        for symbol, run_id in self.config.transparent_shadow_run_ids.items():
            code = f"artifact.transparent_shadow.{symbol.lower()}"
            if not artifact_root_ready:
                checks.append(
                    PreflightCheck(
                        code=code,
                        status=PreflightStatus.SKIPPED,
                        message="transparent artifact validation skipped because the artifact root is unavailable",
                        metadata={"symbol": symbol, "run_id": run_id},
                    )
                )
                continue
            try:
                TransparentArtifactSelector(LocalArtifactStore(self.config.artifact_root)).resolve(
                    symbol=symbol,
                    run_id=run_id,
                    passing_only=True,
                )
            except Exception as exc:
                self._append_failure(checks, code, exc, {"symbol": symbol, "run_id": run_id})
            else:
                checks.append(
                    PreflightCheck(
                        code=code,
                        status=PreflightStatus.PASSED,
                        message="transparent shadow bundle is validation-approved",
                        metadata={"symbol": symbol, "run_id": run_id, "engine_version": "v2"},
                    )
                )

    def _check_database_path(self, checks: list[PreflightCheck]) -> None:
        target_parent = self.config.database_path.parent
        existing_parent = target_parent
        while not existing_parent.exists() and existing_parent != existing_parent.parent:
            existing_parent = existing_parent.parent
        writable = existing_parent.is_dir() and os.access(existing_parent, os.W_OK)
        checks.append(
            PreflightCheck(
                code="filesystem.database",
                status=PreflightStatus.PASSED if writable else PreflightStatus.FAILED,
                message="database location is writable" if writable else "database location is not writable",
                metadata={"path": str(self.config.database_path)},
            )
        )

    def _check_broker_configuration(self, checks: list[PreflightCheck]) -> None:
        env_file = self.config.broker_env_file
        if env_file is not None and (not env_file.exists() or not env_file.is_file()):
            checks.append(
                PreflightCheck(
                    code="broker.environment",
                    status=PreflightStatus.FAILED,
                    message="configured broker environment file does not exist",
                    metadata={"path": str(env_file)},
                )
            )
            checks.append(
                PreflightCheck(
                    code="broker.mode",
                    status=PreflightStatus.SKIPPED,
                    message="broker mode validation skipped because broker configuration is unavailable",
                )
            )
            checks.append(
                PreflightCheck(
                    code="broker.account",
                    status=PreflightStatus.SKIPPED,
                    message="broker account validation skipped because broker configuration is unavailable",
                )
            )
            checks.append(
                PreflightCheck(
                    code="broker.outside_rth",
                    status=PreflightStatus.SKIPPED,
                    message="outside-RTH validation skipped because broker configuration is unavailable",
                )
            )
            return
        checks.append(
            PreflightCheck(
                code="broker.environment",
                status=PreflightStatus.PASSED,
                message="broker configuration source is available",
                metadata={"source": "environment" if env_file is None else str(env_file)},
            )
        )
        try:
            broker = self.broker_config_loader(str(env_file) if env_file is not None else None)
            if not isinstance(broker, IBKRConnectionConfig):
                raise TypeError("broker configuration loader returned an invalid result")
        except Exception as exc:
            self._append_failure(checks, "broker.mode", exc)
            checks.append(
                PreflightCheck(
                    code="broker.account",
                    status=PreflightStatus.SKIPPED,
                    message="broker account validation skipped because broker configuration is invalid",
                )
            )
            checks.append(
                PreflightCheck(
                    code="broker.outside_rth",
                    status=PreflightStatus.SKIPPED,
                    message="outside-RTH validation skipped because broker configuration is invalid",
                )
            )
            return
        expected_paper = self.config.mode is OperatingMode.PAPER
        if broker.paper_trading != expected_paper:
            checks.append(
                PreflightCheck(
                    code="broker.mode",
                    status=PreflightStatus.FAILED,
                    message=(f"broker account mode does not match production mode {self.config.mode.value}"),
                    metadata={
                        "production_mode": self.config.mode.value,
                        "broker_mode": "paper" if broker.paper_trading else "live",
                    },
                )
            )
            return
        checks.append(
            PreflightCheck(
                code="broker.mode",
                status=PreflightStatus.PASSED,
                message="broker account mode matches production mode",
                metadata={
                    "production_mode": self.config.mode.value,
                    "broker_mode": "paper" if broker.paper_trading else "live",
                    "host": broker.host,
                    "port": broker.port,
                    "client_id": broker.client_id,
                },
            )
        )
        account_configured = bool(broker.account_id and broker.account_id.strip())
        checks.append(
            PreflightCheck(
                code="broker.account",
                status=PreflightStatus.PASSED if account_configured else PreflightStatus.FAILED,
                message=(
                    "a broker account is explicitly configured"
                    if account_configured
                    else "IBKR_ACCOUNT_ID is not configured"
                ),
                metadata={"configured": account_configured},
            )
        )
        outside_rth_disabled = not broker.outside_regular_trading_hours
        checks.append(
            PreflightCheck(
                code="broker.outside_rth",
                status=(
                    PreflightStatus.PASSED
                    if outside_rth_disabled
                    else PreflightStatus.FAILED
                ),
                message=(
                    "outside-RTH order routing is disabled"
                    if outside_rth_disabled
                    else "IBKR_OUTSIDE_RTH must be disabled for the paper campaign"
                ),
                metadata={"enabled": broker.outside_regular_trading_hours},
            )
        )

    def _check_retry_policies(self, checks: list[PreflightCheck]) -> None:
        policies = {
            "market_data": self.config.retry.market_data,
            "broker_connection": self.config.retry.broker_connection,
            "broker_read": self.config.retry.broker_read,
        }
        checks.append(
            PreflightCheck(
                code="runtime.retry_policies",
                status=PreflightStatus.PASSED,
                message="operation-specific retry policies are valid",
                metadata={
                    name: {
                        "max_attempts": policy.max_attempts,
                        "maximum_delay_seconds": policy.maximum_delay_seconds,
                    }
                    for name, policy in policies.items()
                },
            )
        )

    def _validate_artifact(self, symbol: str, run_id: str) -> None:
        policy = self.config.model_quality
        selector = ArtifactBundleSelector(LocalArtifactStore(self.config.artifact_root, create=False))
        selector.resolve_passing_by_run_id(
            symbol=symbol,
            run_id=run_id,
            quality_gate=RunQualityGate(
                minimum_fill_rate=policy.minimum_fill_rate,
                maximum_cancel_rate=policy.maximum_cancel_rate,
                maximum_drift_tracking_error_bps=policy.maximum_drift_tracking_error_bps,
                maximum_unseen_edge_rate=policy.maximum_unseen_edge_rate,
            ),
        )

    def _append_failure(
        self,
        checks: list[PreflightCheck],
        code: str,
        error: Exception,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        checks.append(
            PreflightCheck(
                code=code,
                status=PreflightStatus.FAILED,
                message=self._redact(str(error) or type(error).__name__),
                metadata=dict(metadata or {}),
            )
        )

    def _redact(self, message: str) -> str:
        redacted = message
        for value in sorted(self._secret_values, key=len, reverse=True):
            redacted = redacted.replace(value, "[REDACTED]")
        return redacted
