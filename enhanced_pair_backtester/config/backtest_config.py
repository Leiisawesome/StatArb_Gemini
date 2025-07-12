"""
Configuration management for the enhanced pair backtesting system.
Provides flexible, generic configuration for any trading pair.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import os

@dataclass
class BacktestConfig:
    """
    Comprehensive configuration for pair trading backtests.
    Designed to be generic and work with any trading pair.
    """
    
    # === PAIR CONFIGURATION ===
    symbol1: str = "TLT"
    symbol2: str = "TMF"
    pair_name: str = ""  # Auto-generated if empty
    
    # === TIME PERIODS ===
    training_start: str = "2023-01-01"
    training_end: str = "2024-12-31"
    testing_start: str = "2025-01-01"
    testing_end: str = "2025-06-30"
    
    # === DATA CONFIGURATION ===
    data_source: str = "clickhouse"  # clickhouse, polygon, csv
    data_frequency: str = "5min"     # 1min, 5min, 1hour, 1day
    database_config: Dict[str, Any] = field(default_factory=lambda: {
        'host': 'localhost',
        'port': 8123,
        'user': 'default',
        'password': '',
        'database': 'polygon_data'
    })
    
    # === STRATEGY PARAMETERS ===
    initial_capital: float = 1000000.0
    max_position_size: float = 0.25  # 25% of capital
    
    # Signal generation
    lookback_window: int = 60        # Days for rolling statistics
    entry_threshold: float = 2.0     # Z-score threshold for entry
    exit_threshold: float = 0.5      # Z-score threshold for exit
    stop_loss_threshold: float = 3.0 # Z-score threshold for stop loss
    
    # === MODEL CONFIGURATION ===
    use_kalman_filter: bool = True
    use_hmm_regime: bool = True
    use_ensemble_filter: bool = True
    
    # Kalman filter parameters
    kalman_config: Dict[str, float] = field(default_factory=lambda: {
        'process_noise_beta': 1e-6,
        'process_noise_alpha': 1e-6,
        'observation_noise': 1e-4,
        'initial_beta': 1.0,
        'initial_alpha': 0.0
    })
    
    # HMM parameters
    hmm_config: Dict[str, Any] = field(default_factory=lambda: {
        'num_regimes': 3,
        'regime_thresholds': {
            0: 2.0,  # Low volatility regime
            1: 2.5,  # Medium volatility regime  
            2: 3.0   # High volatility regime
        }
    })
    
    # Ensemble classifier parameters
    ensemble_config: Dict[str, Any] = field(default_factory=lambda: {
        'min_confidence': 0.6,
        'n_estimators': 100,
        'max_depth': 5,
        'lookback_periods': [5, 10, 20]
    })
    
    # === EXECUTION PARAMETERS ===
    transaction_costs: Dict[str, float] = field(default_factory=lambda: {
        'commission_per_trade': 0.50,
        'bid_ask_spread_bps': 2.0,
        'market_impact_bps': 1.0,
        'borrowing_rate_annual': 0.015
    })
    
    # Order execution
    order_type: str = "market"       # market, limit
    execution_delay: int = 0         # Bars delay for execution
    slippage_bps: float = 1.0       # Additional slippage in basis points
    
    # === RISK MANAGEMENT ===
    max_drawdown_limit: float = 0.05  # 5% maximum drawdown
    daily_var_limit: float = 0.01      # 1% daily VaR limit
    position_concentration_limit: float = 0.25  # 25% max in single pair
    
    # === PERFORMANCE ANALYSIS ===
    benchmark_symbol: str = "SPY"     # Benchmark for comparison
    risk_free_rate: float = 0.02      # Annual risk-free rate
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    
    # === OUTPUT CONFIGURATION ===
    output_dir: str = "results"
    save_trades: bool = True
    save_daily_pnl: bool = True
    save_plots: bool = True
    plot_format: str = "png"          # png, pdf, svg
    
    # === ADVANCED FEATURES ===
    walk_forward_analysis: bool = False
    walk_forward_window: int = 252    # Days for walk-forward window
    walk_forward_step: int = 21       # Days for walk-forward step
    use_walk_forward: bool = False    # Enable walk-forward analysis
    
    monte_carlo_runs: int = 0         # 0 = disabled, >0 = number of runs
    bootstrap_samples: int = 1000     # For confidence intervals
    
    # === ANALYSIS OPTIONS ===
    performance_analysis: bool = True  # Enable detailed performance analysis
    risk_analysis: bool = True         # Enable comprehensive risk analysis
    
    # === EXECUTION OPTIONS ===
    save_all: bool = False            # Save all possible outputs
    quick_test: bool = False          # Quick test mode with simplified models
    parallel: bool = False            # Enable parallel processing
    debug: bool = False               # Enable debug mode
    
    # === DEBUGGING ===
    verbose: bool = True
    log_level: str = "INFO"          # DEBUG, INFO, WARNING, ERROR
    save_intermediate_results: bool = False
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Auto-generate pair name if not provided
        if not self.pair_name:
            self.pair_name = f"{self.symbol1}_{self.symbol2}"
        
        # Validate dates
        self._validate_dates()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Validate parameters
        self._validate_parameters()
    
    def _validate_dates(self):
        """Validate that dates are in correct order."""
        dates = [
            datetime.strptime(self.training_start, "%Y-%m-%d"),
            datetime.strptime(self.training_end, "%Y-%m-%d"),
            datetime.strptime(self.testing_start, "%Y-%m-%d"),
            datetime.strptime(self.testing_end, "%Y-%m-%d")
        ]
        
        if not (dates[0] < dates[1] <= dates[2] < dates[3]):
            raise ValueError("Dates must be in order: training_start < training_end <= testing_start < testing_end")
    
    def _validate_parameters(self):
        """Validate configuration parameters."""
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if not (0 < self.max_position_size <= 1):
            raise ValueError("Max position size must be between 0 and 1")
        
        if self.entry_threshold <= 0:
            raise ValueError("Entry threshold must be positive")
        
        if self.stop_loss_threshold <= self.entry_threshold:
            raise ValueError("Stop loss threshold must be greater than entry threshold")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    def save_config(self, filepath: str):
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load_config(cls, filepath: str) -> 'BacktestConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        return cls(**config_dict)
    
    def get_pair_config(self, symbol1: str, symbol2: str) -> 'BacktestConfig':
        """Create a new config for a different pair."""
        new_config = BacktestConfig(**self.to_dict())
        new_config.symbol1 = symbol1
        new_config.symbol2 = symbol2
        new_config.pair_name = f"{symbol1}_{symbol2}"
        return new_config
    
    def get_training_period(self) -> Tuple[str, str]:
        """Get training period dates."""
        return self.training_start, self.training_end
    
    def get_testing_period(self) -> Tuple[str, str]:
        """Get testing period dates."""
        return self.testing_start, self.testing_end
    
    def get_full_period(self) -> Tuple[str, str]:
        """Get full period dates."""
        return self.training_start, self.testing_end
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"BacktestConfig(pair={self.pair_name}, training={self.training_start} to {self.training_end}, testing={self.testing_start} to {self.testing_end})"
    
    def __repr__(self) -> str:
        """Detailed representation of the configuration."""
        return self.__str__()


# Pre-defined configurations for common pairs
COMMON_PAIRS = {
    "TLT_TMF": BacktestConfig(
        symbol1="TLT", symbol2="TMF",
        entry_threshold=2.0,
        hmm_config={'num_regimes': 3, 'regime_thresholds': {0: 2.0, 1: 2.5, 2: 3.0}}
    ),
    "QQQ_TQQQ": BacktestConfig(
        symbol1="QQQ", symbol2="TQQQ", 
        entry_threshold=2.0,
        hmm_config={'num_regimes': 3, 'regime_thresholds': {0: 2.0, 1: 2.5, 2: 3.0}}
    ),
    "IWM_TNA": BacktestConfig(
        symbol1="IWM", symbol2="TNA",
        entry_threshold=2.0,
        hmm_config={'num_regimes': 3, 'regime_thresholds': {0: 2.0, 1: 2.5, 2: 3.0}}
    ),
    "UVIX_UVXY": BacktestConfig(
        symbol1="UVIX", symbol2="UVXY",
        entry_threshold=2.5,  # Higher threshold for volatility pairs
        hmm_config={'num_regimes': 3, 'regime_thresholds': {0: 2.5, 1: 3.0, 2: 3.5}}
    )
}

def get_pair_config(pair_name: str) -> BacktestConfig:
    """Get pre-defined configuration for common pairs."""
    if pair_name in COMMON_PAIRS:
        return COMMON_PAIRS[pair_name]
    else:
        # Return default configuration
        symbols = pair_name.split('_')
        if len(symbols) == 2:
            return BacktestConfig(symbol1=symbols[0], symbol2=symbols[1])
        else:
            raise ValueError(f"Invalid pair name format: {pair_name}. Use 'SYMBOL1_SYMBOL2' format.") 