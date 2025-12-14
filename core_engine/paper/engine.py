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
from typing import Any, Dict, List, Optional
import threading

logger = logging.getLogger(__name__)

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
        self._regime_engine = None
        self._session_gate = None
        self._risk_manager = None
        self._risk_budget = None
        self._paper_broker = None
        self._execution_engine = None
        self._position_book = None
        self._event_journal = None
        self._state_manager = None
        self._idempotency_tracker = None
        self._watchdog = None

        # Replay adapter reference
        self._replay_adapter = None

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
                            self._watchdog.on_bar_processed()

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

    async def _process_bar(self, event: Any) -> None:
        """Process a bar event."""
        symbol = event.symbol
        bar = event.payload
        timestamp = event.market_timestamp

        self._stats['bars_processed'] += 1

        # 1. Validate bar
        if self._data_validator:
            result = self._data_validator.validate_bar_dict(symbol, bar)
            if not result.is_valid:
                logger.warning(f"Invalid bar for {symbol}: {result.issues}")
                return

        # 2. Update buffer
        if self._buffer_manager:
            self._buffer_manager.update(symbol, bar)

            # Check warmup
            if not self._buffer_manager.is_warmed_up(symbol):
                return

        # 3. Log bar
        if self._event_journal:
            self._event_journal.log_bar(symbol, bar, event.event_id)

        # 4. Signal bar close to signal manager
        if self._signal_manager:
            self._signal_manager.on_bar_close(timestamp)

        # 5. Compute indicators
        indicators = {}
        if self._indicator_adapter and self._buffer_manager:
            buffer = self._buffer_manager.get_buffer(symbol)
            if buffer is not None:
                indicators = self._indicator_adapter.compute_indicators(buffer)

        # 6. Compute features
        features = {}
        if self._feature_adapter and indicators:
            try:
                features = self._feature_adapter.transform_single(indicators)
            except RuntimeError:
                # Scalers not loaded
                pass

        # 7. Log derived state
        if self._event_journal and (indicators or features):
            self._event_journal.log_features(symbol, {**indicators, **features}, timestamp)

        # 8. Evaluate regime
        if self._regime_engine and self._buffer_manager:
            buffer = self._buffer_manager.get_buffer(symbol)
            if buffer is not None:
                self._regime_engine.evaluate_regime_causal(buffer, symbol)

        # 9. Signal generation would happen here via strategy callbacks
        # For now, we just mark computation complete
        if self._signal_manager:
            self._signal_manager.on_computation_complete()

        # 10. Update paper broker price
        if self._paper_broker:
            close_price = bar.get('close') or bar.get('close_price')
            if close_price:
                self._paper_broker.set_price(symbol, float(close_price))

        # 11. Update state manager
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
            )

        # Update risk budget
        if self._risk_budget:
            # Would need to track stop prices per position
            pass

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
        if self._paper_broker:
            quote = self._paper_broker.get_latest_quote(symbol)
            if quote:
                current_price = quote.get('last_price', 0)

        if current_price <= 0:
            current_price = signal.get('arrival_price', 100.0)

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

