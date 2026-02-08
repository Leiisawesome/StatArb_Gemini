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
import json

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ..system.interfaces import ISystemComponent, IRegimePolicy
except ImportError:
    # Fallback definition for testing
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool: pass
        @abstractmethod
        async def start(self) -> bool: pass
        @abstractmethod
        async def stop(self) -> bool: pass
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abstractmethod
        def get_status(self) -> Dict[str, Any]: pass
    
    class IRegimePolicy(ABC):
        @abstractmethod
        def detect_regime(self, data: Any, **kwargs) -> Any: pass
        @abstractmethod
        def get_capabilities(self) -> Dict[str, Any]: pass

# Import canonical metric functions from core_metrics (Rule: Single Source of Truth)
try:
    from ..analytics.core_metrics import calculate_max_drawdown
except ImportError:
    calculate_max_drawdown = None

# Import centralized configuration (Rule 1, Section 7)
try:
    from ..config.component_config import RegimeConfig
except ImportError:
    RegimeConfig = None

# Import canonical MarketRegime from type_definitions (Single Source of Truth)
from ..type_definitions.regime import MarketRegime, MarketRegimeState, TimeframeRegime
RegimeType = MarketRegime # Alias for backward compatibility
RegimeState = MarketRegimeState # Alias for backward compatibility

# Lazy import for heavy classifier module (33.85MB sklearn dependency)
if TYPE_CHECKING:
    from .regime_classifier import RegimeClassification

# Import all regime components
from .regime_detector import RegimeDetector, RegimeDetection
from .market_regime_analyzer import MarketRegimeAnalyzer, CrossAssetRegime
# Lazy import: regime_classifier (33.85MB sklearn dependency) - import only when needed
from .regime_indicators import (RegimeIndicatorEngine, RegimeIndicator,
                              TransitionSignal, RegimeStrengthMeasure)
from .regime_transition_manager import (RegimeTransitionManager, TransitionPrediction,
                                      RebalancingRecommendation)
# Professional Grade Extraction (Rule 1: Separation of Concerns)
from .allocation import RegimeAwarePortfolioManager
from .attribution import RegimePerformanceAttributor

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

