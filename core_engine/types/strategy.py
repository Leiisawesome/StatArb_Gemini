"""
Core Engine Strategy Types

Lightweight strategy interfaces for standalone core_engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import pandas as pd


class StrategyType(Enum):
    """Strategy type enumeration"""
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"


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
        pass
    
    @abstractmethod
    def update_state(self, data: pd.DataFrame):
        """Update internal strategy state"""
        pass
    
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