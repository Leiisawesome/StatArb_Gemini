"""
Institutional Backtest Configuration System
==========================================

Complete configuration management for backtesting runs.
Follows Rule 10 (Production Standards) for configuration validation.

This configuration system maps to all 9 core_engine "Lego Brick" configurations:
- DataConfig → ClickHouseDataManager (Brick #2)
- StrategyConfig → StrategyManager (Brick #7)
- RiskConfig → CentralRiskManager (Brick #8)
- ExecutionConfig → UnifiedExecutionEngine (Brick #9) + LiquidityEngine (Brick #3)
- AnalyticsConfig → Analytics components (Bricks #10-12)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    """Backtest execution mode"""
    SINGLE_STRATEGY = "single_strategy"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_ADAPTIVE = "regime_adaptive"


@dataclass
class DataConfig:
    """
    Data configuration for backtest
    
    Maps to: BRICK #2 (ClickHouseDataManager)
    """
    symbols: List[str]
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    interval: str = "1min"  # 1min, 5min, 15min, 1H, 1D
    
    # ClickHouse connection
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "polygon_data"
    
    # Data quality
    enable_validation: bool = True
    min_data_points: int = 1000
    max_missing_pct: float = 0.05  # Max 5% missing data
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate data configuration"""
        errors = []
        
        if not self.symbols:
            errors.append("Must specify at least one symbol")
        
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            if end <= start:
                errors.append("end_date must be after start_date")
        except ValueError as e:
            errors.append(f"Invalid date format: {e}")
        
        if self.interval not in ["1min", "5min", "15min", "30min", "1H", "1D"]:
            errors.append(f"Invalid interval: {self.interval}")
        
        return len(errors) == 0, errors


@dataclass
class StrategyConfig:
    """
    Individual strategy configuration
    
    Maps to: BRICK #7 (StrategyManager) via EnhancedStrategyFactory
    """
    strategy_type: str  # 'momentum', 'mean_reversion', 'statistical_arbitrage', etc.
    strategy_name: str
    allocation_pct: float  # 0.0 - 1.0
    
    # Strategy parameters (strategy-specific)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Risk limits (per-strategy)
    max_position_size: float = 0.10  # 10% max per position
    max_concentration: float = 0.15  # 15% max concentration
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate strategy configuration"""
        errors = []
        
        # Valid strategy types (from EnhancedStrategyFactory)
        valid_types = [
            'momentum', 'mean_reversion', 'statistical_arbitrage', 'factor',
            'multi_asset', 'trend_following', 'breakout', 'pairs_trading',
            'volatility', 'arbitrage'
        ]
        
        if self.strategy_type not in valid_types:
            errors.append(f"Invalid strategy_type: {self.strategy_type}. Must be one of {valid_types}")
        
        if not 0.0 <= self.allocation_pct <= 1.0:
            errors.append(f"allocation_pct must be 0-1, got {self.allocation_pct}")
        
        if not 0.0 <= self.max_position_size <= 1.0:
            errors.append(f"max_position_size must be 0-1, got {self.max_position_size}")
        
        return len(errors) == 0, errors


@dataclass
class RiskConfig:
    """
    Risk management configuration
    
    Maps to: BRICK #8 (CentralRiskManager - GOVERNANCE)
    Implements: Rule 4 (Central Risk Management)
    """
    initial_capital: float = 1_000_000.0  # $1M default
    
    # Position limits
    max_position_size: float = 0.10  # 10% per position
    max_total_exposure: float = 1.0   # 100% total exposure
    max_concentration: float = 0.15   # 15% per symbol
    
    # Risk limits
    max_daily_var: float = 0.05       # 5% daily VaR
    max_drawdown: float = 0.20        # 20% max drawdown
    
    # Strategy limits
    max_strategies: int = 10
    min_signal_confidence: float = 0.6  # 60% min confidence
    
    # Regime-adjusted multipliers (Rule 13 integration)
    enable_regime_adjustments: bool = True
    regime_risk_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'low_volatility': 1.2,
        'normal_volatility': 1.0,
        'high_volatility': 0.7,
        'extreme_volatility': 0.4
    })
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate risk configuration"""
        errors = []
        
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
        
        if not 0.0 < self.max_position_size <= 1.0:
            errors.append("max_position_size must be 0-1")
        
        if not 0.0 < self.max_daily_var <= 1.0:
            errors.append("max_daily_var must be 0-1")
        
        return len(errors) == 0, errors


