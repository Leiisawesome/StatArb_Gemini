"""
Defines type-safe data structures for configuration and state management,
optimized for intraday trading.
"""
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime

@dataclass(frozen=True)
class Config:
    # Data Config
    tickers: List[str]
    use_dynamic_pairs: bool
    spread_type: str
    data_interval: str
    history_duration_days: int
    training_window_bars: int
    sample_window_bars: int
    
    # Model Config
    num_regimes: int
    use_hmm: bool
    use_ensemble_classifier: bool
    
    # Strategy Config
    entry_z: float
    exit_z: float
    stop_loss_mult: float
    max_hold_bars: int
    
    # Risk & Execution Config
    trade_size_dollars: float
    slippage_pct: float
    
    # Evaluation Config
    monte_carlo_simulations: int
    cross_validation_slices: int
    perform_ablation: bool
    risk_free_rate: float

@dataclass
class Position:
    type: str = 'FLAT'  # 'LONG', 'SHORT', or 'FLAT'
    entry_date: datetime | None = None
    holding_period: int = 0
    entry_y_price: float = 0.0
    entry_x_price: float = 0.0
    y_shares: float = 0.0
    x_shares: float = 0.0

@dataclass(frozen=True)
class Trade:
    pair: Tuple[str, str]
    entry_date: datetime
    exit_date: datetime
    pnl: float
    type: str 