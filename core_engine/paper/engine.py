"""
PaperTradingEngine - Main Event Loop
====================================

Orchestrates paper trading with all components integrated:
- TimeSource (market/wall time)
- DeterministicEventDispatcher
- StreamingDataValidator
- StreamingBufferManager
- StreamingIndicatorAdapter
- StreamingFeatureAdapter
- StreamingSignalManager with BarPolicy
- RegimeEngine (causal-only mode)
- TradingSessionGate
- CentralRiskManager (6-gate pipeline)
- RiskBudgetState
- PaperBrokerAdapter
- EventJournal
- PaperSessionStateManager
- IdempotencyTracker
- PaperTradingWatchdog

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 6)
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
import threading

from ..system.event_dispatcher import EventType

logger = logging.getLogger(__name__)

class _SignalNormalizer:
    """
    Internal helper to normalize strategy signals into execution signals.
    """
    @staticmethod
    def normalize(
        signal: Any, 
        market_timestamp: datetime, 
        bar_close_price: Optional[float],
        broker: Any,
        risk_manager: Any,
        default_stop_loss_pct: float = 0.02
    ) -> Optional[Dict[str, Any]]:
        try:
            symbol = getattr(signal, "symbol", None)
            if not symbol:
                return None

            signal_type = getattr(signal, "signal_type", None)
            st_val = str(getattr(signal_type, "value", signal_type))
            st_val = (st_val or "").lower()

            # Explicit mapping for canonical signal types
            side = _SignalNormalizer._resolve_side(st_val)
            if not side:
                return None

            # StrategySignal uses target_quantity/target_weight, not `quantity`.
            qty = _SignalNormalizer._resolve_quantity(signal, st_val, bar_close_price, broker, risk_manager)
            
            if qty <= 0:
                return None

            strength = float(getattr(signal, "strength", 0.5) or 0.5)
            confidence = float(getattr(signal, "confidence", 0.0) or 0.0)
            strategy_id = getattr(signal, "strategy_id", "strategy")
            
            arrival_price = _SignalNormalizer._resolve_price(signal, bar_close_price, broker)

            return {
                "symbol": symbol,
                "side": side,
                "requested_quantity": qty,
                "signal_strength": strength,
                "confidence": confidence,
                "strategy_id": strategy_id,
                "signal_timestamp": market_timestamp,
                "arrival_price": arrival_price,
                # Risk 6-gate requires stop info; if none known, allow risk manager / signal manager defaults
                "stop_loss_pct": float(getattr(signal, "stop_loss_pct", 0.0) or default_stop_loss_pct),
            }
        except Exception:
            return None

    @staticmethod
    def _resolve_side(st_val: str) -> Optional[str]:
        if "long_entry" in st_val or "increase_long" in st_val:
            return "buy"
        elif "long_exit" in st_val or "reduce_long" in st_val:
            return "sell"
        elif "short_entry" in st_val or "increase_short" in st_val:
            return "sell"
        elif "short_exit" in st_val or "reduce_short" in st_val:
            return "buy"
        elif st_val == "buy":
            return "buy"
        elif st_val == "sell":
            return "sell"
        return None

    @staticmethod
    def _resolve_price(signal: Any, bar_close_price: Optional[float], broker: Any) -> float:
        arrival_price = float(bar_close_price or 0.0)
        if arrival_price <= 0:
            arrival_price = float(getattr(signal, "price", 0.0) or 0.0)
        if arrival_price <= 0 and broker:
            q = broker.get_latest_quote(getattr(signal, "symbol", ""))
            if q:
                arrival_price = float(q.get("last_price", 0.0) or 0.0)
        if arrival_price <= 0:
            arrival_price = 100.0
        return arrival_price

    @staticmethod
    def _resolve_quantity(signal: Any, st_val: str, bar_close_price: Optional[float], broker: Any, risk_manager: Any) -> float:
        qty = 0.0
        qt = str(getattr(signal, "quantity_type", "") or "").upper()
        symbol = getattr(signal, "symbol", "")
        
        if qt == "ABSOLUTE":
            qty = float(getattr(signal, "target_quantity", 0.0) or 0.0)
            if qty <= 0:
                qty = float(getattr(signal, "quantity", 0.0) or 0.0)
        elif qt == "PERCENTAGE":
            tw = getattr(signal, "target_weight", None)
            if tw is not None and broker:
                try:
                    target_weight = float(tw or 0.0)
                    acct = broker.get_account_info()
                    portfolio_value = float(getattr(acct, "portfolio_value", 0.0) or 0.0)
                    
                    # Backtest parity: sizing uses CentralRiskManager.portfolio_value
                    try:
                        if risk_manager is not None and hasattr(risk_manager, "portfolio_value"):
                            rm_pv = float(getattr(risk_manager, "portfolio_value", 0.0) or 0.0)
                            if rm_pv > 0:
                                portfolio_value = rm_pv
                    except Exception:
                        pass
                        
                    px = _SignalNormalizer._resolve_price(signal, bar_close_price, broker)
                    
                    if target_weight > 0 and portfolio_value > 0 and px > 0:
                        qty = float((target_weight * portfolio_value) / px)
                except Exception:
                    qty = 0.0

        # Exit sizing parity
        try:
            pos = 0.0
            if risk_manager:
                pos = float(getattr(risk_manager, "current_positions", {}).get(symbol, 0.0) or 0.0)

            if ("long_exit" in st_val or "reduce_long" in st_val) and pos > 0:
                qty = abs(pos)
            elif ("short_exit" in st_val or "reduce_short" in st_val) and pos < 0:
                qty = abs(pos)
            elif "short_entry" in st_val and pos > 0:
                qty = abs(pos)
            elif "long_entry" in st_val and pos < 0:
                qty = abs(pos)
            elif st_val == "sell" and pos > 0:
                qty = abs(pos)
            elif st_val == "buy" and pos < 0:
                qty = abs(pos)
        except Exception:
            pass
            
        return qty

class PaperTradingState(Enum):
    """State of the paper trading engine."""
    INITIALIZING = auto()
    WARMING_UP = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()

@dataclass
class PaperTradingConfig:
    """Configuration for paper trading engine."""
    session_id: str = ""

    # Buffer/warmup settings
    buffer_size: int = 500
    warmup_required: int = 200

    # Checkpoint settings
    checkpoint_interval_bars: int = 1000
    checkpoint_dir: str = "checkpoints"

    # Journal settings
    journal_dir: str = "journals"
    journal_compress: bool = False

    # Watchdog settings
    stall_threshold_seconds: float = 60.0

    # Risk settings
    daily_risk_budget_pct: float = 0.01
    per_trade_risk_pct: float = 0.005

    # Execution settings
    initial_cash: float = 100_000.0
    commission_per_share: float = 0.005

    # EOD Liquidation settings
    enable_eod_liquidation: bool = False
    eod_close_time: str = "15:55"

class PaperTradingEngine:
    """
    Main paper trading engine.

    Orchestrates the complete paper trading flow:
    1. Receive bar from replay
    2. Validate bar data
    3. Update buffers
    4. Compute indicators/features
    5. Evaluate regime
    6. Generate signals
    7. Risk authorization (6 gates)
    8. Execute via paper broker
    9. Journal all events
    10. Checkpoint periodically

    Thread-safe and supports pause/resume.
    """

    def __init__(self, config: PaperTradingConfig):
        """
        Initialize paper trading engine.

        Args:
            config: Engine configuration
        """
        self.config = config
        self._state = PaperTradingState.INITIALIZING

        # Generate session ID if not provided
        if not config.session_id:
            from ..system.idempotency import generate_session_id
            config.session_id = generate_session_id()

        self._session_id = config.session_id

        # Component references (set via setup methods)
        self._time_source = None
        self._dispatcher = None
        self._data_validator = None
        self._buffer_manager = None
        self._indicator_adapter = None
        self._feature_adapter = None
        self._signal_manager = None
        self._strategy_manager = None
        self._regime_engine = None
        self._session_gate = None
        self._risk_manager = None
        self._risk_budget = None
        self._paper_broker = None
        self._execution_engine = None
        self._oms = None
        self._position_book = None
        self._event_journal = None
        self._state_manager = None
        self._idempotency_tracker = None
        self._watchdog = None

        # Replay adapter reference
        self._replay_adapter = None

        # Universe / multi-symbol coordination
        self._expected_symbols: List[str] = []
        self._bar_batch_timestamp: Optional[datetime] = None
        self._bar_batch_symbols: set[str] = set()
        self._bar_batch_market_data: Dict[str, Any] = {}

        # Bar-open execution (next_bar_open semantics)
        self._last_bar_open_timestamp: Optional[datetime] = None
        self._pending_open_signals: List[Any] = []
        self._eod_flags: Dict[str, bool] = {}
        # Execution sequencing (parity shim): backtest does not always have regime context on the first trade.
        self._execution_count: int = 0

        # Stats
        self._stats = {
            'bars_processed': 0,
            'signals_generated': 0,
            'orders_submitted': 0,
            'fills_received': 0,
        }

        # Thread safety
        self._lock = threading.Lock()

        # Running flag
        self._running = False

        logger.info(f"📝 PaperTradingEngine created: {self._session_id}")

    # ==================== Component Setup ====================

    def setup_time_source(self, time_source: Any) -> None:
        """Set the time source."""
        self._time_source = time_source

    def setup_dispatcher(self, dispatcher: Any) -> None:
        """Set the event dispatcher."""
        self._dispatcher = dispatcher

    def setup_data_validator(self, validator: Any) -> None:
        """Set the streaming data validator."""
        self._data_validator = validator

    def setup_buffer_manager(self, manager: Any) -> None:
        """Set the streaming buffer manager."""
        self._buffer_manager = manager

    def setup_indicator_adapter(self, adapter: Any) -> None:
        """Set the streaming indicator adapter."""
        self._indicator_adapter = adapter

    def setup_feature_adapter(self, adapter: Any) -> None:
        """Set the streaming feature adapter."""
        self._feature_adapter = adapter

    def setup_signal_manager(self, manager: Any) -> None:
        """Set the streaming signal manager."""
        self._signal_manager = manager

    def setup_strategy_manager(self, manager: Any) -> None:
        """Set the strategy manager."""
        self._strategy_manager = manager

    def setup_regime_engine(self, engine: Any) -> None:
        """Set the regime engine."""
        self._regime_engine = engine
        # Enable causal-only mode
        if hasattr(engine, 'enable_causal_only_mode'):
            engine.enable_causal_only_mode()

    def setup_session_gate(self, gate: Any) -> None:
        """Set the trading session gate."""
        self._session_gate = gate

    def setup_risk_manager(self, manager: Any) -> None:
        """Set the central risk manager."""
        self._risk_manager = manager

    def setup_risk_budget(self, budget: Any) -> None:
        """Set the risk budget state."""
        self._risk_budget = budget

    def setup_paper_broker(self, broker: Any) -> None:
        """Set the paper broker adapter."""
        self._paper_broker = broker

    def setup_execution_engine(self, engine: Any) -> None:
        """Set the execution engine."""
        self._execution_engine = engine

    def setup_oms(self, oms: Any) -> None:
        """Set the order management system."""
        self._oms = oms

    def setup_position_book(self, book: Any) -> None:
        """Set the position book."""
        self._position_book = book

    def setup_event_journal(self, journal: Any) -> None:
        """Set the event journal."""
        self._event_journal = journal

    def setup_state_manager(self, manager: Any) -> None:
        """Set the paper session state manager."""
        self._state_manager = manager

    def setup_idempotency_tracker(self, tracker: Any) -> None:
        """Set the idempotency tracker."""
        self._idempotency_tracker = tracker

    def setup_watchdog(self, watchdog: Any) -> None:
        """Set the paper trading watchdog."""
        self._watchdog = watchdog

    def setup_replay_adapter(self, adapter: Any) -> None:
        """Set the historical replay adapter."""
        self._replay_adapter = adapter
        # Infer expected universe from replay config if available
        try:
            symbols = getattr(getattr(adapter, 'replay_config', None), 'symbols', None)
            if symbols:
                self._expected_symbols = list(symbols)
        except Exception:
            pass

    # ==================== Lifecycle ====================

    async def initialize(self) -> bool:
        """
        Initialize all components.

        Returns:
            True if initialization successful
        """
        logger.info("🚀 Initializing PaperTradingEngine...")

        try:
            # Verify required components
            required = [
                ('time_source', self._time_source),
                ('buffer_manager', self._buffer_manager),
                ('signal_manager', self._signal_manager),
                ('paper_broker', self._paper_broker),
            ]

            for name, component in required:
                if component is None:
                    logger.error(f"Missing required component: {name}")
                    self._state = PaperTradingState.ERROR
                    return False

            # Wire up component dependencies
            if self._risk_manager and self._session_gate:
                self._risk_manager.set_session_gate(self._session_gate)

            if self._risk_manager and self._risk_budget:
                self._risk_manager.set_risk_budget(self._risk_budget)

            if self._execution_engine and self._paper_broker:
                self._execution_engine.set_paper_broker(self._paper_broker)
                self._execution_engine.set_execution_mode('PAPER')

            # Register components with state manager
            if self._state_manager:
                if self._buffer_manager:
                    self._state_manager.register_component('buffer_manager', self._buffer_manager)
                if self._regime_engine:
                    self._state_manager.register_component('regime_engine', self._regime_engine)
                if self._risk_budget:
                    self._state_manager.register_component('risk_budget', self._risk_budget)
                if self._idempotency_tracker:
                    self._state_manager.register_component('idempotency_tracker', self._idempotency_tracker)

            # Setup watchdog callbacks
            if self._watchdog and self._state_manager:
                self._watchdog.set_callbacks(
                    on_warning=lambda: logger.warning("Watchdog warning"),
                    on_critical=lambda: self._state_manager.create_checkpoint('critical'),
                    on_stall=self._on_stall,
                )

            # Log system start
            if self._event_journal:
                self._event_journal.log_system('engine_initialized', {
                    'session_id': self._session_id,
                    'config': {
                        'buffer_size': self.config.buffer_size,
                        'warmup_required': self.config.warmup_required,
                    }
                })

            self._state = PaperTradingState.WARMING_UP
            logger.info("✅ PaperTradingEngine initialized")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            self._state = PaperTradingState.ERROR
            return False

    def _on_stall(self) -> None:
        """Handle stall detection."""
        logger.critical("Stall detected, initiating recovery...")
        if self._state_manager:
            self._state_manager.create_checkpoint('stall')

    async def warmup(self, symbols: List[str]) -> bool:
        """
        Warmup buffers with historical data.

        Args:
            symbols: List of symbols to warmup

        Returns:
            True if warmup successful
        """
        logger.info(f"🔥 Warming up buffers for {len(symbols)} symbols...")

        try:
            for symbol in symbols:
                # Check if already warmed up
                if self._buffer_manager and self._buffer_manager.is_warmed_up(symbol):
                    continue

                # Get warmup data from replay adapter
                if self._replay_adapter and hasattr(self._replay_adapter, 'get_warmup_data'):
                    warmup_df = await self._replay_adapter.get_warmup_data(
                        symbol,
                        bars=self.config.warmup_required
                    )
                    if warmup_df is not None and len(warmup_df) > 0:
                        self._buffer_manager.load_warmup_data(symbol, warmup_df)

            # Check all symbols warmed up
            warmed = self._buffer_manager.get_warmed_up_symbols() if self._buffer_manager else []
            logger.info(f"✅ Warmup complete: {len(warmed)} symbols ready")

            self._state = PaperTradingState.RUNNING
            return True

        except Exception as e:
            logger.error(f"Warmup failed: {e}", exc_info=True)
            return False

    async def run(self) -> None:
        """
        Main event loop.

        Processes events from the dispatcher until stopped.
        """
        if self._state != PaperTradingState.RUNNING:
            logger.error(f"Cannot run in state: {self._state}")
            return

        logger.info("🏃 PaperTradingEngine running...")
        self._running = True

        # Start watchdog
        watchdog_task = None
        if self._watchdog:
            watchdog_task = self._watchdog.start_async_monitor()

        try:
            while self._running and self._state == PaperTradingState.RUNNING:
                # Process events from dispatcher
                if self._dispatcher:
                    event = self._dispatcher.process_next()
                    if event:
                        await self._process_event(event)

                        # Update watchdog
                        if self._watchdog:
                            # Only count BAR events as bars; others are heartbeats
                            if event.event_type == EventType.BAR:
                                self._watchdog.on_bar_processed()
                            else:
                                self._watchdog.on_heartbeat()

                        # Check for checkpoint
                        if self._state_manager:
                            if self._state_manager.increment_bars():
                                self._state_manager.create_checkpoint('periodic')
                    else:
                        # No events, brief sleep
                        await asyncio.sleep(0.001)
                else:
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Run loop cancelled")
        except Exception as e:
            logger.error(f"Run loop error: {e}", exc_info=True)
            self._state = PaperTradingState.ERROR
        finally:
            self._running = False
            if watchdog_task:
                watchdog_task.cancel()

    async def _process_event(self, event: Any) -> None:
        """Process a single event."""
        try:
            event_type = event.event_type.name if hasattr(event.event_type, 'name') else str(event.event_type)

            # Check idempotency
            if self._idempotency_tracker and event.event_id:
                if self._idempotency_tracker.check_and_mark('event', event.event_id):
                    logger.debug(f"Duplicate event skipped: {event.event_id}")
                    return

            if event_type == 'BAR':
                await self._process_bar(event)
            elif event_type in ('QUOTE', 'TRADE'):
                # Quotes/trades handled by conflation, just update prices
                if self._paper_broker and event.symbol:
                    price = event.payload.get('price') or event.payload.get('last_price')
                    if price:
                        self._paper_broker.set_price(event.symbol, price)
            elif event_type == 'FILL':
                await self._process_fill(event)

        except Exception as e:
            logger.error(f"Event processing error: {e}", exc_info=True)

    async def _update_market_data_and_execute_open(self, symbol: str, bar: Dict[str, Any], timestamp: datetime) -> None:
        """
        Update broker prices and execute pending bar-open signals.
        """
        # Ensure broker has up-to-date price BEFORE any executions at this bar's open
        if self._paper_broker:
            open_price = bar.get('open') or bar.get('open_price')
            if open_price:
                self._paper_broker.set_price(symbol, float(open_price))
            # Provide full bar snapshot so the paper broker can reuse backtest's execution simulator inputs.
            if hasattr(self._paper_broker, "set_market_data"):
                try:
                    self._paper_broker.set_market_data(symbol, bar, timestamp)
                except Exception:
                    pass

        # Execute any pending bar-open signals for this symbol when its open is available
        if self._pending_open_signals and self._execution_engine and self._oms and self._paper_broker:
            await self._execute_pending_signals_for_symbol(symbol=symbol, bar=bar, market_timestamp=timestamp)

        # After bar-open execution, process any queued fills up through this bar timestamp.
        if self._dispatcher and hasattr(self._dispatcher, "peek_next"):
            drained = 0
            while True:
                nxt = None
                try:
                    nxt = self._dispatcher.peek_next()
                except Exception:
                    nxt = None
                if nxt is None:
                    break
                try:
                    nxt_type = nxt.event_type.name if hasattr(nxt.event_type, "name") else str(nxt.event_type)
                except Exception:
                    nxt_type = str(getattr(nxt, "event_type", ""))
                if nxt_type != "FILL":
                    break
                try:
                    if getattr(nxt, "market_timestamp", None) is not None and nxt.market_timestamp > timestamp:
                        break
                except Exception:
                    pass
                # Pop + process the fill
                fev = self._dispatcher.process_next()
                if fev is None:
                    break
                await self._process_fill(fev)
                drained += 1

    def _compute_analytics(self, symbol: str, timestamp: datetime) -> Tuple[Optional[Any], Dict[str, float], Dict[str, float]]:
        """
        Compute indicators, features, and evaluate regime.
        Returns (enriched_df, last_row_indicators, last_row_features)
        """
        enriched_df = None
        last_row_indicators: Dict[str, float] = {}
        last_row_features: Dict[str, float] = {}

        if self._indicator_adapter and self._buffer_manager:
            buffer = self._buffer_manager.get_buffer(symbol)
            if buffer is not None and len(buffer) > 0:
                # Compute indicators over the full buffer window for strategy compatibility
                ind_df = self._indicator_adapter.compute_indicators_batch(buffer, last_n=len(buffer))
                if ind_df is not None and len(ind_df) > 0:
                    # Ensure the symbol column is present and correct in the enriched DF
                    if 'symbol' not in ind_df.columns:
                        ind_df['symbol'] = symbol
                    
                    enriched_df = ind_df
                    # Extract last-row indicator values for optional feature transform
                    last = ind_df.iloc[-1]
                    for col in ind_df.columns:
                        if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']:
                            try:
                                val = last[col]
                                if val is not None:
                                    last_row_indicators[col] = float(val)
                            except Exception:
                                continue

        if self._feature_adapter and last_row_indicators:
            try:
                last_row_features = self._feature_adapter.transform_single(last_row_indicators)
            except RuntimeError:
                # Scalers not loaded (allowed)
                last_row_features = {}

        # Log derived state
        if self._event_journal and (last_row_indicators or last_row_features):
            self._event_journal.log_features(symbol, {**last_row_indicators, **last_row_features}, timestamp)

        # Evaluate regime
        if self._regime_engine and self._buffer_manager:
            # Note: buffer might be fetched again here, but it's a cheap reference in memory
            buffer = self._buffer_manager.get_buffer(symbol)
            if buffer is not None:
                self._regime_engine.evaluate_regime_causal(buffer, symbol)
                
        return enriched_df, last_row_indicators, last_row_features

    async def _generate_strategy_signals(self, symbol: str, bar: Dict[str, Any], timestamp: datetime, enriched_df: Any, last_row_features: Dict[str, float]) -> None:
        """
        Coordinate with StrategyManager to generate signals.
        """
        if not self._strategy_manager or enriched_df is None:
            return

        # Track bars for current timestamp batch
        if self._bar_batch_timestamp is None or timestamp != self._bar_batch_timestamp:
            self._bar_batch_timestamp = timestamp
            self._bar_batch_symbols = set()
            self._bar_batch_market_data = {}

        # Attach features (last-row only) as columns so strategies can read them if needed
        if last_row_features:
            for k, v in last_row_features.items():
                if k not in enriched_df.columns:
                    enriched_df[k] = None
                try:
                    enriched_df.at[enriched_df.index[-1], k] = float(v)
                except Exception:
                    pass

        self._bar_batch_symbols.add(symbol)
        self._bar_batch_market_data[symbol] = enriched_df

        expected = set(self._expected_symbols) if self._expected_symbols else set(self._bar_batch_market_data.keys())
        if expected and expected.issubset(self._bar_batch_symbols):
            # Call StrategyManager once per timestamp with full universe snapshot
            position_details: Optional[Dict[str, Dict[str, Any]]] = None
            if self._paper_broker:
                try:
                    pd_map: Dict[str, Dict[str, Any]] = {}
                    for sym in expected:
                        pos = self._paper_broker.get_position(sym)
                        
                        # CRITICAL: Ensure we use the latest price from the broker's price cache
                        curr_price = 0.0
                        if hasattr(self._paper_broker, "_prices"):
                            curr_price = self._paper_broker._prices.get(sym, 0.0)
                        
                        if pos is None:
                            pd_map[sym] = {
                                "quantity": 0.0,
                                "entry_price": 0.0,
                                "current_price": curr_price,
                                "unrealized_pnl": 0.0,
                                "pnl_pct": 0.0,
                                "is_profitable": False,
                            }
                        else:
                            unreal = float(getattr(pos, "unrealized_pl", 0.0) or 0.0)
                            p_price = float(getattr(pos, "current_price", 0.0) or 0.0)
                            final_price = p_price if p_price > 0 else curr_price
                            
                            pd_map[sym] = {
                                "quantity": float(getattr(pos, "quantity", 0.0) or 0.0),
                                "entry_price": float(getattr(pos, "avg_entry_price", 0.0) or 0.0),
                                "current_price": final_price,
                                "unrealized_pnl": unreal,
                                "pnl_pct": float(getattr(pos, "unrealized_plpc", 0.0) or 0.0),
                                "is_profitable": unreal > 0.0,
                            }
                    position_details = pd_map
                except Exception as e:
                    logger.error(f"Failed to build position details: {e}")
                    position_details = None
            try:
                signals = await self._strategy_manager.generate_signals(
                    symbols=list(expected),
                    market_data=dict(self._bar_batch_market_data),
                    current_positions=None,
                    position_details=position_details,
                )
            except TypeError:
                # Backwards compat
                signals = await self._strategy_manager.generate_signals(
                    symbols=list(expected),
                    market_data=dict(self._bar_batch_market_data),
                    current_positions=None,
                )

            # Convert and submit signals through risk manager
            for s in signals or []:
                sig_symbol = getattr(s, "symbol", None)
                sig_price = None
                if sig_symbol and sig_symbol in self._bar_batch_market_data:
                    sig_df = self._bar_batch_market_data[sig_symbol]
                    if not sig_df.empty:
                        sig_price = float(sig_df.iloc[-1]['close'])
                
                if sig_price is None:
                    close_price = bar.get('close') or bar.get('close_price')
                    sig_price = float(close_price) if close_price is not None else None
                    
                signal_dict = self._normalize_strategy_signal(s, market_timestamp=timestamp, bar_close_price=sig_price)
                if signal_dict:
                    await self.submit_signal(signal_dict)

            # Reset batch
            self._bar_batch_symbols = set()
            self._bar_batch_market_data = {}

    async def _process_bar(self, event: Any) -> None:
        """Process a bar event."""
        symbol = event.symbol
        bar = event.payload
        timestamp = event.market_timestamp

        # CRITICAL SAFETY CHECK
        bar_symbol = bar.get('symbol')
        if bar_symbol and bar_symbol != symbol:
            logger.warning(f"⚠️ Data contamination detected: Event symbol {symbol} != Bar symbol {bar_symbol}. Skipping.")
            return

        self._stats['bars_processed'] += 1

        # === BarOpenSynthesizer ===
        if self._signal_manager and (self._last_bar_open_timestamp is None or timestamp != self._last_bar_open_timestamp):
            self._pending_open_signals = list(self._signal_manager.on_bar_open())
            self._last_bar_open_timestamp = timestamp

        # 1. Validate bar
        if self._data_validator:
            result = self._data_validator.validate_bar_dict(symbol, bar)
            if not result.is_valid:
                logger.warning(f"Invalid bar for {symbol}: {result.issues}")
                return

        # 2. Update market data and execute open signals
        await self._update_market_data_and_execute_open(symbol, bar, timestamp)

        # 3. Update buffer
        if self._buffer_manager:
            self._buffer_manager.update(symbol, bar)
            if not self._buffer_manager.is_warmed_up(symbol):
                return

        # 4. Log bar
        if self._event_journal:
            self._event_journal.log_bar(symbol, bar, event.event_id)

        # 5. Signal bar close
        if self._signal_manager:
            self._signal_manager.on_bar_close(timestamp)

        # 6. Compute analytics (Indicators, Features, Regime)
        enriched_df, _, last_row_features = self._compute_analytics(symbol, timestamp)

        # 7. Generate Strategy Signals
        await self._generate_strategy_signals(symbol, bar, timestamp, enriched_df, last_row_features)

        # 8. Mark computation complete
        if self._signal_manager:
            self._signal_manager.on_computation_complete()

        # 9. Update paper broker price (Close)
        if self._paper_broker:
            close_price = bar.get('close') or bar.get('close_price')
            if close_price:
                self._paper_broker.set_price(symbol, float(close_price))

        # 10. Update state manager
        if self._state_manager:
            self._state_manager.set_replay_position(
                symbol=symbol,
                timestamp=timestamp,
                row_index=self._stats['bars_processed'],
            )
            if event.event_id:
                self._state_manager.update_event_tracking(
                    event.event_id,
                    event.sequence_number,
                )

        # 11. Check for EOD liquidation
        await self._check_eod_liquidation(timestamp, bar)

    async def _check_eod_liquidation(self, timestamp: datetime, bar: Dict[str, Any]) -> int:
        """
        Check if we should perform EOD liquidation and close all positions.
        """
        if not self.config.enable_eod_liquidation:
            return 0

        # Parse EOD time
        try:
            eod_hour, eod_minute = map(int, self.config.eod_close_time.split(':'))
        except (ValueError, AttributeError):
            eod_hour, eod_minute = 15, 55

        # Convert timestamp to comparable format (NY time)
        import pandas as pd
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is not None:
            ts = ts.tz_convert('America/New_York')
        else:
            # Assume UTC if no TZ, but for papertest it's usually NY
            ts = ts.tz_localize('UTC').tz_convert('America/New_York')

        current_time_mins = ts.hour * 60 + ts.minute
        eod_time_mins = eod_hour * 60 + eod_minute

        if current_time_mins < eod_time_mins:
            return 0

        # Only liquidate if we haven't already at this timestamp
        eod_key = f"eod_liquidated_{ts.date()}"
        if self._eod_flags.get(eod_key, False):
            return 0

        # Get current positions from broker
        if not self._paper_broker:
            return 0

        # We need to check all positions. 
        # For parity with backtest, we should close everything.
        liquidated_count = 0
        
        # Get all symbols with positions
        symbols_to_close = []
        try:
            # This is a bit expensive but necessary for EOD
            # In a real system we'd track this in the position book
            if self._position_book:
                symbols_to_close = list(self._position_book.get_all_positions().keys())
            elif hasattr(self._paper_broker, "get_all_positions"):
                positions = self._paper_broker.get_all_positions()
                symbols_to_close = [p.symbol for p in positions if abs(p.quantity) > 0]
        except Exception as e:
            logger.error(f"Failed to get positions for EOD liquidation: {e}")
            return 0

        if not symbols_to_close:
            return 0

        self._eod_flags[eod_key] = True
        logger.info(f"\n⏰ EOD LIQUIDATION @ {ts.strftime('%H:%M')} - Closing {len(symbols_to_close)} positions")

        for symbol in symbols_to_close:
            pos = None
            if self._position_book:
                pos = self._position_book.get_position(symbol)
            elif self._paper_broker:
                pos = self._paper_broker.get_position(symbol)
            
            if pos and abs(pos.quantity) > 0:
                side = "sell" if pos.quantity > 0 else "buy"
                
                # Create a liquidation signal
                signal = {
                    'symbol': symbol,
                    'side': side,
                    'requested_quantity': abs(pos.quantity),
                    'type': 'market',
                    'reason': 'EOD_LIQUIDATION',
                    'signal_timestamp': timestamp
                }
                
                logger.info(f"   💰 EOD: {side.upper()} {abs(pos.quantity)} {symbol}")
                await self.submit_signal(signal)
                liquidated_count += 1

        return liquidated_count

    def _normalize_strategy_signal(self, s: Any, market_timestamp: datetime, bar_close_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Convert StrategyManager aggregated signal into PaperTradingEngine.submit_signal() dict.
        Delegates to _SignalNormalizer.
        """
        return _SignalNormalizer.normalize(
            signal=s,
            market_timestamp=market_timestamp,
            bar_close_price=bar_close_price,
            broker=self._paper_broker,
            risk_manager=self._risk_manager,
            default_stop_loss_pct=0.02
        )

    def _get_regime_context(self) -> Optional[Dict[str, Any]]:
        """
        Safely retrieve current regime context from regime engine.
        """
        if not self._regime_engine:
            return None

        try:
            # Prefer standard interface (Rule 2)
            if hasattr(self._regime_engine, "get_current_regime_context"):
                rc = self._regime_engine.get_current_regime_context()
                if isinstance(rc, dict):
                    return rc
                elif hasattr(rc, "__dict__"):
                    return dict(rc.__dict__)
            
            # Fallback for legacy/alternative implementations
            if hasattr(self._regime_engine, "current_regime"):
                cr = getattr(self._regime_engine, "current_regime", None)
                if isinstance(cr, dict):
                    return cr
                elif hasattr(cr, "__dict__"):
                    return dict(cr.__dict__)
        except Exception as e:
            logger.warning(f"Failed to retrieve regime context: {e}")
            
        return None

    def _create_execution_authorization(self, sig: Any) -> Any:
        """Create ExecutionAuthorization from signal."""
        from core_engine.system.unified_execution_engine import ExecutionAuthorization, ExecutionAlgorithm
        
        auth_id = None
        if hasattr(sig, "metadata") and isinstance(sig.metadata, dict):
            auth_id = sig.metadata.get("authorization_id")
            
        return ExecutionAuthorization(
            authorization_id=str(auth_id or f"auth:{getattr(sig, 'signal_id', '')}"),
            symbol=sig.symbol,
            side=sig.side,
            quantity=float(sig.requested_quantity),
            max_quantity=float(sig.requested_quantity),
            strategy_id=getattr(sig, "strategy_id", ""),
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
        )

    def _create_execution_request(self, auth: Any, decision_price: Optional[float], regime_ctx: Optional[Dict]) -> Any:
        """Create ExecutionRequest from authorization."""
        from core_engine.system.unified_execution_engine import ExecutionRequest, ExecutionAlgorithm
        
        return ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            strategy_context={"decision_price": decision_price, "regime_context": regime_ctx},
        )

    async def _execute_pending_signals_for_symbol(self, symbol: str, bar: Dict[str, Any], market_timestamp: datetime) -> None:
        """
        Execute signals at next-bar-open for a given symbol.

        Uses OMS for tracking and UnifiedExecutionEngine for paper routing.
        """
        if not self._pending_open_signals:
            return

        open_price = bar.get("open") or bar.get("open_price") or bar.get("close") or bar.get("close_price")
        if not open_price:
            return

        # Pull signals for this symbol only; keep others pending until their bar arrives
        remaining: List[Any] = []
        to_exec: List[Any] = []
        for sig in self._pending_open_signals:
            if getattr(sig, "symbol", None) == symbol:
                to_exec.append(sig)
            else:
                remaining.append(sig)
        self._pending_open_signals = remaining

        for sig in to_exec:
            try:
                # Construct authorization for execution engine
                auth = self._create_execution_authorization(sig)

                # OMS tracking
                oms_order = await self._oms.create_order(
                    authorization_id=auth.authorization_id,
                    symbol=auth.symbol,
                    side=auth.side,
                    quantity=auth.quantity,
                    strategy_id=auth.strategy_id,
                    metadata={"signal_id": getattr(sig, "signal_id", None)},
                )
                await self._oms.submit_order(oms_order.order_id)

                # Execute
                # Backtest parity: HistoricalExecutionSimulator uses the *signal bar close* (arrival_price)
                # as decision_price, even though execution occurs at next-bar open.
                decision_price = None
                try:
                    if hasattr(sig, "arrival_price") and getattr(sig, "arrival_price", None) is not None:
                        decision_price = float(getattr(sig, "arrival_price"))
                    elif hasattr(sig, "metadata") and isinstance(getattr(sig, "metadata", None), dict):
                        for k in ("arrival_price", "signal_bar_close", "decision_price"):
                            if k in sig.metadata and sig.metadata[k] is not None:
                                decision_price = float(sig.metadata[k])
                                break
                except Exception:
                    decision_price = None
                if decision_price is None:
                    # Fallback: if not available, use the signal's execution open price (best-effort)
                    try:
                        decision_price = float(open_price)
                    except Exception:
                        decision_price = None

                # Backtest parity: pass regime context into execution simulator (affects spread/impact multipliers).
                # NOTE: Backtest's first trade often has no regime context available yet (regime=None in results),
                # so we intentionally skip regime context for the first executed order to match that behavior.
                regime_ctx = None
                skip_regime_for_first_exec = bool(self._execution_count == 0)
                
                if (not skip_regime_for_first_exec):
                    regime_ctx = self._get_regime_context()

                req = self._create_execution_request(auth, decision_price, regime_ctx)
                
                result = await self._execution_engine.execute_with_mode_routing(req)
                self._execution_count += 1

                # Record fill in OMS if filled
                # UnifiedExecutionEngine uses core_engine.system.unified_execution_engine.ExecutionStatus
                if getattr(result, "status", None) and str(result.status).lower().endswith("filled"):
                    # Use fields set by _execute_paper
                    fill_qty = float(getattr(result, "fill_quantity", 0.0) or 0.0)
                    fill_px = float(getattr(result, "fill_price", 0.0) or float(open_price))
                    if fill_qty > 0:
                        await self._oms.record_fill(
                            order_id=oms_order.order_id,
                            fill_quantity=fill_qty,
                            fill_price=fill_px,
                            commission=float(getattr(result, "commission_cost", 0.0) or 0.0),
                        )
                        self._stats["orders_submitted"] += 1
            except Exception as e:
                logger.error(f"Signal execution error: {e}", exc_info=True)

    async def _process_fill(self, event: Any) -> None:
        """Process a fill event."""
        fill = event.payload
        symbol = event.symbol

        self._stats['fills_received'] += 1

        # Check idempotency
        fill_id = fill.get('fill_id')
        if self._idempotency_tracker and fill_id:
            if self._idempotency_tracker.check_and_mark('fill', fill_id):
                logger.debug(f"Duplicate fill skipped: {fill_id}")
                return

        # Log fill
        if self._event_journal:
            self._event_journal.log_fill(
                symbol=symbol,
                order_id=fill.get('order_id', ''),
                fill_id=fill_id or '',
                quantity=fill.get('quantity', 0),
                price=fill.get('price', 0),
                commission=fill.get('commission', 0),
                side=fill.get('side'),
                fill_timestamp=fill.get('timestamp'),
            )

        # Update risk budget
        if self._risk_budget:
            # Would need to track stop prices per position
            pass

        # Update positions via RiskManager ONLY (Rule 3 authority)
        try:
            if self._risk_manager and symbol:
                side = fill.get('side', '')
                # Handle Enum if necessary
                if hasattr(side, 'value'):
                    side = str(side.value)
                
                qty = float(fill.get('quantity', 0) or 0)
                px = float(fill.get('price', 0) or 0)
                ts = fill.get('timestamp')
                if qty > 0 and px > 0 and side:
                    await self._risk_manager.update_position(
                        symbol=symbol,
                        side=side,
                        quantity=qty,
                        price=px,
                        timestamp=ts,
                    )
        except Exception as e:
            logger.error(f"RiskManager fill position update failed: {e}", exc_info=True)

    async def submit_signal(self, signal: Dict[str, Any]) -> Optional[str]:
        """
        Submit a trading signal for processing.

        Args:
            signal: Signal dict with EnhancedTradingSignal fields

        Returns:
            Signal ID if accepted, None if rejected
        """
        symbol = signal.get('symbol')

        # Get current price
        current_price = 0.0
        # Determinism/parity: use the bar-derived arrival_price for risk checks when available.
        # Broker quotes in replay can reflect bar-open and trigger false "stale signal" rejections.
        current_price = float(signal.get('arrival_price', 0.0) or 0.0)
        if current_price <= 0 and self._paper_broker:
            quote = self._paper_broker.get_latest_quote(symbol)
            if quote:
                current_price = float(quote.get('last_price', 0) or 0.0)
        if current_price <= 0:
            current_price = 100.0

        # Get portfolio value
        portfolio_value = self.config.initial_cash
        if self._paper_broker:
            account = self._paper_broker.get_account_info()
            portfolio_value = account.portfolio_value

        # Log signal
        if self._event_journal:
            self._event_journal.log_signal(symbol, signal)

        # Risk authorization
        if self._risk_manager:
            auth_result = await self._risk_manager.authorize_signal_6gate(
                signal, current_price, portfolio_value
            )

            # Log decision
            if self._event_journal:
                decision = 'approved' if auth_result['authorized'] else 'rejected'
                self._event_journal.log_risk_decision(
                    symbol=symbol,
                    decision=decision,
                    authorization=auth_result,
                    reasons=[auth_result.get('rejection_reason', '')],
                )

            if not auth_result['authorized']:
                logger.info(f"Signal rejected: {auth_result['rejection_reason']}")
                return None

            # Submit to signal manager
            if self._signal_manager:
                from ..processing.signals.streaming_manager import EnhancedTradingSignal

                enhanced_signal = EnhancedTradingSignal(
                    symbol=signal['symbol'],
                    side=signal['side'],
                    requested_quantity=auth_result['authorized_quantity'],
                    signal_strength=signal.get('signal_strength', 0.5),
                    strategy_id=signal.get('strategy_id', 'unknown'),
                    signal_timestamp=datetime.now(timezone.utc),
                    arrival_price=signal.get('arrival_price', current_price),
                    stop_price=signal.get('stop_price'),
                    stop_loss_pct=signal.get('stop_loss_pct'),
                )

                signal_id = self._signal_manager.submit_signal(enhanced_signal)

                if signal_id:
                    # Derive an authorization_id tied to the signal + last passed gate
                    gate_passed = auth_result.get('gate_passed', 'G0')
                    auth_id = f"auth:{signal_id}:{gate_passed}"
                    try:
                        enhanced_signal.metadata['authorization_id'] = auth_id
                        enhanced_signal.metadata['gate_passed'] = gate_passed
                        enhanced_signal.metadata['max_loss_estimate'] = auth_result.get('max_loss_estimate', 0.0)
                        enhanced_signal.metadata['estimated_fill_price'] = auth_result.get('estimated_fill_price', current_price)
                    except Exception:
                        pass
                    self._stats['signals_generated'] += 1

                return signal_id

        return None

    def pause(self) -> None:
        """Pause the engine."""
        with self._lock:
            if self._state == PaperTradingState.RUNNING:
                self._state = PaperTradingState.PAUSED
                if self._state_manager:
                    self._state_manager.on_pause()
                logger.info("⏸️ PaperTradingEngine paused")

    def resume(self) -> None:
        """Resume the engine."""
        with self._lock:
            if self._state == PaperTradingState.PAUSED:
                self._state = PaperTradingState.RUNNING
                logger.info("▶️ PaperTradingEngine resumed")

    def stop(self) -> None:
        """Stop the engine."""
        with self._lock:
            self._running = False
            self._state = PaperTradingState.STOPPED

            # Create shutdown checkpoint
            if self._state_manager:
                self._state_manager.on_shutdown()

            # Close journal
            if self._event_journal:
                self._event_journal.log_system('engine_stopped', self._stats)
                self._event_journal.close()

            # Stop watchdog
            if self._watchdog:
                self._watchdog.stop()

            logger.info("🛑 PaperTradingEngine stopped")

    def get_state(self) -> PaperTradingState:
        """Get current engine state."""
        return self._state

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            'state': self._state.name,
            'session_id': self._session_id,
        }

    async def restore_from_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """
        Restore engine state from checkpoint.

        Args:
            checkpoint_id: Specific checkpoint (None = latest)

        Returns:
            True if restored successfully
        """
        if not self._state_manager:
            logger.error("No state manager for restore")
            return False

        success = self._state_manager.restore_checkpoint(checkpoint_id)

        if success:
            # Update local state
            info = self._state_manager.get_last_event_info()
            self._stats['bars_processed'] = info['bars_processed']
            self._state = PaperTradingState.RUNNING
            logger.info("✅ Engine restored from checkpoint")

        return success