@dataclass
class ExecutionConfig:
    """
    Execution simulation configuration
    
    Maps to: BRICK #9 (UnifiedExecutionEngine) + BRICK #3 (LiquidityEngine)
    Implements: Rule 12 (Liquidity Management)
    """
    enable_realistic_fills: bool = True
    enable_liquidity_filtering: bool = True
    enable_cost_modeling: bool = True
    
    # Commission costs
    commission_per_trade: float = 0.005  # $0.005 per trade
    
    # Liquidity filtering (Rule 12 - BRICK #3)
    min_liquidity_score: float = 60.0  # Minimum 60/100
    max_spread_bps: float = 25.0       # Max 25 bps spread
    
    # Execution costs (Rule 12)
    apply_spread_cost: bool = True
    apply_market_impact: bool = True
    apply_slippage: bool = True
    
    # Market impact model
    impact_model: str = "almgren_chriss"  # or "kyle_lambda", "simple"
    linear_coefficient: float = 0.1
    sqrt_coefficient: float = 0.5
    
    # Slippage model
    base_slippage_bps: float = 2.0
    volatility_slippage_multiplier: float = 1.5
    
    # Fill simulation
    default_fill_rate: float = 0.99  # 99% fill rate
    partial_fills_enabled: bool = False
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate execution configuration"""
        errors = []
        
        if not 0.0 <= self.min_liquidity_score <= 100.0:
            errors.append("min_liquidity_score must be 0-100")
        
        if self.impact_model not in ["almgren_chriss", "kyle_lambda", "simple"]:
            errors.append(f"Invalid impact_model: {self.impact_model}")
        
        return len(errors) == 0, errors


@dataclass
class AnalyticsConfig:
    """
    Analytics and reporting configuration
    
    Maps to: BRICKS #10-12 (Analytics components)
    Implements: Rule 9 (Advanced Analytics)
    """
    enable_regime_attribution: bool = True
    enable_strategy_attribution: bool = True
    enable_factor_attribution: bool = False  # Fama-French (future)
    
    # Reporting
    generate_html_report: bool = True
    generate_json_report: bool = True
    generate_csv_trades: bool = True
    
    # Analytics frequency
    metrics_calculation_frequency: str = "end_of_day"  # or "real_time", "end_of_backtest"
    
    # Visualizations
    enable_charts: bool = True
    chart_types: List[str] = field(default_factory=lambda: [
        "equity_curve", "drawdown", "monthly_returns", "regime_distribution"
    ])
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate analytics configuration"""
        errors = []
        
        if self.metrics_calculation_frequency not in ["real_time", "end_of_day", "end_of_backtest"]:
            errors.append(f"Invalid metrics_calculation_frequency: {self.metrics_calculation_frequency}")
        
        return len(errors) == 0, errors


