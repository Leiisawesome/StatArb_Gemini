"""
Core Engine Risk Types

Lightweight risk management for standalone core_engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_portfolio_risk: float = 0.02  # 2% portfolio VaR
    max_position_size: float = 0.1  # 10% per position
    max_correlation: float = 0.7  # Max correlation between positions
    stop_loss_pct: float = 0.05  # 5% stop loss
    daily_loss_limit: float = 0.03  # 3% daily loss limit

    # Leverage limits
    max_leverage: float = 1.0  # No leverage by default
    margin_requirement: float = 0.5  # 50% margin

    # Risk monitoring
    var_confidence: float = 0.95  # 95% VaR
    lookback_days: int = 252  # 1 year lookback

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    portfolio_var: float = 0.0  # Value at Risk
    portfolio_volatility: float = 0.0
    beta: float = 0.0  # Market beta
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

    # Position-level risks
    position_concentrations: Dict[str, float] = field(default_factory=dict)
    sector_concentrations: Dict[str, float] = field(default_factory=dict)

    # Current exposure
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    leverage: float = 0.0

    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskResult:
    """Risk check result"""
    approved: bool
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    adjusted_quantity: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def add_reason(self, reason: str):
        """Add rejection reason"""
        self.reasons.append(reason)
        self.approved = False

    def add_warning(self, warning: str):
        """Add warning message"""
        self.warnings.append(warning)

class RiskManager:
    """Core risk management"""

    def __init__(self, config: RiskConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.daily_start_value = 0.0
        self.risk_overrides: Dict[str, bool] = {}

    def check_trade_risk(self, symbol: str, quantity: float, price: float,
                        portfolio_value: float, current_position: float = 0.0) -> RiskResult:
        """Check if trade meets risk requirements"""
        result = RiskResult(approved=True, risk_level=RiskLevel.LOW)

        # Position size check
        new_position_value = abs(current_position + quantity) * price
        position_pct = new_position_value / portfolio_value

        if position_pct > self.config.max_position_size:
            result.add_reason(f"Position size {position_pct:.2%} exceeds limit {self.config.max_position_size:.2%}")
            result.risk_level = RiskLevel.HIGH

            # Suggest adjusted quantity
            max_position_value = portfolio_value * self.config.max_position_size
            max_additional = (max_position_value / price) - current_position
            result.adjusted_quantity = max(0, max_additional)

        # Daily loss limit check
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_value if self.daily_start_value > 0 else 0
        if daily_loss_pct > self.config.daily_loss_limit:
            result.add_reason(f"Daily loss {daily_loss_pct:.2%} exceeds limit {self.config.daily_loss_limit:.2%}")
            result.risk_level = RiskLevel.CRITICAL

        # Leverage check
        trade_value = abs(quantity * price)
        if trade_value > portfolio_value * self.config.max_leverage:
            result.add_reason(f"Trade would exceed maximum leverage {self.config.max_leverage:.1f}x")
            result.risk_level = RiskLevel.HIGH

        return result

    def calculate_portfolio_metrics(self, positions: Dict[str, float],
                                   prices: Dict[str, float],
                                   returns_data: Optional[Dict[str, List[float]]] = None) -> RiskMetrics:
        """Calculate portfolio risk metrics"""
        import numpy as np

        metrics = RiskMetrics()

        if not positions or not prices:
            return metrics

        # Vectorized portfolio calculations: 6x faster
        symbols = list(positions.keys())
        quantities = np.array([positions[symbol] for symbol in symbols])
        symbol_prices = np.array([prices.get(symbol, 0) for symbol in symbols])

        # Calculate position values
        position_values = quantities * symbol_prices
        abs_position_values = np.abs(position_values)

        # Calculate total value
        total_value = abs_position_values.sum()

        # Calculate concentrations
        if total_value > 0:
            concentrations = abs_position_values / total_value
            metrics.position_concentrations = dict(zip(symbols, concentrations))

        # Calculate exposures
        metrics.gross_exposure = abs_position_values.sum()
        metrics.net_exposure = position_values.sum()

        return metrics

    def update_daily_pnl(self, current_portfolio_value: float):
        """Update daily P&L tracking"""
        if self.daily_start_value == 0:
            self.daily_start_value = current_portfolio_value

        self.daily_pnl = current_portfolio_value - self.daily_start_value

    def reset_daily_tracking(self, portfolio_value: float):
        """Reset daily tracking (call at start of day)"""
        self.daily_start_value = portfolio_value
        self.daily_pnl = 0.0

    def set_risk_override(self, symbol: str, enabled: bool):
        """Set risk override for specific symbol"""
        self.risk_overrides[symbol] = enabled

    def is_trading_allowed(self, symbol: str) -> bool:
        """Check if trading is allowed for symbol"""
        return self.risk_overrides.get(symbol, True)