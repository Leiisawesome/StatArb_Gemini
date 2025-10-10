"""
Regime Detection Engine - Central Regime Manager
Central coordinator for regime-aware strategy adaptation, portfolio management,
risk controls, and performance attribution by regime
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import warnings
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import json

# Lazy import for heavy classifier module (33.85MB sklearn dependency)
if TYPE_CHECKING:
    from .regime_classifier import (RegimeClassifier, RegimeClassification, 
                                  ClassificationConfig, ModelPerformance)

# Import all regime components
from .regime_detector import (RegimeDetector, RegimeType, RegimeDetection, 
                             DetectionMethod, RegimeDetectionConfig)
from .market_regime_analyzer import (MarketRegimeAnalyzer, CrossAssetRegime, 
                                   RegimeAnalysisConfig, AssetRegimeProfile)
# Lazy import: regime_classifier (33.85MB sklearn dependency) - import only when needed
from .regime_indicators import (RegimeIndicatorEngine, RegimeIndicator, 
                              TransitionSignal, RegimeStrengthMeasure, IndicatorConfig)
from .regime_transition_manager import (RegimeTransitionManager, TransitionPrediction, 
                                      RebalancingRecommendation, TransitionMonitoring,
                                      TransitionPredictionConfig)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class RegimeManagerStatus(Enum):
    """Regime manager operational status"""
    INITIALIZING = "initializing"
    READY = "ready"
    ANALYZING = "analyzing"
    PREDICTING = "predicting"
    REBALANCING = "rebalancing"
    MONITORING = "monitoring"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AdaptationMode(Enum):
    """Strategy adaptation modes"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class RegimeManagerConfig:
    """Configuration for regime manager"""
    
    # Component configurations
    detection_config: RegimeDetectionConfig = field(default_factory=RegimeDetectionConfig)
    analysis_config: RegimeAnalysisConfig = field(default_factory=RegimeAnalysisConfig)
    classification_config: Optional['ClassificationConfig'] = None  # Lazy-loaded
    indicator_config: IndicatorConfig = field(default_factory=IndicatorConfig)
    transition_config: TransitionPredictionConfig = field(default_factory=TransitionPredictionConfig)
    
    # Manager-specific settings
    update_frequency: int = 1  # Hours
    min_confidence_threshold: float = 0.6
    regime_persistence_threshold: int = 3  # Days
    
    # Adaptation settings
    adaptation_mode: AdaptationMode = AdaptationMode.MODERATE
    max_portfolio_change: float = 0.25  # Maximum 25% change
    adaptation_speed: float = 0.5  # 0-1 scale, higher = faster adaptation
    
    # Risk management
    max_regime_risk_multiplier: float = 2.0
    emergency_stop_loss: float = -0.10  # 10% emergency stop
    max_drawdown_threshold: float = -0.15  # 15% max drawdown
    
    # Performance monitoring
    performance_attribution_window: int = 252  # Days
    benchmark_tracking: bool = True
    regime_specific_benchmarks: Dict[RegimeType, str] = field(default_factory=dict)
    
    # Alerts and notifications
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'regime_change_probability': 0.8,
        'volatility_spike': 0.3,
        'correlation_breakdown': 0.7,
        'performance_deviation': 0.05
    })
    
    # Data management
    max_history_length: int = 1000  # Days
    backup_frequency: int = 24  # Hours
    
    # Threading and async
    max_workers: int = 4
    async_processing: bool = True


