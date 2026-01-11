"""
System-wide configuration for core_engine
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime

@dataclass
class SystemConfig:
    """System-wide configuration"""
    # System settings
    max_components: int = 100
    health_check_interval: int = 30
    initialization_timeout: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Performance
    max_concurrent_operations: int = 50
    operation_timeout: int = 300

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SystemConfig':
        """Create config from dictionary"""
        return cls(**config_dict)

class BacktestMode(Enum):
    """Backtest execution mode"""
    SINGLE_STRATEGY = "single_strategy"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_ADAPTIVE = "regime_adaptive"

@dataclass
class BacktestConfig:
    """
    Backtest-specific configuration

    Centralizes backtest settings while leveraging core_engine configs.
    Uses composition to integrate with DataConfig, RiskConfig, ExecutionConfig, AnalyticsConfig.

    Usage:
        from core_engine.config import (
            BacktestConfig, BacktestMode, DataConfig, RiskConfig,
            ExecutionConfig, AnalyticsConfig
        )

        config = BacktestConfig(
            backtest_name="My Backtest",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            symbols=["NVDA", "TSLA"],
            start_date="2024-01-02",
            end_date="2024-03-31"
        )
    """
    # Metadata
    backtest_name: str
    backtest_mode: BacktestMode = BacktestMode.SINGLE_STRATEGY
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Data settings (core_engine/config/component_config.py: DataConfig)
    symbols: List[str] = field(default_factory=list)
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""    # YYYY-MM-DD
    interval: str = "1min"
    # Warmup settings
    # If set, backtest will fetch and retain approximately this many *RTH bars* before the first
    # simulated bar for indicator/feature warmup (bars-based warmup).
    # If None, engine will infer a strategy-appropriate default.
    warmup_bars: Optional[int] = None

    # ClickHouse database settings (for backtesting data source)
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "polygon_data"  # Changed from market_data to match actual database

    # Execution settings (core_engine/config/component_config.py: ExecutionConfig)
    enable_realistic_fills: bool = True
    enable_liquidity_filtering: bool = True
    enable_cost_modeling: bool = True
    commission_per_trade: float = 0.005
    min_liquidity_score: float = 60.0
    max_spread_bps: float = 25.0

    # Market impact model (Rule 7 - Execution Management)
    impact_model: str = "almgren_chriss"  # or "kyle_lambda", "simple"
    linear_coefficient: float = 0.1
    sqrt_coefficient: float = 0.5
    base_slippage_bps: float = 2.0
    volatility_slippage_multiplier: float = 1.5
    default_fill_rate: float = 0.99
    partial_fills_enabled: bool = False

    # Risk settings (core_engine/config/component_config.py: RiskConfig)
    initial_capital: float = 1_000_000.0
    max_position_size: float = 0.10
    """Maximum position size as % of portfolio. Default: 0.10 (10%). Must be <= max_concentration."""
    max_position_pct: Optional[float] = None
    """
    Optional per-trade / per-order position cap as % of portfolio.
    If None, engines should default this to max_position_size for backwards compatibility.
    Must be <= max_position_size when provided.
    """
    max_total_exposure: float = 1.0
    max_concentration: float = 0.20
    """Maximum concentration per position. Default: 0.20 (20%). Single-symbol backtests need max_position_size < this."""
    allow_shorts: bool = False
    max_daily_var: float = 0.05
    max_drawdown: float = 0.20
    min_signal_confidence: float = 0.6
    
    # Strategy manager settings
    min_confidence_threshold: float = 0.6
    """Minimum confidence threshold for signals in strategy aggregator. Default: 0.6 (60%). For v5.0 simplified strategies, use 0.5."""

    # Risk authorization thresholds (for CentralRiskManager)
    auto_approval_threshold: float = 0.08
    """Auto-approve trades with risk impact < 8%. Default: 0.08 (8%)"""
    elevated_review_threshold: float = 0.15
    """Elevated review for risk impact 8-15%. Default: 0.15 (15%)"""
    emergency_threshold: float = 0.25
    """Emergency threshold - reject if risk impact > 25%. Default: 0.25 (25%)"""

    # Regime-adjusted multipliers (Rule 2 - Regime-First)
    enable_regime_adjustments: bool = True
    regime_risk_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'low_volatility': 1.2,
        'normal_volatility': 1.0,
        'high_volatility': 0.7,
        'extreme_volatility': 0.4
    })

    # Analytics settings (core_engine/config/component_config.py: AnalyticsConfig)
    risk_free_rate: float = 0.04  # 4% annual risk-free rate (for Sharpe ratio calculations)
    enable_regime_analysis: bool = True  # Enable regime-based analytics
    enable_regime_attribution: bool = True
    enable_strategy_attribution: bool = True
    enable_factor_attribution: bool = False
    generate_html_report: bool = True
    generate_json_report: bool = True
    generate_csv_trades: bool = True
    metrics_calculation_frequency: str = "end_of_day"
    enable_charts: bool = True
    chart_types: List[str] = field(default_factory=lambda: [
        "equity_curve", "drawdown", "monthly_returns", "regime_distribution"
    ])

    # Strategy configurations (for multi-strategy backtests)
    # For single strategy backtests, this can be empty and strategies are registered programmatically
    strategies: List[Dict[str, Any]] = field(default_factory=list)

    # Output settings
    output_directory: str = "backtest_results"
    save_intermediate_results: bool = False

    # Performance settings
    parallel_execution: bool = False
    max_workers: int = 4

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate backtest configuration

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate symbols
        if not self.symbols:
            errors.append("Must specify at least one symbol")

        # Validate dates
        if not self.start_date or not self.end_date:
            errors.append("Must specify start_date and end_date")
        else:
            try:
                start = datetime.strptime(self.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.end_date, "%Y-%m-%d")
                if end < start:
                    errors.append("end_date must be on or after start_date")
            except ValueError as e:
                errors.append(f"Invalid date format: {e}")

        # Validate interval
        if self.interval not in ["1min", "5min", "15min", "30min", "1H", "1D"]:
            errors.append(f"Invalid interval: {self.interval}")

        # Validate warmup bars
        if self.warmup_bars is not None and int(self.warmup_bars) < 0:
            errors.append("warmup_bars must be >= 0")

        # Validate risk parameters
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")

        if not 0.0 < self.max_position_size <= 1.0:
            errors.append("max_position_size must be between 0 and 1")

        if self.max_position_pct is not None:
            try:
                mpp = float(self.max_position_pct)
                if not 0.0 < mpp <= 1.0:
                    errors.append("max_position_pct must be between 0 and 1")
                if mpp > float(self.max_position_size):
                    errors.append("max_position_pct must be <= max_position_size")
            except Exception:
                errors.append("max_position_pct must be a float")

        if not 0.0 < self.max_daily_var <= 1.0:
            errors.append("max_daily_var must be between 0 and 1")

        # Validate liquidity settings
        if not 0.0 <= self.min_liquidity_score <= 100.0:
            errors.append("min_liquidity_score must be between 0 and 100")

        # Validate impact model
        if self.impact_model not in ["almgren_chriss", "kyle_lambda", "simple"]:
            errors.append(f"Invalid impact_model: {self.impact_model}")

        # Validate metrics frequency
        if self.metrics_calculation_frequency not in ["real_time", "end_of_day", "end_of_backtest"]:
            errors.append(f"Invalid metrics_calculation_frequency: {self.metrics_calculation_frequency}")

        return len(errors) == 0, errors

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """Create config from dictionary (supports YAML experiment configs)"""
        # Map YAML experiment config field names to BacktestConfig fields
        field_mappings = {
            'experiment_name': 'backtest_name',
            'initial_capital': 'initial_capital',
        }

        # Fields to ignore (not part of BacktestConfig)
        ignore_fields = {'experiment_type', 'save_trade_log', 'save_regime_log'}

        # Create a new dict with mapped fields
        mapped_dict = {}
        for key, value in config_dict.items():
            if key in ignore_fields:
                continue
            mapped_key = field_mappings.get(key, key)
            mapped_dict[mapped_key] = value

        # Convert backtest_mode string to enum if needed
        if 'backtest_mode' in mapped_dict and isinstance(mapped_dict['backtest_mode'], str):
            mapped_dict['backtest_mode'] = BacktestMode(mapped_dict['backtest_mode'])

        # Get valid field names from the dataclass
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cls)}

        # Filter to only valid fields
        filtered_dict = {k: v for k, v in mapped_dict.items() if k in valid_fields}

        return cls(**filtered_dict)

    @classmethod
    def from_json(cls, json_path: str) -> 'BacktestConfig':
        """Create BacktestConfig from JSON file (convenience method for testing)"""
        import json

        with open(json_path, 'r') as f:
            config_dict = json.load(f)

        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                config_dict[key] = value.value
            else:
                config_dict[key] = value
        return config_dict

    def __str__(self) -> str:
        """Human-readable summary"""
        return f"""
Backtest Configuration: {self.backtest_name}
{"=" * (24 + len(self.backtest_name))}
Mode: {self.backtest_mode.value}
Period: {self.start_date} to {self.end_date}
Symbols: {', '.join(self.symbols)}
Initial Capital: ${self.initial_capital:,.0f}
Output Directory: {self.output_directory}
        """.strip()
