"""
ComponentFactory (Papertest)
============================

Wires core_engine components into core_engine.paper.PaperTradingEngine.

V1 constraint: thin runner around PaperTradingEngine (no HierarchicalSystemOrchestrator).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from core_engine.paper.engine import PaperTradingEngine, PaperTradingConfig

from core_engine.system.time_source import TimeSourceFactory
from core_engine.system.event_dispatcher import DeterministicEventDispatcher
from core_engine.system.event_dispatcher import EventType
from core_engine.system.event_journal import EventJournal
from core_engine.system.paper_state_manager import PaperSessionStateManager
from core_engine.system.paper_watchdog import PaperTradingWatchdog
from core_engine.system.idempotency import IdGenerator, IdempotencyTracker
from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.session_gate import TradingSessionGate
from core_engine.system.risk_budget import RiskBudgetState
from core_engine.system.order_management_system import OrderManagementSystem
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine

from core_engine.data.replay.config import ReplaySpeed, ReplayConfig
from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter
from core_engine.data.validation.streaming_validator import StreamingDataValidator
from core_engine.processing.streaming.buffer_manager import StreamingBufferManager
from core_engine.processing.streaming.adapters import StreamingIndicatorAdapter, StreamingFeatureAdapter
from core_engine.processing.signals.streaming_manager import StreamingSignalManager, BarPolicy

from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.strategies.manager import StrategyManager

from core_engine.broker.adapters.paper_adapter import PaperBrokerAdapter

logger = logging.getLogger(__name__)


@dataclass
class WiredPaperSystem:
    engine: PaperTradingEngine
    replay_adapter: HistoricalReplayFeedAdapter
    dispatcher: DeterministicEventDispatcher
    id_generator: IdGenerator
    components: Dict[str, Any]


def _parse_replay_speed(name: str) -> ReplaySpeed:
    try:
        return ReplaySpeed[name]
    except Exception:
        return ReplaySpeed.REALTIME


class ComponentFactory:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def build(self) -> WiredPaperSystem:
        pt = self.config["papertest"]

        session_cfg = pt.get("session", {})
        data_cfg = pt.get("data", {})
        buffers_cfg = pt.get("buffers", {})
        dispatcher_cfg = pt.get("dispatcher", {})
        risk_cfg = pt.get("risk", {})
        exec_cfg = pt.get("execution", {})
        regime_cfg = pt.get("regime", {}) or {}

        # EOD Liquidation settings (extract from first strategy if available)
        enable_eod = False
        eod_time = "15:55"
        strategies = pt.get("strategies", [])
        if strategies:
            params = strategies[0].get("parameters", {})
            enable_eod = bool(params.get("enable_eod_liquidation", False))
            eod_time = str(params.get("eod_close_time", "15:55"))

        # Session ids
        session_prefix = session_cfg.get("id_prefix", "pt")
        paper_cfg = PaperTradingConfig(
            session_id="",  # let PaperTradingEngine generate
            buffer_size=int(buffers_cfg.get("size", 500)),
            warmup_required=int(buffers_cfg.get("warmup_required", 200)),
            checkpoint_interval_bars=int(session_cfg.get("checkpoint_interval_bars", 1000)),
            checkpoint_dir=str(session_cfg.get("checkpoint_dir", "papertest/results/checkpoints")),
            journal_dir=str(session_cfg.get("journal_dir", "papertest/results/journals")),
            daily_risk_budget_pct=float(risk_cfg.get("daily_risk_budget_pct", 0.01)),
            per_trade_risk_pct=float(risk_cfg.get("per_trade_risk_pct", 0.005)),
            initial_cash=float(exec_cfg.get("initial_cash", 100_000.0)),
            commission_per_share=float(exec_cfg.get("commission_per_share", 0.005)),
            stall_threshold_seconds=float(session_cfg.get("stall_threshold_seconds", 60.0)),
            enable_eod_liquidation=enable_eod,
            eod_close_time=eod_time,
            # Default: causal-only streaming regime.
            # Parity mode (HistoricalExecutionSimulator): disable confirmation lag to match BT semantics.
            enable_causal_only_regime=(
                bool(regime_cfg.get("enable_causal_only_mode", True))
                if not bool(exec_cfg.get("use_historical_execution_simulator", False))
                else bool(regime_cfg.get("enable_causal_only_mode_for_parity", False))
            ),
        )

        engine = PaperTradingEngine(paper_cfg)

        # Deterministic IDs
        id_gen = IdGenerator("papertest", f"{session_prefix}:{engine._session_id}")
        id_tracker = IdempotencyTracker(max_history=100_000)

        # Time + dispatcher
        # Ensure replay market time never needs to move backwards (replay data is historical)
        from datetime import datetime, timezone
        time_source = TimeSourceFactory.create_replay(initial_time=datetime(1970, 1, 1, tzinfo=timezone.utc))
        dispatcher = DeterministicEventDispatcher(
            time_source=time_source,
            max_queue_size=int(dispatcher_cfg.get("max_queue_size", 10000)),
            bar_queue_size=int(dispatcher_cfg.get("bar_queue_size", 1000)),
            conflate_quotes=bool(dispatcher_cfg.get("conflate_quotes", True)),
        )

        # Data validation + buffers
        validator = StreamingDataValidator()
        buffer_manager = StreamingBufferManager(
            buffer_size=int(buffers_cfg.get("size", 500)),
            warmup_required=int(buffers_cfg.get("warmup_required", 200)),
        )

        # Indicators/features
        indicators_engine = EnhancedTechnicalIndicators()
        indicator_adapter = StreamingIndicatorAdapter(indicators_engine)

        feature_engine = EnhancedFeatureEngineer()
        feature_adapter = StreamingFeatureAdapter(feature_engine)

        # Signals + bar policy
        bar_policy = BarPolicy()
        signal_manager = StreamingSignalManager(bar_policy=bar_policy, session_id=engine._session_id)

        # Regime + strategy
        # Regime config: in parity mode, use backtest-aligned defaults unless overridden.
        regime_cfg_effective = dict(regime_cfg or {})
        if bool(exec_cfg.get("use_historical_execution_simulator", False)):
            regime_cfg_effective.setdefault("lookback_window", 60)
            regime_cfg_effective.setdefault("volatility_window", 20)
            regime_cfg_effective.setdefault("trend_threshold", 0.02)
            regime_cfg_effective.setdefault("regime_change_threshold", 0.7)
            regime_cfg_effective.setdefault("update_frequency", 60)
            regime_cfg_effective.setdefault("enable_enhanced_detection", True)
            # Important: parity should not depend on the fast incremental evaluator unless BT also uses it.
            regime_cfg_effective["enable_per_bar_fast"] = False

        regime_engine = EnhancedRegimeEngine(regime_cfg_effective)
        strategy_manager = StrategyManager(config={}, data_config=None)

        # Risk governance
        session_gate = TradingSessionGate()
        risk_budget = RiskBudgetState(
            daily_risk_budget_pct=float(risk_cfg.get("daily_risk_budget_pct", 0.01)),
            per_trade_risk_pct=float(risk_cfg.get("per_trade_risk_pct", 0.005)),
        )
        # OMS + execution + broker
        oms = OrderManagementSystem({})

        # Pass sizing/threshold limits through to CentralRiskManager (alignable with backtest YAML)
        risk_manager = CentralRiskManager(
            {
                "allow_shorts": bool(risk_cfg.get("allow_shorts", False)),
                "min_signal_confidence": float(risk_cfg.get("min_signal_confidence", 0.60)),
                "max_position_size": float(risk_cfg.get("max_position_size", 0.10)),
                "max_position_pct": float(risk_cfg.get("max_position_pct", 0.05)),
                "max_positions": int(risk_cfg.get("max_positions", 5)),
                "position_concentration_limit": float(risk_cfg.get("position_concentration_limit", 0.15)),
                "initial_capital": float(exec_cfg.get("initial_cash", 100_000.0)),
            }
        )
        risk_manager.set_session_gate(session_gate)
        risk_manager.set_risk_budget(risk_budget)
        # Ensure risk manager can account for pending exposure (OMS) in Gate 3
        risk_manager.set_oms(oms)

        execution_engine = UnifiedExecutionEngine({"test_mode": bool(exec_cfg.get("test_mode", True))})
        paper_broker = PaperBrokerAdapter(
            initial_cash=float(exec_cfg.get("initial_cash", 100_000.0)),
            commission_per_share=float(exec_cfg.get("commission_per_share", 0.005)),
            latency_ms_min=float(exec_cfg.get("latency_ms_min", 50.0)),
            latency_ms_max=float(exec_cfg.get("latency_ms_max", 200.0)),
            min_commission=float(exec_cfg.get("min_commission", 1.0)),
            fill_probability=float(exec_cfg.get("fill_probability", 0.95)),
            partial_fill_probability=float(exec_cfg.get("partial_fill_probability", 0.10)),
            slippage_bps_max=float(exec_cfg.get("slippage_bps_max", 5.0)),
            impact_coefficient=float(exec_cfg.get("impact_coefficient", 10.0)),
            seed=(int(exec_cfg["seed"]) if "seed" in exec_cfg and exec_cfg["seed"] is not None else None),
            use_historical_execution_simulator=bool(exec_cfg.get("use_historical_execution_simulator", False)),
        )
        # Critical for replay: fills must be timestamped with market_now(), not wall_now()
        if hasattr(paper_broker, "set_time_source"):
            try:
                paper_broker.set_time_source(time_source)
            except Exception:
                pass
        execution_engine.set_paper_broker(paper_broker)
        execution_engine.set_execution_mode("PAPER")

        # Fill callback -> deterministic FILL events (journal/risk updates)
        def _on_fill(fill: Any) -> None:
            try:
                payload = {
                    "fill_id": getattr(fill, "fill_id", ""),
                    "order_id": getattr(fill, "order_id", ""),
                    "symbol": getattr(fill, "symbol", ""),
                    "side": getattr(fill, "side", ""),
                    "quantity": getattr(fill, "quantity", 0),
                    "price": getattr(fill, "price", 0),
                    "commission": getattr(fill, "commission", 0),
                    "timestamp": getattr(fill, "timestamp", None),
                }
                # Optional debug fields (only present when using HistoricalExecutionSimulator)
                for k in (
                    "_debug_regime_volatility_regime",
                    "_debug_regime_primary_regime",
                    "_debug_total_cost_bps",
                    "_debug_spread_cost_bps",
                    "_debug_market_impact_bps",
                    "_debug_slippage_bps",
                    "_debug_commission_bps",
                    "_debug_market_volume",
                    "_debug_market_volatility",
                ):
                    if hasattr(fill, k):
                        payload[k] = getattr(fill, k)
                dispatcher.enqueue(
                    event_type=EventType.FILL,
                    payload=payload,
                    market_timestamp=getattr(fill, "timestamp", None),
                    symbol=getattr(fill, "symbol", None),
                    event_id=getattr(fill, "fill_id", None),
                )
            except Exception:
                return

        paper_broker.set_fill_callback(_on_fill)

        # Ops: journal/state/watchdog
        journal = EventJournal(
            session_id=engine._session_id,
            output_dir=str(paper_cfg.journal_dir),
            compress=bool(session_cfg.get("journal_compress", False)),
        )
        state_mgr = PaperSessionStateManager(
            session_id=engine._session_id,
            checkpoint_dir=paper_cfg.checkpoint_dir,
            checkpoint_interval_bars=paper_cfg.checkpoint_interval_bars,
        )
        watchdog = PaperTradingWatchdog(stall_threshold_seconds=paper_cfg.stall_threshold_seconds)

        # Replay adapter
        replay_speed = _parse_replay_speed(str(data_cfg.get("replay_speed", "REALTIME")))
        replay_cfg = ReplayConfig.create_for_symbols(
            symbols=list(data_cfg["symbols"]),
            start_date=str(data_cfg["start_date"]),
            end_date=str(data_cfg["end_date"]),
            speed=replay_speed,
            interval=str(data_cfg.get("interval", "1min")),
        ).copy(simulate_market_hours=bool(data_cfg.get("simulate_market_hours", True)))
        replay_adapter = HistoricalReplayFeedAdapter(replay_cfg)

        # Wire into engine
        engine.setup_time_source(time_source)
        engine.setup_dispatcher(dispatcher)
        engine.setup_data_validator(validator)
        engine.setup_buffer_manager(buffer_manager)
        engine.setup_indicator_adapter(indicator_adapter)
        engine.setup_feature_adapter(feature_adapter)
        engine.setup_signal_manager(signal_manager)
        engine.setup_regime_engine(regime_engine)
        engine.setup_session_gate(session_gate)
        engine.setup_risk_manager(risk_manager)
        engine.setup_risk_budget(risk_budget)
        engine.setup_paper_broker(paper_broker)
        engine.setup_execution_engine(execution_engine)
        engine.setup_event_journal(journal)
        engine.setup_state_manager(state_mgr)
        engine.setup_idempotency_tracker(id_tracker)
        engine.setup_watchdog(watchdog)
        engine.setup_replay_adapter(replay_adapter)

        # Strategy manager is wired later by papertest patches to PaperTradingEngine
        if hasattr(engine, "setup_strategy_manager"):
            engine.setup_strategy_manager(strategy_manager)
        if hasattr(engine, "setup_oms"):
            engine.setup_oms(oms)

        return WiredPaperSystem(
            engine=engine,
            replay_adapter=replay_adapter,
            dispatcher=dispatcher,
            id_generator=id_gen,
            components={
                "time_source": time_source,
                "dispatcher": dispatcher,
                "validator": validator,
                "buffer_manager": buffer_manager,
                "indicator_engine": indicators_engine,
                "indicator_adapter": indicator_adapter,
                "feature_engine": feature_engine,
                "feature_adapter": feature_adapter,
                "signal_manager": signal_manager,
                "regime_engine": regime_engine,
                "strategy_manager": strategy_manager,
                "session_gate": session_gate,
                "risk_budget": risk_budget,
                "risk_manager": risk_manager,
                "oms": oms,
                "execution_engine": execution_engine,
                "paper_broker": paper_broker,
                "journal": journal,
                "state_manager": state_mgr,
                "idempotency_tracker": id_tracker,
                "watchdog": watchdog,
            },
        )


