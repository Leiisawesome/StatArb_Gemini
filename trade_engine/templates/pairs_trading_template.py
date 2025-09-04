"""
Simple Pairs Trading Strategy Template
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .base_template import BaseTemplate, ParameterBounds

@dataclass
class PairsConfiguration:
    """Simple configuration for Pairs Trading Strategy"""
    symbol_pairs: List[List[str]] = field(default_factory=lambda: [['SPY', 'IVV']])
    lookback_window: int = 252
    spread_lookback: int = 60
    significance_level: float = 0.05
    min_correlation: float = 0.8
    entry_zscore_long: float = -2.0
    entry_zscore_short: float = 2.0
    exit_zscore: float = 0.5
    stop_loss_zscore: float = 3.0
    max_position_hold_periods: int = 100
    capital_per_pair: float = 10000.0
    max_pairs_active: int = 3
    hedge_ratio_update_frequency: int = 20

class ProfessionalPairsTradingTemplate(BaseTemplate):
    """
    Simple Pairs Trading Strategy Template.
    """
    def __init__(self):
        super().__init__(
            template_id="professional_pairs_trading_v1",
            name="Professional Pairs Trading Strategy",
            description="Statistical arbitrage strategy based on cointegration and mean reversion of spread."
        )

    def _define_template(self) -> None:
        """Define template-specific parameters."""
        self.add_parameter_bounds("lookback_window", ParameterBounds(
            min_value=50, max_value=500, default_value=252
        ))
        self.add_parameter_bounds("spread_lookback", ParameterBounds(
            min_value=20, max_value=200, default_value=60
        ))
        self.add_parameter_bounds("significance_level", ParameterBounds(
            min_value=0.01, max_value=0.1, default_value=0.05
        ))
        self.add_parameter_bounds("min_correlation", ParameterBounds(
            min_value=0.5, max_value=0.99, default_value=0.8
        ))
        self.add_parameter_bounds("entry_zscore_long", ParameterBounds(
            min_value=-3.0, max_value=-1.0, default_value=-2.0
        ))
        self.add_parameter_bounds("entry_zscore_short", ParameterBounds(
            min_value=1.0, max_value=3.0, default_value=2.0
        ))
        self.add_parameter_bounds("exit_zscore", ParameterBounds(
            min_value=0.1, max_value=1.0, default_value=0.5
        ))
        self.add_parameter_bounds("stop_loss_zscore", ParameterBounds(
            min_value=2.5, max_value=5.0, default_value=3.0
        ))
        self.add_parameter_bounds("max_position_hold_periods", ParameterBounds(
            min_value=20, max_value=500, default_value=100, data_type=int
        ))
        self.add_parameter_bounds("capital_per_pair", ParameterBounds(
            min_value=1000.0, max_value=100000.0, default_value=10000.0
        ))
        self.add_parameter_bounds("max_pairs_active", ParameterBounds(
            min_value=1, max_value=10, default_value=3, data_type=int
        ))
        self.add_parameter_bounds("hedge_ratio_update_frequency", ParameterBounds(
            min_value=10, max_value=100, default_value=20, data_type=int
        ))

        self._required_indicators = ['close', 'volume']
        self._metadata = {
            "strategy_category": "Statistical Arbitrage",
            "asset_class": "Equities",
            "timeframe_suitability": ["intraday", "daily"],
            "complexity": "High"
        }