class RegimeManager(ISystemComponent, IRegimePolicy):
    """
    Central Regime Manager (Strategic Brain)

    Orchestrates the entire regime brick:
    - Long-term strategic regime detection
    - Real-time tactical regime sensing
    - Portfolio parameter adaptation
    - Multi-timeframe performance attribution
    
    Implements ISystemComponent for orchestrator integration (Rule 1).
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize regime manager with centralized configuration

        Args:
            config: RegimeConfig or dict (for backward compatibility)
        """

        # Use centralized RegimeConfig (Rule 1, Section 7)
        # Import at module level handles None gracefully
        from ..config.component_config import RegimeConfig as CentralizedRegimeConfig

        # Handle different config input types
        if isinstance(config, CentralizedRegimeConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = CentralizedRegimeConfig(**config) if config else CentralizedRegimeConfig()
        elif config is None:
            self.config = CentralizedRegimeConfig()
        else:
            # Try to use as-is (for backward compat with old RegimeManagerConfig)
            self.config = config if hasattr(config, 'update_frequency_hours') else CentralizedRegimeConfig()

        logger.info("✅ RegimeManager using centralized RegimeConfig (Rule 1, Section 7)")

        # ISystemComponent state (Rule 1)
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.initialization_time: Optional[datetime] = None
        self.analysis_count = 0

        # Lazy import for heavy modules
        from .engine import RealTimeRegimeSensor

        # Initialize all components with centralized config
        # Note: Sub-components will also be updated to use centralized config
        self.regime_detector = RegimeDetector(self.config)
        self.market_analyzer = MarketRegimeAnalyzer(self.config)
        self.indicator_engine = RegimeIndicatorEngine(self.config)
        self.transition_manager = RegimeTransitionManager(self.config)
        self.regime_sensor = RealTimeRegimeSensor(self.config)

        # Initialize specialized managers (Injected dependencies for Rule 1 purity)
        self.portfolio_manager = RegimeAwarePortfolioManager(self.config)
        self.performance_attribution = RegimePerformanceAttributor(self.config)

        # State management
        self.current_state: Optional[MarketRegimeState] = None
        self.state_history: List[MarketRegimeState] = []
        self.adaptation_history: List[RegimeAdaptation] = []

        # Orchestrator integration
        self.orchestrator: Optional[Any] = None

        # Status and control
        self.status = RegimeManagerStatus.INITIALIZING
        self.last_update = datetime.now()
        self.update_lock = asyncio.Lock()

        # Regime-First Notification System (Rule 1, Section 7)
        self.subscribers: List[IRegimeAware] = []

        # Async support
        self.executor = ThreadPoolExecutor(max_workers=self._get_config_attr("max_workers", 4))

        logger.info("Regime manager initialized")
        self.status = RegimeManagerStatus.READY

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="RegimeManager",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5  # Layer 0: REGIME-FIRST - Foundation for all components
        )

        logger.info(f"✅ RegimeManager registered with orchestrator: {self.component_id}")
        return self.component_id

    def add_subscriber(self, component: Any) -> None:
        """Add a regime-aware subscriber"""
        if component not in self.subscribers:
            self.subscribers.append(component)
            logger.info(f"Regime subscriber added: {type(component).__name__}")

    async def notify_subscribers(self, regime_state: MarketRegimeState) -> None:
        """Notify all subscribers of regime change (Rule 1, Section 7)"""
        from ..system.interfaces import RegimeContext
        
        # Convert MarketRegimeState to RegimeContext for public distribution
        context = RegimeContext(
            primary_regime=regime_state.primary_regime.value if hasattr(regime_state.primary_regime, 'value') else str(regime_state.primary_regime),
            regime_confidence=getattr(regime_state, 'regime_confidence', 0.8),
            regime_start_time=getattr(regime_state, 'transition_timestamp', datetime.now()),
            regime_duration_minutes=0.0, # Will be calculated on next update
            volatility_regime=regime_state.volatility_regime.value if hasattr(regime_state.volatility_regime, 'value') else str(regime_state.volatility_regime),
            trend_regime=regime_state.directional_regime.value if hasattr(regime_state.directional_regime, 'value') else str(regime_state.directional_regime),
            risk_multiplier=regime_state.risk_multiplier,
            last_update=datetime.now()
        )

        tasks = []
        for subscriber in self.subscribers:
            if hasattr(subscriber, "on_regime_change"):
                tasks.append(subscriber.on_regime_change(context))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Notified {len(tasks)} subscribers of regime change to {context.primary_regime}")

    def _get_config_attr(self, attr_name, default):

        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

    async def update_regime_analysis(self, market_data: Dict[str, pd.DataFrame],
                                   portfolio_data: Optional[Dict[str, Any]] = None) -> MarketRegimeState:
        """Update comprehensive regime analysis"""

        try:
            async with self.update_lock:
                self.status = RegimeManagerStatus.ANALYZING
                logger.info("Updating regime analysis")

                # 1. Update Real-Time Sensor (Low Latency Path)
                # Now using standardized IRegimePolicy interface
                sensor_results = {}
                for symbol, df in market_data.items():
                    sensor_results[symbol] = self.regime_sensor.detect_regime(df)

                # Run overall analyses
                if self._get_config_attr("async_processing", True):
                    # Async analysis
                    regime_state = await self._async_update_analysis(market_data, portfolio_data)
                else:
                    # Synchronous analysis
                    regime_state = self._sync_update_analysis(market_data, portfolio_data)

                # Link sensor data if available
                # (Optional: refine regime_state using sensor_results)
                if self.regime_sensor.current_regime:
                    regime_state.directional_regime = self.regime_sensor.current_regime.directional_regime
                    regime_state.volatility_regime = self.regime_sensor.current_regime.volatility_regime

                # Update state
                self.current_state = regime_state
                self.state_history.append(regime_state)

                # Limit history
                if len(self.state_history) > self._get_config_attr("max_history_length", 1000):
                    self.state_history = self.state_history[-self._get_config_attr("max_history_length", 1000)//2:]

                self.last_update = datetime.now()
                self.status = RegimeManagerStatus.READY

                # Notify subscribers (Rule 1, Section 7)
                await self.notify_subscribers(regime_state)

                logger.info(f"Regime analysis updated - Current regime: {regime_state.primary_regime.value}")
                return regime_state

        except Exception as e:
            logger.error(f"Error updating regime analysis: {e}")
            self.status = RegimeManagerStatus.ERROR
            return self.current_state or MarketRegimeState()

    def detect_regime(self, data: Any, **kwargs) -> MarketRegimeState:
        """Standardized entry point for regime detection (IRegimePolicy interface)"""
        # Orchestrator-level detection (Synchronous bridge)
        # Note: In production, use the async update_regime_analysis for real-time updates
        return self._sync_update_analysis(data, kwargs.get('portfolio_data'))

    def get_capabilities(self) -> Dict[str, Any]:
        """Returns metadata about what this policy can detect (IRegimePolicy interface)"""
        return {
            "policy_type": "Orchestrated (Brain)",
            "latency_profile": "Mixed (Fast Sensor + Slow Detector)",
            "sub_components": {
                "detector": self.regime_detector.get_capabilities(),
                "sensor": self.regime_sensor.get_capabilities()
            },
            "features": [
                "portfolio_adaptation",
                "performance_attribution",
                "consensus_logic",
                "multi_methodology"
            ]
        }

    async def _async_update_analysis(self, market_data: Dict[str, pd.DataFrame],
                                   portfolio_data: Optional[Dict[str, Any]]) -> MarketRegimeState:
        """Asynchronous regime analysis update"""

        try:
            # Extract returns data for regime detection
            returns_data = self._extract_returns_data(market_data)

            # Create async tasks
            loop = asyncio.get_event_loop()

            # Detection task
            detection_task = loop.run_in_executor(
                    self.executor,
                self.regime_detector.detect_regime,
                returns_data
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
            return MarketRegimeState()

    def _sync_update_analysis(self, market_data: Dict[str, pd.DataFrame],
                            portfolio_data: Optional[Dict[str, Any]]) -> MarketRegimeState:
        """Synchronous regime analysis update"""

        try:
            # Extract returns data for regime detection
            returns_data = self._extract_returns_data(market_data)

            # Detection
            detection_result = self.regime_detector.detect_regime(returns_data)

            # Market analysis
            analysis_result = self.market_analyzer.analyze_market_regime(market_data)

            # Indicators
            indicators_result = self.indicator_engine.calculate_all_indicators(returns_data)

            # Combine results
            regime_state = self._combine_analysis_results(
                detection_result, analysis_result, indicators_result, portfolio_data
            )

            return regime_state

        except Exception as e:
            logger.error(f"Error in sync regime analysis: {e}")
            return MarketRegimeState()

    def _extract_returns_data(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract returns data from market data symbols.
        Optimized vectorized extraction (Professional Grade).
        """
        try:
            if not market_data:
                return pd.DataFrame()

            returns_data = {}
            for symbol, df in market_data.items():
                if df.empty:
                    continue
                
                # Prioritize 'close' or 'price', then fallback to first numeric
                target_col = next((c for c in ['close', 'price'] if c in df.columns), None)
                if not target_col:
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if not numeric_cols.empty:
                        target_col = numeric_cols[0]
                
                if target_col:
                    returns_data[symbol] = df[target_col].pct_change()

            if not returns_data:
                return pd.DataFrame()

            # Vectorized concatenation is faster than building row-by-row
            returns_df = pd.DataFrame(returns_data).dropna()
            return returns_df

        except Exception as e:
            logger.error(f"Error extracting returns data: {e}", exc_info=True)
            return pd.DataFrame()

    def _combine_analysis_results(self, detection_result: Optional[RegimeDetection],
                                analysis_result: Dict[str, Any],
                                indicators_result: Dict[str, RegimeIndicator],
                                portfolio_data: Optional[Dict[str, Any]]) -> MarketRegimeState:
        """Combine analysis results into regime state"""

        try:
            regime_state = MarketRegimeState()

            # Primary regime from detection
            if detection_result:
                regime_state.primary_regime = detection_result.regime_type
                regime_state.regime_confidence = detection_result.confidence

                if detection_result.regime_start:
                    regime_state.regime_duration = (datetime.now() - detection_result.regime_start).days

            # Cross-asset regime analysis
            if 'cross_asset_regime' in analysis_result:
                regime_state.cross_asset_regime = analysis_result['cross_asset_regime']

            # Indicators
            regime_state.active_indicators = indicators_result

            # Transition signals
            transition_signals = self.indicator_engine.detect_regime_transitions(indicators_result)
            regime_state.transition_signals = transition_signals

            # Regime strength
            if regime_state.primary_regime != RegimeType.UNKNOWN:
                regime_strength = self.indicator_engine.calculate_regime_strength(
                    regime_state.primary_regime, indicators_result
                )
                regime_state.regime_strength = regime_strength

            # Transition prediction
            if portfolio_data and 'price_data' in portfolio_data:
                self.status = RegimeManagerStatus.PREDICTING
                transition_analysis = self.transition_manager.analyze_transition_opportunity(
                    portfolio_data['price_data'],
                    indicators_result,
                    regime_state.primary_regime,
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
            return MarketRegimeState()

    def _calculate_portfolio_implications(self, regime_state: MarketRegimeState,
                                        portfolio_data: Dict[str, Any]) -> MarketRegimeState:
        """Calculate portfolio implications of regime state"""

        try:
            current_portfolio = portfolio_data.get('current_portfolio', {})
            available_assets = portfolio_data.get('available_assets', list(current_portfolio.keys()))

            # Calculate optimal allocation for current regime
            optimal_allocation = self.portfolio_manager.calculate_regime_optimal_allocation(
                regime_state.primary_regime,
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

    def generate_regime_adaptation(self, regime_state: MarketRegimeState,
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

    def _should_adapt(self, regime_state: MarketRegimeState) -> bool:
        """Determine if adaptation is needed"""

        try:
            # Check regime change
            if (len(self.state_history) > 1 and
                self.state_history[-2].current_regime != regime_state.current_regime and
                regime_state.regime_confidence > self._get_config_attr("min_confidence_threshold", 0.6)):
                return True

            # Check high transition probability
            if (regime_state.transition_probability > self._get_config_attr("alert_thresholds", {}).get('regime_change_probability', 0.8) and
                regime_state.confidence_in_state > self._get_config_attr("min_confidence_threshold", 0.6)):
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

    def _get_adaptation_reason(self, regime_state: MarketRegimeState) -> str:
        """Get reason for adaptation"""

        reasons = []

        if len(self.state_history) > 1 and self.state_history[-2].current_regime != regime_state.current_regime:
            reasons.append(f"Regime change from {self.state_history[-2].current_regime.value} to {regime_state.current_regime.value}")

        if regime_state.transition_probability > 0.7:
            reasons.append(f"High transition probability ({regime_state.transition_probability:.2f})")

        if regime_state.rebalancing_recommendations:
            reasons.append(f"{len(regime_state.rebalancing_recommendations)} rebalancing triggers")

        return "; ".join(reasons) if reasons else "Regime-based optimization"

    def _calculate_strategy_adjustments(self, regime_state: MarketRegimeState,
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
                adjustment = (preferred_weight - current_weight) * confidence * self._get_config_attr("adaptation_speed", 0.5)

                # Limit adjustment magnitude
                max_adjustment = self._get_config_attr("max_portfolio_change", 0.25) * current_weight
                adjustment = np.clip(adjustment, -max_adjustment, max_adjustment)

                if abs(adjustment) > 0.01:  # 1% threshold
                    adjustments[strategy] = adjustment

            return adjustments

        except Exception as e:
            logger.error(f"Error calculating strategy adjustments: {e}")
            return {}

    def _calculate_risk_adjustments(self, regime_state: MarketRegimeState) -> Dict[str, float]:
        """Calculate risk budget adjustments"""

        try:
            adjustments = {}
            regime = regime_state.current_regime
            regime_state.risk_adjustment_factor

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
                                  regime_state: MarketRegimeState) -> RegimeAdaptation:
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
            if total_change > self._get_config_attr("max_portfolio_change", 0.25):
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
                                   regime_state: MarketRegimeState) -> RegimeAdaptation:
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

    # ========================================================================
    # ISystemComponent Implementation (Rule 1)
    # ========================================================================

    async def initialize(self) -> bool:
        """
        Initialize the regime manager

        Implements ISystemComponent.initialize() for orchestrator integration.

        Returns:
            bool: True if initialization successful
        """
        try:
            if self.is_initialized:
                logger.warning("RegimeManager already initialized")
                return True

            logger.info("🔧 Initializing RegimeManager...")

            # Initialize sub-components (already done in __init__)
            # Mark as initialized
            self.is_initialized = True
            self.initialization_time = datetime.now()
            self.status = RegimeManagerStatus.READY

            logger.info("✅ RegimeManager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ RegimeManager initialization failed: {e}")
            self.status = RegimeManagerStatus.ERROR
            return False

    async def start(self) -> bool:
        """
        Start the regime manager operations

        Implements ISystemComponent.start() for orchestrator integration.

        Returns:
            bool: True if start successful
        """
        try:
            if not self.is_initialized:
                logger.error("Cannot start RegimeManager: not initialized")
                return False

            if self.is_operational:
                logger.warning("RegimeManager already operational")
                return True

            logger.info("🚀 Starting RegimeManager...")

            # Mark as operational
            self.is_operational = True
            self.status = RegimeManagerStatus.READY

            logger.info("✅ RegimeManager started successfully")
            return True

        except Exception as e:
            logger.error(f"❌ RegimeManager start failed: {e}")
            self.status = RegimeManagerStatus.ERROR
            return False

    async def stop(self) -> bool:
        """
        Stop the regime manager operations

        Implements ISystemComponent.stop() for orchestrator integration.

        Returns:
            bool: True if stop successful
        """
        try:
            if not self.is_operational:
                logger.warning("RegimeManager not operational")
                return True

            logger.info("🛑 Stopping RegimeManager...")

            # Stop operations
            self.is_operational = False
            self.status = RegimeManagerStatus.MAINTENANCE

            # Shutdown executor (call existing method)
            self.shutdown()

            logger.info("✅ RegimeManager stopped successfully")
            return True

        except Exception as e:
            logger.error(f"❌ RegimeManager stop failed: {e}")
            return False

    def get_current_regime_context(self) -> Optional[MarketRegimeState]:
        """Get current regime context (SSOT for all components)"""
        return self.current_state

    def get_current_regime(self) -> Optional[MarketRegimeState]:
        """Alias for get_current_regime_context for backward compatibility"""
        return self.current_state

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on regime manager

        Implements ISystemComponent.health_check() for orchestrator integration.

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            # Basic health metrics
            is_healthy = (
                self.is_initialized and
                self.is_operational and
                self.status not in [RegimeManagerStatus.ERROR]
            )

            # Component health
            components_healthy = {
                'regime_detector': hasattr(self, 'regime_detector'),
                'market_analyzer': hasattr(self, 'market_analyzer'),
                'indicator_engine': hasattr(self, 'indicator_engine'),
                'transition_manager': hasattr(self, 'transition_manager'),
                'regime_sensor': hasattr(self, 'regime_sensor')
            }

            # Performance metrics
            uptime = (datetime.now() - self.initialization_time).total_seconds() if self.initialization_time else 0

            health_report = {
                'healthy': is_healthy,
                'status': self.status.value,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime,
                'analysis_count': self.analysis_count,
                'components': components_healthy,
                'all_components_healthy': all(components_healthy.values()),
                'current_state_available': self.current_state is not None,
                'state_history_size': len(self.state_history),
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'timestamp': datetime.now().isoformat()
            }

            return health_report

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of regime manager

        Implements ISystemComponent.get_status() for orchestrator integration.

        Returns:
            Dict[str, Any]: Current status information
        """
        try:
            status_info = {
                'component_type': 'RegimeManager',
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'status': self.status.value,
                'initialization_time': self.initialization_time.isoformat() if self.initialization_time else None,
                'analysis_count': self.analysis_count,
                'state_history_size': len(self.state_history),
                'adaptation_history_size': len(self.adaptation_history),
                'current_regime': self.current_state.current_regime.value if self.current_state else None,
                'regime_confidence': self.current_state.regime_confidence if self.current_state else 0.0,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'config': {
                    'update_frequency_hours': self._get_config_attr("update_frequency_hours", 1) if hasattr(self.config, 'update_frequency_hours') else None,
                    'confidence_threshold': self._get_config_attr("confidence_threshold", 0.6) if hasattr(self.config, 'confidence_threshold') else None
                }
            }

            return status_info

        except Exception as e:
            logger.error(f"Get status failed: {e}")
            return {
                'component_type': 'RegimeManager',
                'error': str(e)
            }