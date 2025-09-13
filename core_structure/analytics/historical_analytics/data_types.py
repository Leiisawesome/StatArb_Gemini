#!/usr/bin/env python3
"""
Data Types and Classes for Historical Analytics
==============================================

Defines all data structures and interfaces used throughout
the historical analytics framework.

Author: StatArb Gemini Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Import from existing validated components
from ..market_condition_analytics import MarketCondition, StrategyType


@dataclass
class HistoricalPeriod:
    """
    Represents a historical analysis period with metadata
    """
    name: str
    start_date: str  # Format: "YYYY-MM-DD"
    end_date: str    # Format: "YYYY-MM-DD"
    regime_hint: Optional[str] = None  # Expected regime for validation
    description: Optional[str] = None
    category: Optional[str] = None  # e.g., "crisis", "bull", "bear", "volatile", "sideways"
    
    def __post_init__(self):
        """Validate dates and calculate derived properties"""
        try:
            self.start_datetime = datetime.strptime(self.start_date, "%Y-%m-%d")
            self.end_datetime = datetime.strptime(self.end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format in period '{self.name}': {e}")
        
        if self.start_datetime >= self.end_datetime:
            raise ValueError(f"Start date must be before end date in period '{self.name}'")
    
    @property
    def duration_days(self) -> int:
        """Calculate duration in days"""
        return (self.end_datetime - self.start_datetime).days
    
    @property
    def duration_months(self) -> float:
        """Calculate duration in months (approximate)"""
        return self.duration_days / 30.44  # Average days per month
    
    def overlaps_with(self, other: 'HistoricalPeriod') -> bool:
        """Check if this period overlaps with another period"""
        return not (self.end_datetime <= other.start_datetime or 
                   self.start_datetime >= other.end_datetime)


@dataclass
class MarketDataset:
    """
    Market data for a specific historical period with enrichment
    """
    period: HistoricalPeriod
    market_data: pd.DataFrame
    macro_data: Optional[Dict[str, Any]] = None
    sentiment_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived properties"""
        if self.market_data is not None and not self.market_data.empty:
            self.total_data_points = len(self.market_data)
            self.symbols = list(self.market_data['symbol'].unique()) if 'symbol' in self.market_data.columns else []
            self.date_range = {
                'start': self.market_data['timestamp'].min() if 'timestamp' in self.market_data.columns else None,
                'end': self.market_data['timestamp'].max() if 'timestamp' in self.market_data.columns else None
            }
        else:
            self.total_data_points = 0
            self.symbols = []
            self.date_range = {'start': None, 'end': None}
    
    @property
    def is_valid(self) -> bool:
        """Check if dataset is valid for analysis"""
        return (self.market_data is not None and 
                not self.market_data.empty and 
                self.total_data_points > 100)  # Minimum data requirement


@dataclass
class RegimeDetectionResult:
    """
    Result from regime detection for a specific period
    """
    period: HistoricalPeriod
    detected_regime: MarketCondition
    confidence: float
    regime_strength: float
    market_stress: float
    supporting_indicators: Dict[str, Any]
    transition_probability: Dict[MarketCondition, float]
    data_points_analyzed: int
    detection_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeStats:
    """
    Statistical information about a market regime across historical periods
    """
    frequency: float  # How often this regime occurs (0-1)
    avg_confidence: float  # Average confidence when detected
    avg_duration_days: float  # Average duration in days
    total_occurrences: int  # Total number of times detected
    dominant_periods: List[str]  # Period names where regime was strongly detected
    key_characteristics: Dict[str, Any]  # Typical market characteristics
    transition_patterns: Dict[str, float]  # Common transitions from this regime


@dataclass
class RegimeAnalysisOutput:
    """
    Complete output from comprehensive regime analysis
    """
    regime_results: List[RegimeDetectionResult]
    regime_distribution: Dict[str, RegimeStats]  # regime_name -> stats
    transition_matrix: Dict[str, Dict[str, float]]  # from_regime -> to_regime -> probability
    regime_clusters: Dict[str, Any]  # Advanced clustering results
    analysis_metadata: Dict[str, Any]
    
    @property
    def total_periods_analyzed(self) -> int:
        """Total number of periods analyzed"""
        return len(self.regime_results)
    
    @property
    def avg_confidence(self) -> float:
        """Average confidence across all detections"""
        if not self.regime_results:
            return 0.0
        return sum(r.confidence for r in self.regime_results) / len(self.regime_results)
    
    def get_regime_accuracy(self, regime_hints_available: bool = True) -> float:
        """
        Calculate regime detection accuracy if regime hints are available
        """
        if not regime_hints_available:
            return None
        
        correct_detections = 0
        total_with_hints = 0
        
        for result in self.regime_results:
            if result.period.regime_hint:
                total_with_hints += 1
                if result.detected_regime.value == result.period.regime_hint:
                    correct_detections += 1
        
        return correct_detections / total_with_hints if total_with_hints > 0 else 0.0


@dataclass
class InstrumentScore:
    """
    Performance score for an instrument in a specific strategy/regime combination
    """
    symbol: str
    strategy: StrategyType
    regime: MarketCondition
    expected_return: float  # Annualized expected return
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float  # Percentage of profitable periods
    regime_consistency: float  # How consistently it performs in this regime
    volatility: float
    correlation_to_market: float
    composite_score: float  # Overall ranking score
    sample_size: int  # Number of data points used for calculation
    confidence_interval: Dict[str, float] = field(default_factory=dict)  # 95% CI for returns
    
    def __post_init__(self):
        """Validate score ranges"""
        if not -1.0 <= self.expected_return <= 5.0:  # Reasonable annual return range
            raise ValueError(f"Expected return {self.expected_return} outside reasonable range")
        if not 0.0 <= self.win_rate <= 1.0:
            raise ValueError(f"Win rate {self.win_rate} must be between 0 and 1")
        if not 0.0 <= self.regime_consistency <= 1.0:
            raise ValueError(f"Regime consistency {self.regime_consistency} must be between 0 and 1")


