"""
Risk management module for statistical arbitrage trading.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class RiskLimits:
    """Risk limit configuration."""
    def __init__(self, 
                 max_position_size: float = 0.1,
                 max_drawdown: float = 0.05,
                 max_correlation: float = 0.8,
                 max_leverage: float = 2.0):
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.max_correlation = max_correlation
        self.max_leverage = max_leverage

class RiskManager:
    """
    Comprehensive risk management for statistical arbitrage strategies.
    """
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.portfolio_value = 100000.0  # Default initial value
        self.peak_portfolio_value = self.portfolio_value
        self.position_history = []
        self.returns_history = []

    def update_portfolio_value(self, new_value: float):
        """Update portfolio value and track peak."""
        prev_value = self.portfolio_value
        self.portfolio_value = new_value
        self.peak_portfolio_value = max(self.peak_portfolio_value, new_value)
        if prev_value > 0:
            return_rate = (new_value - prev_value) / prev_value
            self.returns_history.append(return_rate)

    def add_position(self, position_data: Dict):
        """Add position to history."""
        self.position_history.append(position_data)

    def can_take_position(self, position_type: str, strength: float) -> bool:
        """Check if a new position can be taken based on risk limits."""
        if strength > self.risk_limits.max_position_size:
            return False
        current_drawdown = (self.peak_portfolio_value - self.portfolio_value) / self.peak_portfolio_value
        if current_drawdown > self.risk_limits.max_drawdown:
            return False
        # Correlation and leverage checks can be added here
        return True

    def calculate_position_size(self, price1: float, price2: float, hedge_ratio: float) -> float:
        """Calculate position size based on risk limits and prices."""
        # Simple fixed fraction of portfolio value
        notional = self.portfolio_value * self.risk_limits.max_position_size
        size1 = notional / price1 if price1 > 0 else 0
        size2 = notional * hedge_ratio / price2 if price2 > 0 else 0
        return min(size1, size2)

    def check_risk_limits(self, position: int, pnl_history: List[float]) -> List[str]:
        """Check risk limits and return any actions needed."""
        actions = []
        if not pnl_history:
            return actions
        # Drawdown check
        cumulative = np.cumsum(pnl_history)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / np.abs(peak)
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
        if abs(max_drawdown) > self.risk_limits.max_drawdown:
            actions.append('reduce_position_due_to_drawdown')
        # Add more checks as needed
        return actions

    def get_risk_metrics(self) -> Dict[str, float]:
        """Return current risk metrics."""
        if not self.returns_history:
            return {}
        returns = np.array(self.returns_history)
        return {
            'VaR_95': calculate_var(returns, 0.95),
            'CVaR_95': calculate_cvar(returns, 0.95),
            'max_drawdown': calculate_maximum_adverse_excursion(list(returns))
        }

def calculate_var(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """Calculate Value at Risk."""
    if len(returns) == 0:
        return 0.0
    return float(np.percentile(returns, (1 - confidence_level) * 100))

def calculate_cvar(returns: np.ndarray, confidence_level: float = 0.95) -> float:
    """Calculate Conditional Value at Risk (Expected Shortfall)."""
    if len(returns) == 0:
        return 0.0
    var = calculate_var(returns, confidence_level)
    return float(returns[returns <= var].mean()) if np.any(returns <= var) else 0.0

def calculate_maximum_adverse_excursion(trade_pnls: List[float]) -> float:
    """Calculate Maximum Adverse Excursion."""
    if not trade_pnls:
        return 0.0
    cumulative_pnl = np.cumsum(trade_pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = cumulative_pnl - running_max
    return float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0 