@dataclass
class RegimeState:
    """Current regime state"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Primary regime information
    current_regime: RegimeType = RegimeType.UNKNOWN
    regime_confidence: float = 0.0
    regime_duration: int = 0  # Days in current regime
    
    # Secondary regime assessments
    cross_asset_regime: Optional[CrossAssetRegime] = None
    classification_result: Optional['RegimeClassification'] = None  # Lazy-loaded type
    
    # Indicators and signals
    active_indicators: Dict[str, RegimeIndicator] = field(default_factory=dict)
    transition_signals: List[TransitionSignal] = field(default_factory=list)
    regime_strength: Optional[RegimeStrengthMeasure] = None
    
    # Transition information
    transition_prediction: Optional[TransitionPrediction] = None
    transition_probability: float = 0.0
    predicted_next_regime: RegimeType = RegimeType.UNKNOWN
    
    # Risk and portfolio implications
    risk_adjustment_factor: float = 1.0
    recommended_portfolio_adjustments: Dict[str, float] = field(default_factory=dict)
    rebalancing_recommendations: List[RebalancingRecommendation] = field(default_factory=list)
    
    # Performance context
    regime_performance_attribution: Dict[RegimeType, float] = field(default_factory=dict)
    current_regime_performance: float = 0.0
    
    # Metadata
    last_update: datetime = field(default_factory=datetime.now)
    update_frequency_achieved: float = 1.0  # Actual vs target frequency
    confidence_in_state: float = 0.0  # Overall confidence in regime state


@dataclass
class RegimeAdaptation:
    """Regime-based strategy adaptation"""
    
    adaptation_timestamp: datetime = field(default_factory=datetime.now)
    
    # Adaptation trigger
    trigger_regime: RegimeType = RegimeType.UNKNOWN
    adaptation_reason: str = ""
    
    # Strategy adjustments
    strategy_weights: Dict[str, float] = field(default_factory=dict)
    strategy_parameters: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Risk adjustments
    risk_budget_adjustments: Dict[str, float] = field(default_factory=dict)
    volatility_target_adjustment: float = 1.0
    position_sizing_adjustment: float = 1.0
    
    # Portfolio adjustments
    asset_allocation_changes: Dict[str, float] = field(default_factory=dict)
    sector_allocation_changes: Dict[str, float] = field(default_factory=dict)
    
    # Implementation details
    implementation_urgency: str = "normal"  # normal, high, emergency
    phased_implementation: bool = False
    expected_implementation_time: int = 1  # Days
    
    # Expected outcomes
    expected_performance_impact: float = 0.0
    expected_risk_impact: float = 0.0
    expected_volatility_impact: float = 0.0
    
    # Validation
    adaptation_confidence: float = 0.0
    back_test_validation: Optional[Dict[str, float]] = None


class RegimeAwarePortfolioManager:
    """Regime-aware portfolio management"""
    
    def __init__(self, config: RegimeManagerConfig):
        self.config = config
        
        logger.info("Regime-aware portfolio manager initialized")
    
    def calculate_regime_optimal_allocation(self, current_regime: RegimeType,
                                          regime_confidence: float,
                                          available_assets: List[str]) -> Dict[str, float]:
        """Calculate optimal allocation for current regime"""
        
        try:
            # Regime-specific allocation logic
            allocation = {}
            
            if current_regime == RegimeType.BULL_MARKET:
                allocation = self._get_bull_market_allocation(available_assets)
            elif current_regime == RegimeType.BEAR_MARKET:
                allocation = self._get_bear_market_allocation(available_assets)
            elif current_regime == RegimeType.HIGH_VOLATILITY:
                allocation = self._get_high_volatility_allocation(available_assets)
            elif current_regime == RegimeType.LOW_VOLATILITY:
                allocation = self._get_low_volatility_allocation(available_assets)
            elif current_regime == RegimeType.CRISIS:
                allocation = self._get_crisis_allocation(available_assets)
            elif current_regime == RegimeType.SIDEWAYS:
                allocation = self._get_sideways_allocation(available_assets)
            else:
                allocation = self._get_neutral_allocation(available_assets)
            
            # Adjust based on confidence
            allocation = self._adjust_for_confidence(allocation, regime_confidence)
            
            # Normalize to sum to 1
            total_weight = sum(allocation.values())
            if total_weight > 0:
                allocation = {asset: weight / total_weight for asset, weight in allocation.items()}
            
            return allocation
            
        except Exception as e:
            logger.error(f"Error calculating regime optimal allocation: {e}")
            return {}
    
    def _get_bull_market_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for bull market regime"""
        
        # Aggressive equity allocation
        allocation = {}
        equity_weight = 0.7
        
        # Prioritize growth assets
        growth_assets = [asset for asset in assets if any(x in asset.upper() for x in ['QQQ', 'TECH', 'GROWTH'])]
        value_assets = [asset for asset in assets if any(x in asset.upper() for x in ['VALUE', 'DIVIDEND'])]
        
        if growth_assets:
            for asset in growth_assets[:3]:  # Top 3 growth assets
                allocation[asset] = equity_weight / min(3, len(growth_assets))
        
        # Add some value exposure
        remaining_weight = 1.0 - sum(allocation.values())
        if value_assets and remaining_weight > 0:
            for asset in value_assets[:2]:
                allocation[asset] = remaining_weight / min(2, len(value_assets)) * 0.6
        
        # Small cash position
        remaining_weight = 1.0 - sum(allocation.values())
        if remaining_weight > 0:
            cash_assets = [asset for asset in assets if 'CASH' in asset.upper() or 'BILL' in asset.upper()]
            if cash_assets:
                allocation[cash_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_bear_market_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for bear market regime"""
        
        allocation = {}
        
        # Defensive allocation
        defensive_assets = [asset for asset in assets if any(x in asset.upper() for x in ['BOND', 'TREASURY', 'GOLD'])]
        cash_assets = [asset for asset in assets if any(x in asset.upper() for x in ['CASH', 'BILL'])]
        
        # High bond/treasury allocation
        if defensive_assets:
            for asset in defensive_assets[:3]:
                allocation[asset] = 0.4 / min(3, len(defensive_assets))
        
        # Significant cash position
        if cash_assets:
            allocation[cash_assets[0]] = 0.3
        
        # Minimal equity exposure
        equity_assets = [asset for asset in assets if any(x in asset.upper() for x in ['SPY', 'EQUITY', 'STOCK'])]
        if equity_assets:
            allocation[equity_assets[0]] = 0.2
        
        # Alternative investments
        remaining_weight = 1.0 - sum(allocation.values())
        alt_assets = [asset for asset in assets if any(x in asset.upper() for x in ['GOLD', 'COMMODITY'])]
        if alt_assets and remaining_weight > 0:
            allocation[alt_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_high_volatility_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for high volatility regime"""
        
        allocation = {}
        
        # Risk-off positioning
        low_vol_assets = [asset for asset in assets if any(x in asset.upper() for x in ['BOND', 'TREASURY', 'UTILITY'])]
        cash_assets = [asset for asset in assets if any(x in asset.upper() for x in ['CASH', 'BILL'])]
        
        # Conservative allocation
        if low_vol_assets:
            for asset in low_vol_assets[:2]:
                allocation[asset] = 0.4 / min(2, len(low_vol_assets))
        
        if cash_assets:
            allocation[cash_assets[0]] = 0.4
        
        # Small equity position
        remaining_weight = 1.0 - sum(allocation.values())
        if remaining_weight > 0:
            equity_assets = [asset for asset in assets if 'SPY' in asset.upper()]
            if equity_assets:
                allocation[equity_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_low_volatility_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for low volatility regime"""
        
        allocation = {}
        
        # Higher risk allocation during low vol
        equity_assets = [asset for asset in assets if any(x in asset.upper() for x in ['SPY', 'QQQ', 'EQUITY'])]
        
        if equity_assets:
            for asset in equity_assets[:3]:
                allocation[asset] = 0.6 / min(3, len(equity_assets))
        
        # Some fixed income
        bond_assets = [asset for asset in assets if any(x in asset.upper() for x in ['BOND', 'TREASURY'])]
        if bond_assets:
            allocation[bond_assets[0]] = 0.3
        
        # Small cash position
        remaining_weight = 1.0 - sum(allocation.values())
        if remaining_weight > 0:
            cash_assets = [asset for asset in assets if 'CASH' in asset.upper()]
            if cash_assets:
                allocation[cash_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_crisis_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for crisis regime"""
        
        allocation = {}
        
        # Flight to quality
        treasury_assets = [asset for asset in assets if 'TREASURY' in asset.upper() or 'TLT' in asset.upper()]
        cash_assets = [asset for asset in assets if any(x in asset.upper() for x in ['CASH', 'BILL'])]
        gold_assets = [asset for asset in assets if 'GOLD' in asset.upper()]
        
        # Heavy treasury allocation
        if treasury_assets:
            allocation[treasury_assets[0]] = 0.5
        
        # High cash
        if cash_assets:
            allocation[cash_assets[0]] = 0.3
        
        # Gold hedge
        if gold_assets:
            allocation[gold_assets[0]] = 0.15
        
        # Minimal equity
        remaining_weight = 1.0 - sum(allocation.values())
        if remaining_weight > 0:
            equity_assets = [asset for asset in assets if 'SPY' in asset.upper()]
            if equity_assets:
                allocation[equity_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_sideways_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get allocation for sideways regime"""
        
        allocation = {}
        
        # Balanced allocation for range-bound markets
        equity_assets = [asset for asset in assets if any(x in asset.upper() for x in ['SPY', 'EQUITY'])]
        bond_assets = [asset for asset in assets if any(x in asset.upper() for x in ['BOND', 'TREASURY'])]
        
        # Equal weight equity/bonds
        if equity_assets:
            allocation[equity_assets[0]] = 0.4
        
        if bond_assets:
            allocation[bond_assets[0]] = 0.4
        
        # Cash buffer
        remaining_weight = 1.0 - sum(allocation.values())
        if remaining_weight > 0:
            cash_assets = [asset for asset in assets if 'CASH' in asset.upper()]
            if cash_assets:
                allocation[cash_assets[0]] = remaining_weight
        
        return allocation
    
    def _get_neutral_allocation(self, assets: List[str]) -> Dict[str, float]:
        """Get neutral allocation when regime is uncertain"""
        
        # Conservative balanced allocation
        allocation = {}
        
        if len(assets) > 0:
            # Equal weight among first few assets (up to 5)
            weight_per_asset = 1.0 / min(5, len(assets))
            for asset in assets[:5]:
                allocation[asset] = weight_per_asset
        
        return allocation
    
    def _adjust_for_confidence(self, allocation: Dict[str, float], confidence: float) -> Dict[str, float]:
        """Adjust allocation based on regime confidence"""
        
        try:
            if confidence < 0.5:
                # Low confidence - move toward neutral allocation
                neutral_weight = 1.0 / len(allocation) if allocation else 0
                adjustment_factor = confidence * 2  # 0-1 scale
                
                adjusted_allocation = {}
                for asset, weight in allocation.items():
                    adjusted_weight = (weight * adjustment_factor + 
                                     neutral_weight * (1 - adjustment_factor))
                    adjusted_allocation[asset] = adjusted_weight
                
                return adjusted_allocation
            else:
                # High confidence - use allocation as is
                return allocation
                
        except Exception as e:
            logger.error(f"Error adjusting for confidence: {e}")
            return allocation


class RegimePerformanceAttribution:
    """Regime-based performance attribution"""
    
    def __init__(self, config: RegimeManagerConfig):
        self.config = config
        self.regime_performance_history: Dict[RegimeType, List[float]] = {}
        
        logger.info("Regime performance attribution initialized")
    
    def calculate_regime_attribution(self, portfolio_returns: pd.Series,
                                   regime_history: pd.Series,
                                   benchmark_returns: Optional[pd.Series] = None) -> Dict[str, Any]:
        """Calculate performance attribution by regime"""
        
        try:
            attribution = {}
            
            # Align data
            common_index = portfolio_returns.index.intersection(regime_history.index)
            portfolio_aligned = portfolio_returns.loc[common_index]
            regime_aligned = regime_history.loc[common_index]
            
            if benchmark_returns is not None:
                benchmark_aligned = benchmark_returns.loc[common_index]
            else:
                benchmark_aligned = pd.Series(0, index=common_index)
            
            # Calculate performance by regime
            regime_performance = {}
            regime_periods = {}
            
            for regime_type in RegimeType:
                if regime_type == RegimeType.UNKNOWN:
                    continue
                
                regime_mask = regime_aligned == regime_type
                if regime_mask.sum() == 0:
                    continue
                
                regime_returns = portfolio_aligned[regime_mask]
                regime_benchmark = benchmark_aligned[regime_mask]
                
                performance_stats = {
                    'total_return': (1 + regime_returns).prod() - 1,
                    'annualized_return': regime_returns.mean() * 252,
                    'volatility': regime_returns.std() * np.sqrt(252),
                    'sharpe_ratio': (regime_returns.mean() / regime_returns.std() * np.sqrt(252) 
                                   if regime_returns.std() > 0 else 0),
                    'max_drawdown': self._calculate_max_drawdown(regime_returns),
                    'periods': regime_mask.sum(),
                    'win_rate': (regime_returns > 0).mean(),
                    'avg_win': regime_returns[regime_returns > 0].mean() if (regime_returns > 0).sum() > 0 else 0,
                    'avg_loss': regime_returns[regime_returns < 0].mean() if (regime_returns < 0).sum() > 0 else 0
                }
                
                # Relative to benchmark
                if benchmark_returns is not None:
                    excess_returns = regime_returns - regime_benchmark
                    performance_stats.update({
                        'excess_return': excess_returns.mean() * 252,
                        'tracking_error': excess_returns.std() * np.sqrt(252),
                        'information_ratio': (excess_returns.mean() / excess_returns.std() * np.sqrt(252)
                                            if excess_returns.std() > 0 else 0),
                        'alpha': excess_returns.mean() * 252,
                        'beta': np.cov(regime_returns, regime_benchmark)[0, 1] / np.var(regime_benchmark)
                                if np.var(regime_benchmark) > 0 else 1.0
                    })
                
                regime_performance[regime_type.value] = performance_stats
                regime_periods[regime_type.value] = regime_mask.sum()
            
            # Overall attribution
            total_periods = len(portfolio_aligned)
            regime_contributions = {}
            
            for regime_name, stats in regime_performance.items():
                weight = regime_periods[regime_name] / total_periods
                contribution = stats['total_return'] * weight
                regime_contributions[regime_name] = {
                    'weight': weight,
                    'return': stats['total_return'],
                    'contribution': contribution
                }
            
            attribution = {
                'regime_performance': regime_performance,
                'regime_contributions': regime_contributions,
                'total_attribution': sum(contrib['contribution'] for contrib in regime_contributions.values()),
                'best_regime': max(regime_performance.keys(), 
                                 key=lambda x: regime_performance[x]['total_return']) if regime_performance else None,
                'worst_regime': min(regime_performance.keys(), 
                                  key=lambda x: regime_performance[x]['total_return']) if regime_performance else None,
                'most_frequent_regime': max(regime_periods.keys(), 
                                          key=lambda x: regime_periods[x]) if regime_periods else None
            }
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error calculating regime attribution: {e}")
            return {}
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def update_regime_performance_history(self, regime: RegimeType, performance: float):
        """Update performance history for regime"""
        
        try:
            if regime not in self.regime_performance_history:
                self.regime_performance_history[regime] = []
            
            self.regime_performance_history[regime].append(performance)
            
            # Limit history length
            max_history = 252  # 1 year of daily data
            if len(self.regime_performance_history[regime]) > max_history:
                self.regime_performance_history[regime] = self.regime_performance_history[regime][-max_history:]
                
        except Exception as e:
            logger.error(f"Error updating regime performance history: {e}")


class RegimeManager:
    """
    Central Regime Manager
    
    Integrates all regime detection and analysis components to provide
    comprehensive regime-aware trading and portfolio management.
    """
    
    def __init__(self, config: Optional[RegimeManagerConfig] = None):
        """Initialize regime manager"""
        
        # Lazy import regime_classifier (33.85MB sklearn dependency)
        from .regime_classifier import RegimeClassifier, ClassificationConfig
        
        self.config = config or RegimeManagerConfig()
        
        # Create classification config if not provided (lazy loading)
        if self.config.classification_config is None:
            self.config.classification_config = ClassificationConfig()
        
        # Initialize all components
        self.regime_detector = RegimeDetector(self.config.detection_config)
        self.market_analyzer = MarketRegimeAnalyzer(self.config.analysis_config)
        self.regime_classifier = RegimeClassifier(self.config.classification_config)
        self.indicator_engine = RegimeIndicatorEngine(self.config.indicator_config)
        self.transition_manager = RegimeTransitionManager(self.config.transition_config)
        
        # Initialize managers
        self.portfolio_manager = RegimeAwarePortfolioManager(self.config)
        self.performance_attribution = RegimePerformanceAttribution(self.config)
        
        # State management
        self.current_state: Optional[RegimeState] = None
        self.state_history: List[RegimeState] = []
        self.adaptation_history: List[RegimeAdaptation] = []
        
        # Status and control
        self.status = RegimeManagerStatus.INITIALIZING
        self.last_update = datetime.now()
        self.update_lock = threading.Lock()
        
        # Async support
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        logger.info("Regime manager initialized")
        self.status = RegimeManagerStatus.READY
    
    async def update_regime_analysis(self, market_data: Dict[str, pd.DataFrame],
                                   portfolio_data: Optional[Dict[str, Any]] = None) -> RegimeState:
        """Update comprehensive regime analysis"""
        
        try:
            with self.update_lock:
                self.status = RegimeManagerStatus.ANALYZING
                logger.info("Updating regime analysis")
                
                # Run all analyses
                if self.config.async_processing:
                    # Async analysis
                    regime_state = await self._async_update_analysis(market_data, portfolio_data)
                else:
                    # Synchronous analysis
                    regime_state = self._sync_update_analysis(market_data, portfolio_data)
                
                # Update state
                self.current_state = regime_state
                self.state_history.append(regime_state)
                
                # Limit history
                if len(self.state_history) > self.config.max_history_length:
                    self.state_history = self.state_history[-self.config.max_history_length//2:]
                
                self.last_update = datetime.now()
                self.status = RegimeManagerStatus.READY
                
                logger.info(f"Regime analysis updated - Current regime: {regime_state.current_regime.value}")
                return regime_state
                
        except Exception as e:
            logger.error(f"Error updating regime analysis: {e}")
            self.status = RegimeManagerStatus.ERROR
            return self.current_state or RegimeState()
    
    async def _async_update_analysis(self, market_data: Dict[str, pd.DataFrame],
                                   portfolio_data: Optional[Dict[str, Any]]) -> RegimeState:
        """Asynchronous regime analysis update"""
        
        try:
            # Create async tasks
            loop = asyncio.get_event_loop()
            
            # Detection task
            detection_task = loop.run_in_executor(
                self.executor,
                self.regime_detector.detect_regime,
                market_data
            )
            
            # Analysis task
            analysis_task = loop.run_in_executor(
                self.executor,
                self.market_analyzer.analyze_market_regime,
                market_data
            )
            
            # Indicators task
            returns_data = self._extract_returns_data(market_data)
            indicators_task = loop.run_in_executor(
                self.executor,
                self.indicator_engine.calculate_all_indicators,
                returns_data
            )
            
            # Wait for all tasks
            detection_result, analysis_result, indicators_result = await asyncio.gather(
                detection_task, analysis_task, indicators_task
            )
            
            # Combine results
            regime_state = self._combine_analysis_results(
                detection_result, analysis_result, indicators_result, portfolio_data
            )
            
            return regime_state
            
        except Exception as e:
            logger.error(f"Error in async regime analysis: {e}")
            return RegimeState()
    
    def _sync_update_analysis(self, market_data: Dict[str, pd.DataFrame],
                            portfolio_data: Optional[Dict[str, Any]]) -> RegimeState:
        """Synchronous regime analysis update"""
        
        try:
            # Detection
            detection_result = self.regime_detector.detect_regime(market_data)
            
            # Market analysis
            analysis_result = self.market_analyzer.analyze_market_regime(market_data)
            
            # Indicators
            returns_data = self._extract_returns_data(market_data)
            indicators_result = self.indicator_engine.calculate_all_indicators(returns_data)
            
            # Combine results
            regime_state = self._combine_analysis_results(
                detection_result, analysis_result, indicators_result, portfolio_data
            )
            
            return regime_state
            
        except Exception as e:
            logger.error(f"Error in sync regime analysis: {e}")
            return RegimeState()
    
    def _extract_returns_data(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract returns data from market data"""
        
        try:
            returns_dict = {}
            
            for symbol, data in market_data.items():
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                elif 'price' in data.columns:
                    returns = data['price'].pct_change().dropna()
                else:
                    # Use first numeric column
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        returns = data[numeric_cols[0]].pct_change().dropna()
                    else:
                        continue
                
                returns_dict[symbol] = returns
            
            if not returns_dict:
                return pd.DataFrame()
            
            returns_df = pd.DataFrame(returns_dict).dropna()
            return returns_df
            
        except Exception as e:
            logger.error(f"Error extracting returns data: {e}")
            return pd.DataFrame()
    
    def _combine_analysis_results(self, detection_result: Optional[RegimeDetection],
                                analysis_result: Dict[str, Any],
                                indicators_result: Dict[str, RegimeIndicator],
                                portfolio_data: Optional[Dict[str, Any]]) -> RegimeState:
        """Combine analysis results into regime state"""
        
        try:
            regime_state = RegimeState()
            
            # Primary regime from detection
            if detection_result:
                regime_state.current_regime = detection_result.regime_type
                regime_state.regime_confidence = detection_result.confidence
                
                if detection_result.regime_start_date:
                    regime_state.regime_duration = (datetime.now() - detection_result.regime_start_date).days
            
            # Cross-asset regime analysis
            if 'cross_asset_regime' in analysis_result:
                regime_state.cross_asset_regime = analysis_result['cross_asset_regime']
            
            # Indicators
            regime_state.active_indicators = indicators_result
            
            # Transition signals
            transition_signals = self.indicator_engine.detect_regime_transitions(indicators_result)
            regime_state.transition_signals = transition_signals
            
            # Regime strength
            if regime_state.current_regime != RegimeType.UNKNOWN:
                regime_strength = self.indicator_engine.calculate_regime_strength(
                    regime_state.current_regime, indicators_result
                )
                regime_state.regime_strength = regime_strength
            
            # Transition prediction
            if portfolio_data and 'price_data' in portfolio_data:
                self.status = RegimeManagerStatus.PREDICTING
                transition_analysis = self.transition_manager.analyze_transition_opportunity(
                    portfolio_data['price_data'],
                    indicators_result,
                    regime_state.current_regime,
                    portfolio_data.get('current_portfolio', {})
                )
                
                if 'transition_prediction' in transition_analysis:
                    regime_state.transition_prediction = transition_analysis['transition_prediction']
                    regime_state.transition_probability = transition_analysis['transition_prediction'].transition_probability
                    regime_state.predicted_next_regime = transition_analysis['transition_prediction'].predicted_regime
                
                if 'rebalancing_recommendations' in transition_analysis:
                    regime_state.rebalancing_recommendations = transition_analysis['rebalancing_recommendations']
            
            # Portfolio implications
            if portfolio_data:
                regime_state = self._calculate_portfolio_implications(regime_state, portfolio_data)
            
            # Overall confidence
            confidences = [
                regime_state.regime_confidence,
                regime_state.regime_strength.overall_strength if regime_state.regime_strength else 0.5,
                regime_state.transition_prediction.prediction_confidence if regime_state.transition_prediction else 0.5
            ]
            regime_state.confidence_in_state = sum(confidences) / len(confidences)
            
            return regime_state
            
        except Exception as e:
            logger.error(f"Error combining analysis results: {e}")
            return RegimeState()
    
    def _calculate_portfolio_implications(self, regime_state: RegimeState,
                                        portfolio_data: Dict[str, Any]) -> RegimeState:
        """Calculate portfolio implications of regime state"""
        
        try:
            current_portfolio = portfolio_data.get('current_portfolio', {})
            available_assets = portfolio_data.get('available_assets', list(current_portfolio.keys()))
            
            # Calculate optimal allocation for current regime
            optimal_allocation = self.portfolio_manager.calculate_regime_optimal_allocation(
                regime_state.current_regime,
                regime_state.regime_confidence,
                available_assets
            )
            
            # Calculate recommended adjustments
            adjustments = {}
            for asset in set(list(current_portfolio.keys()) + list(optimal_allocation.keys())):
                current_weight = current_portfolio.get(asset, 0)
                optimal_weight = optimal_allocation.get(asset, 0)
                adjustment = optimal_weight - current_weight
                
                # Only include significant adjustments
                if abs(adjustment) > 0.01:  # 1% threshold
                    adjustments[asset] = adjustment
            
            regime_state.recommended_portfolio_adjustments = adjustments
            
            # Risk adjustment factor
            if regime_state.transition_prediction:
                regime_state.risk_adjustment_factor = regime_state.transition_prediction.risk_increase_factor
            elif regime_state.current_regime in [RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY]:
                regime_state.risk_adjustment_factor = 1.5
            elif regime_state.current_regime == RegimeType.LOW_VOLATILITY:
                regime_state.risk_adjustment_factor = 0.8
            else:
                regime_state.risk_adjustment_factor = 1.0
            
            return regime_state
            
        except Exception as e:
            logger.error(f"Error calculating portfolio implications: {e}")
            return regime_state
    
    def generate_regime_adaptation(self, regime_state: RegimeState,
                                 current_strategies: Dict[str, float],
                                 force_adaptation: bool = False) -> Optional[RegimeAdaptation]:
        """Generate regime-based strategy adaptation"""
        
        try:
            # Check if adaptation is needed
            if not force_adaptation and not self._should_adapt(regime_state):
                return None
            
            self.status = RegimeManagerStatus.REBALANCING
            
            adaptation = RegimeAdaptation(
                trigger_regime=regime_state.current_regime,
                adaptation_reason=self._get_adaptation_reason(regime_state)
            )
            
            # Strategy weight adjustments
            adaptation.strategy_weights = self._calculate_strategy_adjustments(
                regime_state, current_strategies
            )
            
            # Risk adjustments
            adaptation.risk_budget_adjustments = self._calculate_risk_adjustments(regime_state)
            adaptation.volatility_target_adjustment = regime_state.risk_adjustment_factor
            adaptation.position_sizing_adjustment = 1.0 / regime_state.risk_adjustment_factor
            
            # Portfolio adjustments
            adaptation.asset_allocation_changes = regime_state.recommended_portfolio_adjustments
            
            # Implementation details
            adaptation = self._set_implementation_details(adaptation, regime_state)
            
            # Expected outcomes
            adaptation = self._calculate_expected_outcomes(adaptation, regime_state)
            
            # Store adaptation
            self.adaptation_history.append(adaptation)
            
            # Limit history
            if len(self.adaptation_history) > 100:
                self.adaptation_history = self.adaptation_history[-50:]
            
            logger.info(f"Generated regime adaptation for {regime_state.current_regime.value}")
            return adaptation
            
        except Exception as e:
            logger.error(f"Error generating regime adaptation: {e}")
            return None
        finally:
            self.status = RegimeManagerStatus.READY
    
    def _should_adapt(self, regime_state: RegimeState) -> bool:
        """Determine if adaptation is needed"""
        
        try:
            # Check regime change
            if (len(self.state_history) > 1 and 
                self.state_history[-2].current_regime != regime_state.current_regime and
                regime_state.regime_confidence > self.config.min_confidence_threshold):
                return True
            
            # Check high transition probability
            if (regime_state.transition_probability > self.config.alert_thresholds.get('regime_change_probability', 0.8) and
                regime_state.confidence_in_state > self.config.min_confidence_threshold):
                return True
            
            # Check significant portfolio adjustments needed
            if regime_state.recommended_portfolio_adjustments:
                max_adjustment = max(abs(adj) for adj in regime_state.recommended_portfolio_adjustments.values())
                if max_adjustment > 0.1:  # 10% adjustment threshold
                    return True
            
            # Check urgent rebalancing recommendations
            urgent_recommendations = [rec for rec in regime_state.rebalancing_recommendations
                                    if rec.urgency in ['strong', 'very_strong']]
            if urgent_recommendations:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking adaptation need: {e}")
            return False
    
    def _get_adaptation_reason(self, regime_state: RegimeState) -> str:
        """Get reason for adaptation"""
        
        reasons = []
        
        if len(self.state_history) > 1 and self.state_history[-2].current_regime != regime_state.current_regime:
            reasons.append(f"Regime change from {self.state_history[-2].current_regime.value} to {regime_state.current_regime.value}")
        
        if regime_state.transition_probability > 0.7:
            reasons.append(f"High transition probability ({regime_state.transition_probability:.2f})")
        
        if regime_state.rebalancing_recommendations:
            reasons.append(f"{len(regime_state.rebalancing_recommendations)} rebalancing triggers")
        
        return "; ".join(reasons) if reasons else "Regime-based optimization"
    
    def _calculate_strategy_adjustments(self, regime_state: RegimeState,
                                      current_strategies: Dict[str, float]) -> Dict[str, float]:
        """Calculate strategy weight adjustments"""
        
        try:
            adjustments = {}
            regime = regime_state.current_regime
            confidence = regime_state.regime_confidence
            
            # Regime-specific strategy preferences
            strategy_preferences = {
                RegimeType.BULL_MARKET: {'momentum': 0.4, 'growth': 0.3, 'trend_following': 0.3},
                RegimeType.BEAR_MARKET: {'mean_reversion': 0.4, 'defensive': 0.4, 'hedge': 0.2},
                RegimeType.HIGH_VOLATILITY: {'mean_reversion': 0.5, 'defensive': 0.3, 'hedge': 0.2},
                RegimeType.LOW_VOLATILITY: {'momentum': 0.3, 'carry': 0.3, 'growth': 0.4},
                RegimeType.CRISIS: {'defensive': 0.6, 'hedge': 0.3, 'cash': 0.1},
                RegimeType.SIDEWAYS: {'mean_reversion': 0.6, 'range_trading': 0.4}
            }
            
            preferred_weights = strategy_preferences.get(regime, {})
            
            for strategy, current_weight in current_strategies.items():
                preferred_weight = preferred_weights.get(strategy, current_weight)
                
                # Adjust based on confidence
                adjustment = (preferred_weight - current_weight) * confidence * self.config.adaptation_speed
                
                # Limit adjustment magnitude
                max_adjustment = self.config.max_portfolio_change * current_weight
                adjustment = np.clip(adjustment, -max_adjustment, max_adjustment)
                
                if abs(adjustment) > 0.01:  # 1% threshold
                    adjustments[strategy] = adjustment
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error calculating strategy adjustments: {e}")
            return {}
    
    def _calculate_risk_adjustments(self, regime_state: RegimeState) -> Dict[str, float]:
        """Calculate risk budget adjustments"""
        
        try:
            adjustments = {}
            regime = regime_state.current_regime
            risk_factor = regime_state.risk_adjustment_factor
            
            # Risk adjustments by regime
            if regime in [RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY]:
                adjustments['overall_risk'] = -0.3  # Reduce risk by 30%
                adjustments['max_position_size'] = -0.2
                adjustments['leverage'] = -0.5
            elif regime == RegimeType.LOW_VOLATILITY:
                adjustments['overall_risk'] = 0.2  # Increase risk by 20%
                adjustments['max_position_size'] = 0.1
                adjustments['leverage'] = 0.2
            elif regime == RegimeType.BEAR_MARKET:
                adjustments['overall_risk'] = -0.2
                adjustments['max_position_size'] = -0.15
                adjustments['leverage'] = -0.3
            
            # Adjust based on transition probability
            if regime_state.transition_probability > 0.7:
                for key in adjustments:
                    adjustments[key] *= 0.5  # Reduce adjustments during uncertain transitions
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error calculating risk adjustments: {e}")
            return {}
    
    def _set_implementation_details(self, adaptation: RegimeAdaptation,
                                  regime_state: RegimeState) -> RegimeAdaptation:
        """Set implementation details for adaptation"""
        
        try:
            # Implementation urgency
            if regime_state.current_regime == RegimeType.CRISIS:
                adaptation.implementation_urgency = "emergency"
                adaptation.expected_implementation_time = 0  # Immediate
            elif regime_state.transition_probability > 0.8:
                adaptation.implementation_urgency = "high"
                adaptation.expected_implementation_time = 1
            else:
                adaptation.implementation_urgency = "normal"
                adaptation.expected_implementation_time = 2
            
            # Phased implementation for large changes
            total_change = sum(abs(change) for change in adaptation.asset_allocation_changes.values())
            if total_change > self.config.max_portfolio_change:
                adaptation.phased_implementation = True
                adaptation.expected_implementation_time *= 2
            
            # Adaptation confidence
            adaptation.adaptation_confidence = (
                regime_state.regime_confidence * 0.4 +
                regime_state.confidence_in_state * 0.4 +
                (1 - regime_state.transition_probability) * 0.2  # Less confidence during transitions
            )
            
            return adaptation
            
        except Exception as e:
            logger.error(f"Error setting implementation details: {e}")
            return adaptation
    
    def _calculate_expected_outcomes(self, adaptation: RegimeAdaptation,
                                   regime_state: RegimeState) -> RegimeAdaptation:
        """Calculate expected outcomes of adaptation"""
        
        try:
            # Expected performance impact (simplified)
            regime_performance_map = {
                RegimeType.BULL_MARKET: 0.02,  # 2% expected improvement
                RegimeType.BEAR_MARKET: -0.01,  # Accept some loss for protection
                RegimeType.HIGH_VOLATILITY: -0.005,  # Small cost for stability
                RegimeType.LOW_VOLATILITY: 0.01,
                RegimeType.CRISIS: -0.02,  # Protection focus
                RegimeType.SIDEWAYS: 0.005
            }
            
            adaptation.expected_performance_impact = regime_performance_map.get(
                regime_state.current_regime, 0.0
            )
            
            # Expected risk impact
            adaptation.expected_risk_impact = regime_state.risk_adjustment_factor - 1.0
            
            # Expected volatility impact
            if regime_state.transition_prediction:
                adaptation.expected_volatility_impact = (
                    regime_state.transition_prediction.volatility_increase_factor - 1.0
                )
            else:
                adaptation.expected_volatility_impact = adaptation.expected_risk_impact * 0.5
            
            return adaptation
            
        except Exception as e:
            logger.error(f"Error calculating expected outcomes: {e}")
            return adaptation
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get comprehensive regime summary"""
        
        try:
            if not self.current_state:
                return {'status': 'not_initialized'}
            
            state = self.current_state
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'status': self.status.value,
                'current_regime': {
                    'type': state.current_regime.value,
                    'confidence': state.regime_confidence,
                    'duration_days': state.regime_duration,
                    'strength': state.regime_strength.overall_strength if state.regime_strength else 0.0
                },
                'transition_outlook': {
                    'probability': state.transition_probability,
                    'predicted_regime': state.predicted_next_regime.value,
                    'signals_count': len(state.transition_signals)
                },
                'portfolio_implications': {
                    'risk_adjustment_factor': state.risk_adjustment_factor,
                    'recommended_adjustments_count': len(state.recommended_portfolio_adjustments),
                    'rebalancing_recommendations': len(state.rebalancing_recommendations)
                },
                'indicators_summary': {
                    'total_indicators': len(state.active_indicators),
                    'strong_signals': len([ind for ind in state.active_indicators.values() 
                                         if ind.signal_strength.value in ['strong', 'very_strong']])
                },
                'overall_confidence': state.confidence_in_state,
                'last_update': self.last_update.isoformat(),
                'adaptations_count': len(self.adaptation_history)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating regime summary: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def export_regime_state(self, filename: Optional[str] = None) -> str:
        """Export current regime state to file"""
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"regime_state_{timestamp}.json"
            
            if not self.current_state:
                return ""
            
            # Prepare export data
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'regime_manager_status': self.status.value,
                'current_state': {
                    'current_regime': self.current_state.current_regime.value,
                    'regime_confidence': self.current_state.regime_confidence,
                    'regime_duration': self.current_state.regime_duration,
                    'transition_probability': self.current_state.transition_probability,
                    'predicted_next_regime': self.current_state.predicted_next_regime.value,
                    'risk_adjustment_factor': self.current_state.risk_adjustment_factor,
                    'confidence_in_state': self.current_state.confidence_in_state,
                    'indicators_count': len(self.current_state.active_indicators),
                    'transition_signals_count': len(self.current_state.transition_signals),
                    'rebalancing_recommendations_count': len(self.current_state.rebalancing_recommendations)
                },
                'recent_adaptations': [
                    {
                        'timestamp': adapt.adaptation_timestamp.isoformat(),
                        'trigger_regime': adapt.trigger_regime.value,
                        'reason': adapt.adaptation_reason,
                        'urgency': adapt.implementation_urgency,
                        'confidence': adapt.adaptation_confidence
                    }
                    for adapt in self.adaptation_history[-5:]  # Last 5 adaptations
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Regime state exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting regime state: {e}")
            return ""
    
    def shutdown(self):
        """Shutdown regime manager"""
        
        try:
            self.status = RegimeManagerStatus.MAINTENANCE
            
            # Shutdown executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            
            logger.info("Regime manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")