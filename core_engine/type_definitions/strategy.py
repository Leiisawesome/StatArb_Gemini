"""
Core Engine Strategy Types

Lightweight strategy interfaces for standalone core_engine.

This module provides canonical type definitions for:
- StrategyType: All strategy type classifications
- SignalType: All trading signal action types
- SignalStrength: Signal confidence levels
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import pandas as pd

# =============================================================================
# CANONICAL STRATEGY TYPE ENUM (Single Source of Truth)
# =============================================================================

class StrategyType(Enum):
    """
    Canonical strategy type enumeration.

    Single source of truth for all strategy type classifications.
    Consolidates definitions from:
    - type_definitions/strategy.py (original)
    - config/strategies.py
    - trading/strategies/strategy_engine.py
    - system/position_aging_monitor.py
    """
    # Core strategy types
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    PAIRS_TRADING = "pairs_trading"
    SES_PAIRS_TRADING = "ses_pairs_trading"  # Advanced SES-based pairs trading
    ARBITRAGE = "arbitrage"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    FACTOR = "factor"
    MULTI_ASSET = "multi_asset"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    VOLATILITY = "volatility"

    # Extended types from strategy_engine.py
    MARKET_MAKING = "market_making"
    MULTI_FACTOR = "multi_factor"
    MACHINE_LEARNING = "machine_learning"

    # Generic/fallback types
    CUSTOM = "custom"
    OTHER = "other"

# =============================================================================
# CANONICAL SIGNAL TYPE ENUM (Single Source of Truth)
# =============================================================================

class SignalType(Enum):
    """
    Canonical trading signal type enumeration.

    Single source of truth for all trading signal actions.

    UNIFIED TERMINOLOGY:
    ┌─────────────────┬─────────────────────────────┬─────────────────────┐
    │ Action          │ Meaning                     │ When Used           │
    ├─────────────────┼─────────────────────────────┼─────────────────────┤
    │ BUY/LONG_ENTRY  │ Open a LONG position        │ Bullish - price ↑   │
    │ SELL/LONG_EXIT  │ Close a LONG position       │ Exit your long      │
    │ SHORT/SHORT_ENTRY│ Open a SHORT position      │ Bearish - price ↓   │
    │ COVER/SHORT_EXIT│ Close a SHORT position      │ Exit your short     │
    └─────────────────┴─────────────────────────────┴─────────────────────┘

    IMPORTANT: Signal types MUST explicitly indicate BOTH:
    1. Action (entry/exit/increase/reduce)
    2. Direction (long/short)

    PREFERRED (explicit):
    - LONG_ENTRY: Open new long position (buy to open)
    - LONG_EXIT: Close existing long position (sell to close)
    - SHORT_ENTRY: Open new short position (sell to open)
    - SHORT_EXIT: Close existing short position (buy to cover)

    DEPRECATED (ambiguous - kept for backward compatibility only):
    - BUY, SELL (could mean entry OR exit depending on context)
    """
    # =========================================================================
    # EXPLICIT SIGNAL TYPES (PREFERRED - use these)
    # =========================================================================

    # Long Position Actions
    LONG_ENTRY = "long_entry"       # Open long (buy to open)
    LONG_EXIT = "long_exit"         # Close long (sell to close) - alias: CLOSE_LONG
    LONG_INCREASE = "increase_long" # Add to existing long
    LONG_REDUCE = "reduce_long"     # Partial close long

    # Short Position Actions
    SHORT_ENTRY = "short_entry"     # Open short (sell to open)
    SHORT_EXIT = "short_exit"       # Close short (buy to cover) - alias: CLOSE_SHORT
    SHORT_INCREASE = "increase_short" # Add to existing short
    SHORT_REDUCE = "reduce_short"    # Partial close short

    # Neutral
    HOLD = "hold"

    # =========================================================================
    # DEPRECATED: Ambiguous signals (kept for backward compatibility)
    # =========================================================================
    # WARNING: These are ambiguous and should be avoided in new code:
    # - BUY could mean LONG_ENTRY (open long) or SHORT_EXIT (cover short)
    # - SELL could mean LONG_EXIT (close long) or SHORT_ENTRY (open short)

    BUY = "buy"      # DEPRECATED: Use LONG_ENTRY or SHORT_EXIT instead
    SELL = "sell"    # DEPRECATED: Use LONG_EXIT or SHORT_ENTRY instead
    CLOSE = "close"  # DEPRECATED: Use LONG_EXIT or SHORT_EXIT instead

    # Legacy aliases (kept for backward compatibility)
    CLOSE_LONG = "close_long"     # Alias for LONG_EXIT
    CLOSE_SHORT = "close_short"   # Alias for SHORT_EXIT
    COVER = "cover"               # Alias for SHORT_EXIT (buy to cover)
    SHORT = "short"               # Alias for SHORT_ENTRY (sell to open)
    REDUCE_LONG = "reduce_long"   # Same as LONG_REDUCE
    REDUCE_SHORT = "reduce_short" # Same as SHORT_REDUCE
    INCREASE_LONG = "increase_long"   # Same as LONG_INCREASE
    INCREASE_SHORT = "increase_short" # Same as SHORT_INCREASE

    @classmethod
    def is_entry_signal(cls, signal_type: 'SignalType') -> bool:
        """Check if signal type is an entry signal (opens a new position)."""
        return signal_type in (cls.LONG_ENTRY, cls.SHORT_ENTRY, cls.SHORT, cls.BUY)

    @classmethod
    def is_exit_signal(cls, signal_type: 'SignalType') -> bool:
        """Check if signal type is an exit signal (closes a position)."""
        return signal_type in (
            cls.LONG_EXIT, cls.SHORT_EXIT, cls.CLOSE, cls.COVER,
            cls.CLOSE_LONG, cls.CLOSE_SHORT,
            cls.LONG_REDUCE, cls.SHORT_REDUCE,
            cls.REDUCE_LONG, cls.REDUCE_SHORT, cls.SELL
        )

    @classmethod
    def is_long_signal(cls, signal_type: 'SignalType') -> bool:
        """Check if signal type is related to long positions (opening or closing longs)."""
        return signal_type in (
            cls.LONG_ENTRY, cls.LONG_EXIT, cls.LONG_INCREASE, cls.LONG_REDUCE,
            cls.CLOSE_LONG, cls.INCREASE_LONG, cls.REDUCE_LONG, cls.BUY
        )

    @classmethod
    def is_short_signal(cls, signal_type: 'SignalType') -> bool:
        """Check if signal type is related to short positions (opening or closing shorts)."""
        return signal_type in (
            cls.SHORT_ENTRY, cls.SHORT_EXIT, cls.SHORT_INCREASE, cls.SHORT_REDUCE,
            cls.CLOSE_SHORT, cls.INCREASE_SHORT, cls.REDUCE_SHORT, cls.SHORT, cls.COVER
        )

    @classmethod
    def is_bullish_entry(cls, signal_type: 'SignalType') -> bool:
        """Check if signal opens a bullish position (long entry or short cover)."""
        return signal_type in (cls.LONG_ENTRY, cls.BUY, cls.SHORT_EXIT, cls.COVER, cls.CLOSE_SHORT)

    @classmethod
    def is_bearish_entry(cls, signal_type: 'SignalType') -> bool:
        """Check if signal opens a bearish position (short entry or long close)."""
        return signal_type in (cls.SHORT_ENTRY, cls.SHORT, cls.LONG_EXIT, cls.CLOSE_LONG, cls.SELL)

    @classmethod
    def normalize(cls, signal_type: 'SignalType', has_long: bool = False, has_short: bool = False) -> 'SignalType':
        """
        Normalize ambiguous/alias signals to canonical explicit signals based on position context.

        Args:
            signal_type: The signal type to normalize
            has_long: Whether there's an existing long position
            has_short: Whether there's an existing short position

        Returns:
            Normalized SignalType (canonical form: LONG_ENTRY, LONG_EXIT, SHORT_ENTRY, SHORT_EXIT)
        """
        # Normalize aliases to canonical forms
        if signal_type == cls.SHORT:
            return cls.SHORT_ENTRY
        elif signal_type == cls.COVER:
            return cls.SHORT_EXIT
        elif signal_type == cls.CLOSE_LONG:
            return cls.LONG_EXIT
        elif signal_type == cls.CLOSE_SHORT:
            return cls.SHORT_EXIT
        
        # Handle ambiguous BUY/SELL based on position context
        if signal_type == cls.BUY:
            if has_short:
                return cls.SHORT_EXIT  # Cover short
            return cls.LONG_ENTRY  # Open long
        elif signal_type == cls.SELL:
            if has_long:
                return cls.LONG_EXIT  # Close long
            return cls.SHORT_ENTRY  # Open short
        elif signal_type == cls.CLOSE:
            if has_long:
                return cls.LONG_EXIT
            elif has_short:
                return cls.SHORT_EXIT

        return signal_type

class SignalStrength(Enum):
    """
    Canonical signal strength enumeration.

    Standardized signal confidence levels.
    """
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MEDIUM = "medium"      # Backward compatibility alias
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str
    strategy_type: StrategyType
    symbols: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    risk_limit: float = 0.1  # 10% portfolio risk
    position_limit: float = 0.05  # 5% per position

@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    strategy_id: str
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # Signal strength 0-1
    price: Optional[float] = None
    quantity: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_buy(self) -> bool:
        return self.signal_type.upper() == 'BUY'

    @property
    def is_sell(self) -> bool:
        return self.signal_type.upper() == 'SELL'

    @property
    def is_hold(self) -> bool:
        return self.signal_type.upper() == 'HOLD'

@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    strategy_id: str
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    avg_trade_return: float = 0.0

    # Time-based metrics
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Risk metrics
    volatility: float = 0.0
    var_95: float = 0.0  # 95% VaR

    def update_from_returns(self, returns: pd.Series):
        """Update metrics from return series"""
        if len(returns) == 0:
            return

        self.total_return = (1 + returns).prod() - 1
        self.sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        self.volatility = returns.std() * (252 ** 0.5)

        # Drawdown calculation
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        self.max_drawdown = drawdown.min()

        # VaR
        self.var_95 = returns.quantile(0.05)

class BaseStrategy(ABC):
    """Base strategy interface"""

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy_id = config.name
        self.is_active = config.enabled
        self.metrics = StrategyMetrics(self.strategy_id)

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """Generate trading signals from market data"""

    @abstractmethod
    def update_state(self, data: pd.DataFrame):
        """Update internal strategy state"""

    def validate_signal(self, signal: TradingSignal) -> bool:
        """Validate signal before sending to risk manager"""
        return True

    def get_metrics(self) -> StrategyMetrics:
        """Get current strategy metrics"""
        return self.metrics

class StrategyInterface(BaseStrategy):
    """Enhanced strategy interface with callbacks"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self._signal_callbacks: List[Callable[[TradingSignal], None]] = []
        self._state_data: Dict[str, Any] = {}

    def add_signal_callback(self, callback: Callable[[TradingSignal], None]):
        """Add callback for signal generation"""
        self._signal_callbacks.append(callback)

    def emit_signal(self, signal: TradingSignal):
        """Emit signal to all callbacks"""
        if self.validate_signal(signal):
            for callback in self._signal_callbacks:
                callback(signal)

    def set_state(self, key: str, value: Any):
        """Set internal state value"""
        self._state_data[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get internal state value"""
        return self._state_data.get(key, default)

class StrategyManager:
    """Manager for multiple strategies"""

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: List[str] = []

    def register_strategy(self, strategy: BaseStrategy):
        """Register a new strategy"""
        self.strategies[strategy.strategy_id] = strategy
        if strategy.is_active:
            self.active_strategies.append(strategy.strategy_id)

    def remove_strategy(self, strategy_id: str):
        """Remove strategy"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
        if strategy_id in self.active_strategies:
            self.active_strategies.remove(strategy_id)

    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)

    def generate_all_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """Generate signals from all active strategies"""
        all_signals = []
        for strategy_id in self.active_strategies:
            strategy = self.strategies[strategy_id]
            signals = strategy.generate_signals(data)
            all_signals.extend(signals)
        return all_signals

    def update_all_strategies(self, data: pd.DataFrame):
        """Update all active strategies"""
        for strategy_id in self.active_strategies:
            strategy = self.strategies[strategy_id]
            strategy.update_state(data)

    def get_all_metrics(self) -> Dict[str, StrategyMetrics]:
        """Get metrics for all strategies"""
        return {sid: strategy.get_metrics() for sid, strategy in self.strategies.items()}