@dataclass
class InstrumentRankings:
    """
    Comprehensive instrument rankings across all strategies and regimes
    """
    strategy_rankings: Dict[str, Dict[str, List[InstrumentScore]]]  # strategy -> regime -> instruments
    ranking_metadata: Dict[str, Any]
    generation_timestamp: datetime = field(default_factory=datetime.now)
    
    def get_top_instruments(self, strategy: str, regime: str, top_n: int = 10) -> List[InstrumentScore]:
        """Get top N instruments for a strategy/regime combination"""
        if strategy not in self.strategy_rankings:
            return []
        if regime not in self.strategy_rankings[strategy]:
            return []
        return self.strategy_rankings[strategy][regime][:top_n]
    
    def get_instrument_score(self, symbol: str, strategy: str, regime: str) -> Optional[InstrumentScore]:
        """Get score for a specific instrument/strategy/regime combination"""
        instruments = self.get_top_instruments(strategy, regime, top_n=1000)  # Get all
        for instrument in instruments:
            if instrument.symbol == symbol:
                return instrument
        return None


@dataclass
class AnalysisOutputPaths:
    """
    File paths for persisted analysis outputs
    """
    regime_distribution: Path
    regime_transitions: Path
    detailed_results: Path
    regime_clusters: Optional[Path] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))


@dataclass
class RankingsOutputPaths:
    """
    File paths for persisted ranking outputs
    """
    strategy_files: Dict[str, Path]  # strategy_name -> file_path
    summary_file: Optional[Path] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))


@dataclass
class BacktestConfig:
    """
    Configuration for a single backtest execution
    """
    config_id: str
    name: str
    strategy: str
    instruments: List[str]
    regime_context: str
    parameters: Dict[str, Any]
    risk_params: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    config_type: str = "optimized"  # "optimized", "baseline", "stress"
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.instruments:
            raise ValueError("Backtest config must have at least one instrument")
        if not self.strategy:
            raise ValueError("Backtest config must specify a strategy")


@dataclass  
class BacktestSuite:
    """
    Complete suite of backtest configurations
    """
    optimized_configs: List[BacktestConfig]
    baseline_configs: List[BacktestConfig]
    stress_configs: List[BacktestConfig]
    suite_metadata: Dict[str, Any]
    generation_timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def total_configs(self) -> int:
        """Total number of configurations in the suite"""
        return len(self.optimized_configs) + len(self.baseline_configs) + len(self.stress_configs)
    
    def get_configs_by_strategy(self, strategy: str) -> List[BacktestConfig]:
        """Get all configurations for a specific strategy"""
        all_configs = self.optimized_configs + self.baseline_configs + self.stress_configs
        return [config for config in all_configs if config.strategy == strategy]


@dataclass
class BacktestResult:
    """
    Result from a single backtest execution
    """
    config_id: str
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades_count: int
    execution_metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResults:
    """
    Complete results from backtest suite execution
    """
    results: Dict[str, List[BacktestResult]]  # config_type -> results
    performance_comparison: Dict[str, Any]
    execution_metadata: Dict[str, Any]


@dataclass
class AnalysisResults:
    """
    Complete results from historical market analytics pipeline
    """
    regime_analysis: RegimeAnalysisOutput
    instrument_rankings: InstrumentRankings
    analysis_paths: AnalysisOutputPaths
    rankings_paths: RankingsOutputPaths
    backtest_suite: Optional[BacktestSuite] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_metrics(self) -> Dict[str, Any]:
        """Calculate key success metrics"""
        return {
            "regime_accuracy": self.regime_analysis.get_regime_accuracy(),
            "avg_confidence": self.regime_analysis.avg_confidence,
            "total_periods": self.regime_analysis.total_periods_analyzed,
            "total_instruments_ranked": sum(
                len(instruments) 
                for strategy_rankings in self.instrument_rankings.strategy_rankings.values()
                for instruments in strategy_rankings.values()
            ),
            "backtest_configs_generated": self.backtest_suite.total_configs if self.backtest_suite else 0
        }


# Type aliases for convenience
StrategyRegimeRankings = Dict[str, Dict[str, List[InstrumentScore]]]
RegimeTransitionMatrix = Dict[str, Dict[str, float]]
PerformanceMetrics = Dict[str, Union[float, int, str]]


# Validation functions
def validate_historical_period(period: HistoricalPeriod) -> bool:
    """Validate a historical period"""
    try:
        return (period.duration_days > 7 and  # Minimum 1 week
                period.duration_days < 3650)     # Maximum 10 years
    except Exception:
        return False


def validate_market_dataset(dataset: MarketDataset) -> bool:
    """Validate a market dataset"""
    return (dataset.is_valid and
            len(dataset.symbols) > 0 and
            dataset.total_data_points >= 100)


def validate_regime_analysis(analysis: RegimeAnalysisOutput) -> bool:
    """Validate regime analysis output"""
    return (len(analysis.regime_results) > 0 and
            len(analysis.regime_distribution) > 0 and
            analysis.avg_confidence > 0.0)