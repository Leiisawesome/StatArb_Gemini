"""Source-backed entrypoints for replay and streaming paper execution."""

from __future__ import annotations

from dataclasses import dataclass

from l1_microstructure.artifacts import ArtifactBundleSelector, RunQualityGate, RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest.interfaces import HistoricalBatchRequest, LiveSubscriptionRequest, MarketDataSource
from l1_microstructure.monitoring import InMemoryMonitoringSink

from .interfaces import RunnerConfig
from .paper import SimulatorPaperTradingRunner


@dataclass(slots=True)
class SourceBackedPaperRunner:
    source: MarketDataSource
    framework_config: FrameworkConfig | None = None
    monitoring_sink: InMemoryMonitoringSink | None = None
    bundle_selector: ArtifactBundleSelector | None = None
    require_validation_passed: bool = False
    quality_gate: RunQualityGate | None = None

    def run_historical(
        self,
        request: HistoricalBatchRequest,
        config: RunnerConfig,
        run_id: str | None = None,
    ) -> SimulatorPaperTradingRunner:
        events = list(self.source.load_historical(request))
        return self._run_events(events, config, run_id=run_id, trade_date=request.trade_date.isoformat())

    def run_live(
        self,
        request: LiveSubscriptionRequest,
        config: RunnerConfig,
        run_id: str | None = None,
    ) -> SimulatorPaperTradingRunner:
        events = list(self.source.subscribe_live(request))
        return self._run_events(events, config, run_id=run_id, trade_date=None)

    def _run_events(
        self,
        events: list,
        config: RunnerConfig,
        run_id: str | None,
        trade_date: str | None,
    ) -> SimulatorPaperTradingRunner:
        runtime_artifacts = RuntimeArtifactBundle()
        if self.bundle_selector is not None:
            if len(config.symbols) != 1:
                raise ValueError("artifact-resolved source-backed runner currently supports exactly one symbol")
            symbol = config.symbols[0]
            if run_id is None and trade_date is not None:
                if self.require_validation_passed:
                    runtime_artifacts = self.bundle_selector.resolve_passing_for_symbol_on_date(
                        symbol=symbol,
                        trade_date=trade_date,
                        quality_gate=self.quality_gate,
                    )
                else:
                    runtime_artifacts = self.bundle_selector.resolve_for_symbol_on_date(symbol=symbol, trade_date=trade_date)
            elif run_id is None:
                if self.require_validation_passed:
                    runtime_artifacts = self.bundle_selector.resolve_latest_passing_for_symbol(
                        symbol,
                        quality_gate=self.quality_gate,
                    )
                else:
                    runtime_artifacts = self.bundle_selector.resolve_latest_for_symbol(symbol)
            else:
                runtime_artifacts = self.bundle_selector.resolve_by_run_id(symbol=symbol, run_id=run_id)

        runner = SimulatorPaperTradingRunner(
            events=events,
            framework_config=self.framework_config,
            runtime_artifacts=runtime_artifacts,
            monitoring_sink=self.monitoring_sink,
        )
        runner.start(config)
        return runner