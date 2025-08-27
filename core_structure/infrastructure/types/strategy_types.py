"""
Canonical Strategy Type Definitions
==================================
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class StrategyType(Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"

@dataclass
class StrategyConfig:
    """Canonical strategy configuration"""
    strategy_id: str
    strategy_type: StrategyType
    symbols: list
    parameters: Dict[str, Any]
    risk_params: Optional[Dict[str, Any]] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.risk_params is None:
            self.risk_params = {}


@dataclass
class Position:
    """Canonical position representation for basic position tracking"""
    symbol: str
    quantity: float
    average_price: float
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.market_value == 0.0:
            self.market_value = self.quantity * self.average_price