@dataclass
class BacktestConfiguration:
    """
    Complete backtest configuration
    
    This is the master configuration class that orchestrates all aspects
    of an institutional backtest run. It maps to all 9 core_engine Lego Bricks.
    
    Usage:
        # Create from scratch
        config = BacktestConfiguration(
            backtest_name="My Backtest",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            data=DataConfig(...),
            strategies=[StrategyConfig(...)],
            risk=RiskConfig(...),
            execution=ExecutionConfig(...),
            analytics=AnalyticsConfig(...)
        )
        
        # Save to JSON
        config.to_json(Path("my_backtest.json"))
        
        # Load from JSON
        config = BacktestConfiguration.from_json(Path("my_backtest.json"))
    """
    # Metadata (required fields first)
    backtest_name: str
    backtest_mode: BacktestMode
    
    # Component configurations (required fields - map to Lego Bricks)
    data: DataConfig                    # → BRICK #2
    strategies: List[StrategyConfig]    # → BRICK #7
    risk: RiskConfig                    # → BRICK #8
    execution: ExecutionConfig          # → BRICK #9 + #3
    analytics: AnalyticsConfig          # → BRICKS #10-12
    
    # Optional fields with defaults
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    output_directory: str = "backtest_results"
    save_intermediate_results: bool = False
    parallel_execution: bool = False
    max_workers: int = 4
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate complete configuration"""
        all_errors = []
        
        # Validate each section
        sections = [
            ("data", self.data),
            ("risk", self.risk),
            ("execution", self.execution),
            ("analytics", self.analytics)
        ]
        
        for section_name, section_config in sections:
            valid, errors = section_config.validate()
            if not valid:
                all_errors.extend([f"{section_name}: {e}" for e in errors])
        
        # Validate strategies
        if not self.strategies:
            all_errors.append("Must specify at least one strategy")
        
        for i, strategy in enumerate(self.strategies):
            valid, errors = strategy.validate()
            if not valid:
                all_errors.extend([f"strategy[{i}]: {e}" for e in errors])
        
        # Validate strategy allocations sum to <= 1.0
        total_allocation = sum(s.allocation_pct for s in self.strategies)
        if total_allocation > 1.0:
            all_errors.append(f"Total strategy allocation {total_allocation:.2f} > 1.0")
        
        return len(all_errors) == 0, all_errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        config_dict = asdict(self)
        # Convert enum to string
        config_dict['backtest_mode'] = self.backtest_mode.value
        return config_dict
    
    def to_json(self, filepath: Path) -> None:
        """Save configuration to JSON file"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"✅ Configuration saved to {filepath}")
    
    @classmethod
    def from_json(cls, filepath: Path) -> 'BacktestConfiguration':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        # Convert nested dicts to dataclass instances
        config_dict['backtest_mode'] = BacktestMode(config_dict['backtest_mode'])
        config_dict['data'] = DataConfig(**config_dict['data'])
        config_dict['strategies'] = [StrategyConfig(**s) for s in config_dict['strategies']]
        config_dict['risk'] = RiskConfig(**config_dict['risk'])
        config_dict['execution'] = ExecutionConfig(**config_dict['execution'])
        config_dict['analytics'] = AnalyticsConfig(**config_dict['analytics'])
        
        logger.info(f"✅ Configuration loaded from {filepath}")
        return cls(**config_dict)
    
    def __str__(self) -> str:
        """Human-readable summary"""
        return f"""
Backtest Configuration: {self.backtest_name}
{"=" * (24 + len(self.backtest_name))}
Mode: {self.backtest_mode.value}
Period: {self.data.start_date} to {self.data.end_date}
Symbols: {', '.join(self.data.symbols)}
Strategies: {len(self.strategies)} ({', '.join(s.strategy_name for s in self.strategies)})
Initial Capital: ${self.risk.initial_capital:,.0f}
Output Directory: {self.output_directory}
        """.strip()


def create_example_config() -> BacktestConfiguration:
    """
    Create example configuration for reference
    
    This demonstrates a simple single-strategy backtest configuration.
    """
    return BacktestConfiguration(
        backtest_name="Example Single Strategy Backtest",
        backtest_mode=BacktestMode.SINGLE_STRATEGY,
        data=DataConfig(
            symbols=["NVDA"],
            start_date="2024-01-02",
            end_date="2024-03-31",
            interval="1min"
        ),
        strategies=[
            StrategyConfig(
                strategy_type="momentum",
                strategy_name="momentum_60",
                allocation_pct=1.0,
                parameters={
                    "lookback_period": 60,
                    "momentum_threshold": 0.02,
                    "adx_threshold": 25.0
                }
            )
        ],
        risk=RiskConfig(
            initial_capital=1_000_000.0,
            max_position_size=0.10,
            enable_regime_adjustments=True
        ),
        execution=ExecutionConfig(
            enable_cost_modeling=True,
            enable_liquidity_filtering=True,
            min_liquidity_score=60.0
        ),
        analytics=AnalyticsConfig(
            enable_regime_attribution=True,
            enable_strategy_attribution=True,
            generate_html_report=True
        )
    )


if __name__ == "__main__":
    # Create and validate example configuration
    config = create_example_config()
    
    print("=" * 80)
    print("BACKTEST CONFIGURATION VALIDATION")
    print("=" * 80)
    print(config)
    print()
    
    valid, errors = config.validate()
    
    if valid:
        print("✅ Configuration valid!")
        print()
        
        # Save to file
        output_path = Path("example_backtest_config.json")
        config.to_json(output_path)
        print(f"✅ Saved to {output_path}")
        print()
        
        # Test loading
        loaded_config = BacktestConfiguration.from_json(output_path)
        print("✅ Successfully loaded configuration back from JSON")
        print()
        
    else:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"  - {error}")

