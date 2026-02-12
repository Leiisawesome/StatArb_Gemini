#!/usr/bin/env python3
"""
Enhanced Technical Indicators Engine for Core Engine
====================================================

Architecturally compliant technical indicators engine following core_engine patterns.
Integrates with existing signal processing components while maintaining independence.

Key Features:
- Follows core_engine component architecture patterns
- Configurable indicator sets with professional defaults
- Vectorized calculations for performance
- Integration with strategy and signal generation systems
- Compatible with existing core_engine types and interfaces

Author: StatArb_Gemini Core Engine (Architecture Compliant)
Version: 2.0.0 (Enhanced Architecture)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import warnings
import uuid
from datetime import datetime
warnings.filterwarnings('ignore')

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
from ...system.interfaces import ISystemComponent, IRegimeAware

# Core engine architectural compliance
from abc import ABC, abstractmethod

class IIndicatorProcessor(ABC):
    """Interface for indicator processing components"""

    @abstractmethod
    def calculate_indicators(
        self,
        data: pd.DataFrame,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Calculate indicators for market data"""

    @abstractmethod
    def get_supported_indicators(self) -> List[str]:
        """Get list of supported indicators"""

logger = logging.getLogger(__name__)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
from core_engine.config import IndicatorConfig as EnhancedIndicatorConfig

@dataclass
class IndicatorResult:
    """Result container for calculated indicators (core_engine pattern)"""
    symbol: str
    timestamp: pd.Timestamp
    indicators: Dict[str, float]
    signals: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'indicators': self.indicators,
            'signals': self.signals,
            'metadata': self.metadata
        }

@dataclass
class MultiTimeframeIndicatorResult:
    """Result container for multi-timeframe indicators (Tier 2 Enhancement #4)"""
    symbol: str
    timestamp: pd.Timestamp
    timeframe_indicators: Dict[str, Dict[str, float]]  # timeframe -> indicators
    consensus_signals: Dict[str, Any] = field(default_factory=dict)
    timeframe_alignment: float = 0.0  # 0-1 alignment score across timeframes
    dominant_timeframe: str = "1D"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MacroRegimeIndicators:
    """Container for macro regime indicators (Tier 2 Enhancement #4)"""
    timestamp: pd.Timestamp
    vix_regime: str = "normal"  # low, normal, elevated, extreme
    yield_curve_regime: str = "normal"  # steep, normal, flat, inverted
    dollar_strength: float = 0.0  # -1 to 1 (weak to strong)
    commodity_trend: str = "neutral"  # bearish, neutral, bullish
    credit_spread_regime: str = "normal"  # tight, normal, wide, stressed
    cross_asset_correlation: float = 0.0  # 0-1 correlation strength
    macro_regime_score: float = 0.0  # -1 to 1 (bearish to bullish)
    regime_confidence: float = 0.0  # 0-1 confidence in macro assessment

class EnhancedTechnicalIndicators(IIndicatorProcessor, ISystemComponent, IRegimeAware):
    """
    Enhanced Technical Indicators Engine with ISystemComponent & IRegimeAware Integration

    Institutional-grade technical indicators engine with orchestrator integration:
    - Implements ISystemComponent for lifecycle management (Rule 1)
    - Implements IRegimeAware for regime adaptation (Rule 2)
    - Configuration-driven initialization
    - Performance-optimized calculations
    - Integration with signal generation pipeline
    - Professional indicator defaults
    - Health monitoring and status reporting

    Key Features:
    - 42+ professional technical indicators
    - Vectorized calculations for performance
    - Signal generation integration
    - Caching and optimization support
    - Compatible with existing core_engine components
    - Orchestrator integration and lifecycle management
    - Regime-aware indicator parameter adaptation
    """

    def __init__(self, config: Optional[EnhancedIndicatorConfig] = None):
        # Handle both EnhancedIndicatorConfig objects and dictionaries
        # Rule 1 Section 7: Use centralized configuration from core_engine.config
        if isinstance(config, dict):
            # Convert dictionary to EnhancedIndicatorConfig object
            try:
                from core_engine.config import IndicatorConfig
                self.config = IndicatorConfig(**{k: v for k, v in config.items() if hasattr(IndicatorConfig, k)})
            except ImportError:
                # Fallback during migration
                self.config = EnhancedIndicatorConfig(**{k: v for k, v in config.items() if k in EnhancedIndicatorConfig.__dataclass_fields__})
        else:
            self.config = config or EnhancedIndicatorConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None

        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference

        # PHASE 3: Regime awareness (Rule 2 Regime-First)
        self.regime_engine: Optional[Any] = None  # EnhancedRegimeEngine reference
        self.current_regime: Optional[Any] = None  # Current regime context

        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedTechnicalIndicators',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_calculations': 0,
                'successful_calculations': 0,
                'failed_calculations': 0,
                'average_calculation_time': 0.0,
                'cache_hit_rate': 0.0
            }
        }

        # Performance optimization
        self._indicator_cache: Dict[str, Any] = {} if self.config.enable_caching else None

        # Supported indicators registry (core_engine pattern)
        self._supported_indicators = self._initialize_indicator_registry()

        self.logger.info(f"🚀 Enhanced Technical Indicators initialized with component ID: {self.component_id}")
        self.logger.info(f"📊 Loaded {len(self._supported_indicators)} indicators")
        self.liquidity_engine: Optional[Any] = None
        self.current_liquidity: Optional[Dict[str, Any]] = None
        self._base_bb_std = getattr(self.config, 'bb_std', getattr(self.config, 'bollinger_std', 2.0))
        self._base_bb_period = getattr(self.config, 'bb_period', getattr(self.config, 'bollinger_period', 20))
        self._base_volume_sma_period = getattr(self.config, 'volume_sma_period', 20)

    def _initialize_indicator_registry(self) -> List[str]:
        """Initialize registry of supported indicators"""
        return [
            # Moving Averages
            'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_9', 'ema_21', 'ema_50',

            # Momentum
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'stoch_k', 'stoch_d', 'williams_r',

            # Volatility
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_percent',
            'atr', 'true_range',

            # Volume
            'volume_sma', 'volume_ratio',

            # Trend
            'adx', 'aroon_up', 'aroon_down', 'aroon_oscillator',

            # Price Patterns
            'pivot_points', 'support_resistance'
        ]

    def get_supported_indicators(self) -> List[str]:
        """Get list of supported indicators (interface compliance)"""
        return self._supported_indicators.copy()

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedTechnicalIndicators",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15  # PHASE 3: After DataManager(10), before Features(16)
        )

        self.logger.info(f"✅ EnhancedTechnicalIndicators registered with orchestrator: {self.component_id}")
        return self.component_id

    def set_liquidity_engine(self, liquidity_engine: Any) -> None:
        """Inject liquidity engine reference for liquidity-aware adjustments"""
        self.liquidity_engine = liquidity_engine
        self.logger.debug("✅ Liquidity engine reference set for indicators")

    # ========================================
    # PHASE 3: REGIME AWARENESS (RULE 2 - IRegimeAware Interface)
    # ========================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine reference for regime-aware indicator calculation (Rule 2 Regime-First)
        Part of IRegimeAware interface implementation.
        """
        self.regime_engine = regime_engine
        self.logger.info(f"✅ RegimeEngine injected into TechnicalIndicators (IRegimeAware, Rule 2)")

    async def on_regime_change(self, new_regime_context: Any) -> None:
        """
        Handle regime change event - IRegimeAware interface method
        Callback for regime changes from the EnhancedRegimeEngine.
        Adapt indicator parameters based on new market regime.

        Args:
            new_regime_context: New regime context with updated information (RegimeContext or compatible object)
        """
        previous_regime = self.current_regime.primary_regime.value if (self.current_regime and hasattr(self.current_regime, 'primary_regime') and hasattr(self.current_regime.primary_regime, 'value')) else (self.current_regime.primary_regime if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None)
        self.current_regime = new_regime_context

        regime_name = new_regime_context.primary_regime.value if (hasattr(new_regime_context, 'primary_regime') and hasattr(new_regime_context.primary_regime, 'value')) else (new_regime_context.primary_regime if hasattr(new_regime_context, 'primary_regime') else str(new_regime_context))
        self.logger.info(f"🔄 Indicators adapting to regime change: {previous_regime} → {regime_name}")

        # Adapt indicator parameters based on regime
        await self.adapt_to_regime(new_regime_context)

    def get_current_regime_context(self) -> Optional[Any]:
        """
        Get current regime context - IRegimeAware interface method

        Returns:
            Current RegimeContext or None if not available
        """
        return self.current_regime

    async def adapt_to_regime(self, regime_context: Any) -> Dict[str, Any]:
        """
        Adapt component behavior to current regime - IRegimeAware interface method

        Adaptation strategy:
        - High volatility → Wider Bollinger Bands, longer periods
        - Low volatility → Tighter bands, shorter periods
        - Trending → Prioritize trend indicators (MACD, ADX)
        - Range-bound → Prioritize oscillators (RSI, Stochastic)

        Args:
            regime_context: Current regime context

        Returns:
            Dictionary with adaptation details and adjustments made
        """
        adaptations = {
            'timestamp': datetime.now().isoformat(),
            'previous_regime': str(self.current_regime.primary_regime.value) if (self.current_regime and hasattr(self.current_regime, 'primary_regime') and hasattr(self.current_regime.primary_regime, 'value')) else (str(self.current_regime.primary_regime) if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None),
            'new_regime': str(regime_context.primary_regime.value) if (hasattr(regime_context, 'primary_regime') and hasattr(regime_context.primary_regime, 'value')) else (str(regime_context.primary_regime) if (hasattr(regime_context, 'primary_regime') and regime_context.primary_regime is not None) else 'unknown'),
            'adjustments': [],
            'success': True
        }

        try:
            regime_name = regime_context.primary_regime.value if (hasattr(regime_context, 'primary_regime') and hasattr(regime_context.primary_regime, 'value') and regime_context.primary_regime is not None) else (regime_context.primary_regime if (hasattr(regime_context, 'primary_regime') and regime_context.primary_regime is not None) else str(regime_context))
            volatility_regime = regime_context.volatility_regime if hasattr(regime_context, 'volatility_regime') else 'normal_volatility'

            # Adapt Bollinger Bands based on volatility
            if volatility_regime == 'high_volatility':
                self.config.bb_std = 2.5  # Wider bands in high vol
                self.config.bb_period = 25  # Longer period
                adaptations['adjustments'].append({'indicator': 'BB', 'std': 2.5, 'period': 25, 'reason': 'high_volatility'})
                self.logger.info(f"📊 BB adapted for high volatility: std=2.5, period=25")
            elif volatility_regime == 'low_volatility':
                self.config.bb_std = 1.5  # Tighter bands in low vol
                self.config.bb_period = 15  # Shorter period
                adaptations['adjustments'].append({'indicator': 'BB', 'std': 1.5, 'period': 15, 'reason': 'low_volatility'})
                self.logger.info(f"📊 BB adapted for low volatility: std=1.5, period=15")
            else:
                self.config.bb_std = 2.0  # Normal bands
                self.config.bb_period = 20  # Normal period
                adaptations['adjustments'].append({'indicator': 'BB', 'std': 2.0, 'period': 20, 'reason': 'normal_volatility'})

            # Adapt RSI period based on regime
            if 'trending' in regime_name:
                self.config.rsi_period = 21  # Longer RSI for trending
                adaptations['adjustments'].append({'indicator': 'RSI', 'period': 21, 'reason': 'trending_regime'})
                self.logger.info(f"📊 RSI adapted for trending: period=21")
            elif 'range' in regime_name:
                self.config.rsi_period = 14  # Standard RSI for range-bound
                adaptations['adjustments'].append({'indicator': 'RSI', 'period': 14, 'reason': 'range_bound_regime'})
                self.logger.info(f"📊 RSI adapted for range-bound: period=14")

            # Clear cache when regime changes (force recalculation with new parameters)
            if self.config.enable_caching and self._indicator_cache:
                cache_size = len(self._indicator_cache)
                self._indicator_cache.clear()
                adaptations['cache_cleared'] = True
                adaptations['cache_entries_cleared'] = cache_size
                self.logger.info(f"🗑️ Indicator cache cleared ({cache_size} entries) for regime adaptation")

            # Store regime context in health metrics
            self.health_metrics['current_regime'] = regime_name
            self.health_metrics['volatility_regime'] = volatility_regime

        except Exception as e:
            self.logger.error(f"❌ Regime adaptation failed: {e}")
            adaptations['success'] = False
            adaptations['error'] = str(e)

        return adaptations

    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is properly configured - IRegimeAware interface method

        Returns:
            True if regime engine is properly configured, False otherwise
        """
        is_valid = hasattr(self, 'regime_engine') and self.regime_engine is not None
        if not is_valid:
            self.logger.warning("⚠️ Regime engine not configured for TechnicalIndicators")
        else:
            self.logger.debug("✅ Regime engine properly configured")
        return is_valid

    def adapt_to_liquidity(self, liquidity_context: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust indicator parameters based on liquidity conditions"""
        adjustments = {
            'score': liquidity_context.get('overall_score'),
            'liquidity_regime': getattr(liquidity_context.get('liquidity_regime'), 'value', liquidity_context.get('liquidity_regime'))
        }
        if not getattr(self.config, 'enable_liquidity_adjustments', True):
            adjustments['mode'] = 'disabled'
            self.current_liquidity = liquidity_context
            return adjustments

        score = liquidity_context.get('overall_score', 70.0)
        if score is None:
            score = 70.0

        # Restore defaults first
        self.config.bb_std = self._base_bb_std
        if hasattr(self.config, 'bollinger_std'):
            self.config.bollinger_std = self._base_bb_std
        self.config.bb_period = self._base_bb_period
        if hasattr(self.config, 'bollinger_period'):
            self.config.bollinger_period = self._base_bb_period
        self.config.volume_sma_period = self._base_volume_sma_period

        if score <= 40:
            new_std = min(self._base_bb_std * 1.2, 3.0)
            new_period = max(self._base_bb_period, int(self._base_bb_period * 1.2))
            self.config.bb_std = new_std
            if hasattr(self.config, 'bollinger_std'):
                self.config.bollinger_std = new_std
            self.config.bb_period = new_period
            if hasattr(self.config, 'bollinger_period'):
                self.config.bollinger_period = new_period
            self.config.volume_sma_period = max(self._base_volume_sma_period, int(self._base_volume_sma_period * 1.5))
            adjustments['mode'] = 'low_liquidity'
        elif score >= 80:
            new_std = max(self._base_bb_std * 0.9, 1.5)
            new_period = max(5, int(self._base_bb_period * 0.9))
            self.config.bb_std = new_std
            if hasattr(self.config, 'bollinger_std'):
                self.config.bollinger_std = new_std
            self.config.bb_period = new_period
            if hasattr(self.config, 'bollinger_period'):
                self.config.bollinger_period = new_period
            self.config.volume_sma_period = max(5, int(self._base_volume_sma_period * 0.8))
            adjustments['mode'] = 'high_liquidity'
        else:
            adjustments['mode'] = 'normal'

        self.current_liquidity = liquidity_context
        adjustments['bb_std'] = self.config.bb_std
        adjustments['bb_period'] = self.config.bb_period
        adjustments['volume_sma_period'] = self.config.volume_sma_period
        return adjustments

    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            self.logger.warning("No orchestrator available for authorization request")
            return False

        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )

    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================

    async def initialize(self) -> bool:
        """Initialize the Enhanced Technical Indicators Engine"""
        try:
            self.logger.info("🔄 Initializing Enhanced Technical Indicators Engine...")

            # Initialize calculation engines
            await self._initialize_calculation_engines()

            # Initialize monitoring
            await self._initialize_monitoring_system()

            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'

            self.logger.info("✅ Enhanced Technical Indicators Engine initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Technical Indicators Engine initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False

    async def start(self) -> bool:
        """Start the Enhanced Technical Indicators Engine"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Technical Indicators Engine: not initialized")
            return False

        try:
            self.logger.info("🚀 Starting Enhanced Technical Indicators Engine...")

            # Start monitoring
            await self._start_monitoring()

            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'

            self.logger.info("✅ Enhanced Technical Indicators Engine started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Technical Indicators Engine start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def stop(self) -> bool:
        """Stop the Enhanced Technical Indicators Engine"""
        try:
            self.logger.info("🛑 Stopping Enhanced Technical Indicators Engine...")

            # Stop monitoring
            await self._stop_monitoring()

            # Clear caches
            if self._indicator_cache:
                self._indicator_cache.clear()

            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'

            self.logger.info("✅ Enhanced Technical Indicators Engine stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Technical Indicators Engine stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time

            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()

            # Check calculation engines health
            engines_healthy = await self._check_engines_health()

            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                engines_healthy and
                self.health_metrics['error_count'] < 10
            )

            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'performance_metrics': self.health_metrics['performance_metrics'],
                'engines_healthy': engines_healthy,
                'cache_size': len(self._indicator_cache) if self._indicator_cache else 0,
                'supported_indicators_count': len(self._supported_indicators),
                'last_health_check': current_time.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'error': str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current component status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'configuration': {
                'enable_caching': self.config.enable_caching,
                'parallel_processing': self.config.parallel_processing,
                'output_format': self.config.output_format,
                'enable_multi_timeframe': self.config.enable_multi_timeframe,
                'enable_macro_indicators': self.config.enable_macro_indicators
            },
            'health_metrics': self.health_metrics
        }

    # Enhanced Internal Methods

    async def _initialize_calculation_engines(self) -> None:
        """Initialize calculation engines"""
        try:
            self.logger.info("📊 Initializing calculation engines...")

            # Initialize indicator calculation engines
            # This is where we would set up any complex calculation frameworks
            # For now, we use the existing vectorized calculations

            self.logger.info("✅ Calculation engines initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize calculation engines: {e}")
            raise

    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")

            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_calculations': 0,
                'successful_calculations': 0,
                'failed_calculations': 0,
                'average_calculation_time': 0.0,
                'cache_hit_rate': 0.0
            }

            self.logger.info("✅ Monitoring system initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise

    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for indicators engine
            self.logger.info("✅ Monitoring systems started")

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise

    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for indicators engine
            self.logger.info("✅ Monitoring systems stopped")

        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise

    async def _check_engines_health(self) -> bool:
        """Check health of calculation engines"""
        try:
            # Basic health check - verify core functionality
            test_data = pd.DataFrame({
                'open': [100.0, 101.0, 102.0],
                'high': [101.0, 102.0, 103.0],
                'low': [99.0, 100.0, 101.0],
                'close': [100.5, 101.5, 102.5],
                'volume': [1000, 1100, 1200]
            })

            # Test basic SMA calculation
            result = test_data['close'].rolling(window=2).mean()
            return len(result) > 0 and not result.isna().all()

        except Exception as e:
            self.logger.warning(f"Engine health check failed: {e}")
            return False

    def calculate_indicators(
        self,
        data: pd.DataFrame,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Calculate indicators following core_engine interface.

        Args:
            data: DataFrame with OHLCV data
            regime_context: Optional regime context for dynamic parameters
            liquidity_context: Optional liquidity context for dynamic parameters

        Returns:
            DataFrame with calculated indicators
        """
        return self.calculate_all_indicators(
            data,
            regime_context=regime_context,
            liquidity_context=liquidity_context
        )

    def _process_single_symbol(
        self,
        symbol_df: pd.DataFrame,
        symbol: str,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Process indicators for a single symbol with optional context awareness.
        """
        symbol_df = symbol_df.sort_values('timestamp').copy()

        # Add symbol column back
        symbol_df['symbol'] = symbol

        if len(symbol_df) < 2:
            return symbol_df

        # Apply parameters from context locally if provided (Statelessness Enhancement #2)
        # Note: We don't mutate self.config here to remain thread-safe for parallel calls.
        bb_std = self._base_bb_std
        bb_period = self._base_bb_period
        vol_sma_period = self._base_volume_sma_period

        if liquidity_context:
            score = liquidity_context.get('liquidity_score', 50)
            if score <= 40:
                bb_std = min(self._base_bb_std * 1.2, 3.0)
                bb_period = max(self._base_bb_period, int(self._base_bb_period * 1.2))
                vol_sma_period = max(self._base_volume_sma_period, int(self._base_volume_sma_period * 1.5))
            elif score >= 80:
                bb_std = max(self._base_bb_std * 0.9, 1.5)
                bb_period = max(5, int(self._base_bb_period * 0.9))
                vol_sma_period = max(5, int(self._base_volume_sma_period * 0.8))

        # Calculate all indicators using local parameters
        symbol_df = self._calculate_moving_averages(symbol_df)
        symbol_df = self._calculate_momentum_indicators(symbol_df)
        # Pass local parameters to volatility if needed, but for now we'll stick to 
        # the structure where we might need to modify _calculate_volatility_indicators
        symbol_df = self._calculate_volatility_indicators(symbol_df, bb_std=bb_std, bb_period=bb_period)
        symbol_df = self._calculate_volume_indicators(symbol_df, vol_sma_period=vol_sma_period)
        symbol_df = self._calculate_price_patterns(symbol_df)

        return symbol_df

    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Calculate all configured indicators for the given DataFrame

        Args:
            df: DataFrame with OHLCV data
            regime_context: Optional regime context
            liquidity_context: Optional liquidity context

        Returns:
            DataFrame with all indicators added
        """
        if df.empty:
            return df

        n_symbols = df['symbol'].nunique()

        # Use groupby().apply() for vectorized processing
        result = df.groupby('symbol', group_keys=False).apply(
            lambda x: self._process_single_symbol(
                x, x.name,
                regime_context=regime_context,
                liquidity_context=liquidity_context
            ),
            include_groups=False
        )

        # Reset index to ensure clean output
        if not result.empty:
            result = result.reset_index(drop=True)

        return result

    def _calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate moving averages (SMA and EMA)"""
        # Simple Moving Averages
        for period in self.config.sma_periods:
            if len(df) >= period:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()

        # Exponential Moving Averages
        for period in self.config.ema_periods:
            if len(df) >= period:
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()

        return df

    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum indicators (RSI, MACD, Stochastic, ADX)"""
        # RSI (Relative Strength Index)
        if len(df) >= self.config.rsi_period:
            df['rsi'] = self._calculate_rsi(df['close'], self.config.rsi_period)

        # MACD (Moving Average Convergence Divergence)
        if len(df) >= self.config.macd_slow:
            df['macd'], df['macd_signal'], df['macd_histogram'] = self._calculate_macd(
                df['close'],
                self.config.macd_fast,
                self.config.macd_slow,
                self.config.macd_signal
            )

        # Stochastic Oscillator
        if len(df) >= self.config.stoch_k_period:
            df['stoch_k'], df['stoch_d'] = self._calculate_stochastic(
                df['high'], df['low'], df['close'],
                self.config.stoch_k_period, self.config.stoch_d_period
            )

        # ADX (Average Directional Index) - NEWLY ADDED
        adx_period = getattr(self.config, 'adx_period', 14)
        if len(df) >= adx_period * 2:  # Need enough data for smoothing
            df['adx'], df['plus_di'], df['minus_di'] = self._calculate_adx(
                df['high'], df['low'], df['close'], adx_period
            )

        # Rate of Change
        for period in [1, 5, 10]:
            if len(df) > period:
                df[f'roc_{period}'] = df['close'].pct_change(period, fill_method=None) * 100

        return df

    def _calculate_volatility_indicators(
        self,
        df: pd.DataFrame,
        bb_std: Optional[float] = None,
        bb_period: Optional[int] = None
    ) -> pd.DataFrame:
        """Calculate volatility indicators (Bollinger Bands, ATR)"""
        # Bollinger Bands (with optional context overrides for statelessness)
        period = bb_period or self.config.bb_period
        std = bb_std or self.config.bb_std

        if len(df) >= period:
            sma = df['close'].rolling(window=period).mean()
            rolling_std = df['close'].rolling(window=period).std()

            df['bb_upper'] = sma + (rolling_std * std)
            df['bb_middle'] = sma
            df['bb_lower'] = sma - (rolling_std * std)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Average True Range (ATR)
        if len(df) >= self.config.atr_period:
            df['atr'] = self._calculate_atr(df['high'], df['low'], df['close'], self.config.atr_period)

        # Historical Volatility
        for period_v in [10, 20, 30]:
            if len(df) > period_v:
                returns = df['close'].pct_change(fill_method=None)
                df[f'volatility_{period_v}'] = returns.rolling(window=period_v).std() * np.sqrt(252)  # Annualized

        return df

    def _calculate_volume_indicators(
        self,
        df: pd.DataFrame,
        vol_sma_period: Optional[int] = None
    ) -> pd.DataFrame:
        """Calculate volume-based indicators"""
        if 'volume' not in df.columns:
            return df

        # Volume Moving Average (with optional context overrides)
        period = vol_sma_period or self.config.volume_sma_period

        if len(df) >= period:
            df['volume_sma'] = df['volume'].rolling(window=period).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Volume-Price Trend (VPT)
        if len(df) > 1:
            price_change = df['close'].pct_change(fill_method=None)
            df['vpt'] = (price_change * df['volume']).cumsum()

        # On-Balance Volume (OBV)
        if len(df) > 1:
            price_change = df['close'].diff()
            volume_direction = np.where(price_change > 0, df['volume'],
                                       np.where(price_change < 0, -df['volume'], 0))
            df['obv'] = volume_direction.cumsum()

        # VPIN (Volume-Synchronized Probability of Informed Trading)
        # Easley-Lopez de Prado-O'Hara (2012) adapted for bar-level estimation.
        #
        # Core idea: classify each bar's volume into buy-initiated vs sell-initiated
        # using the bulk volume classification (BVC) approach, then measure the
        # imbalance over rolling volume buckets.
        #
        # VPIN = Σ|V_buy - V_sell| / (n × V_bucket)
        #
        # High VPIN indicates high probability of informed trading (toxic flow).
        df = self._calculate_vpin(df)

        return df

    def _calculate_vpin(
        self,
        df: pd.DataFrame,
        n_buckets: int = 50,
        sample_length: int = 50,
    ) -> pd.DataFrame:
        """
        Calculate VPIN (Volume-Synchronized Probability of Informed Trading).

        Uses Bulk Volume Classification (BVC) to classify volume into
        buy-initiated and sell-initiated components, then computes order
        flow imbalance over rolling windows.

        Args:
            df: DataFrame with OHLCV data
            n_buckets: Number of volume buckets for VPIN calculation
            sample_length: Rolling window length for VPIN estimation

        Returns:
            DataFrame with vpin and vpin_percentile columns added
        """
        if 'volume' not in df.columns or 'close' not in df.columns or len(df) < sample_length:
            df['vpin'] = 0.5
            df['vpin_percentile'] = 0.5
            df['buy_volume_pct'] = 0.5
            return df

        try:
            close = df['close'].values.astype(float)
            volume = df['volume'].values.astype(float)
            n = len(df)

            # ------------------------------------------------------------------
            # Step 1: Bulk Volume Classification (BVC)
            #
            # For each bar, classify volume into buy-initiated and sell-initiated
            # using the price change relative to the bar's range and a CDF
            # approximation.  Z = ΔP / σ,  V_buy = V × Φ(Z)
            # ------------------------------------------------------------------
            returns = np.zeros(n)
            returns[1:] = (close[1:] - close[:-1]) / np.maximum(close[:-1], 1e-10)

            # Rolling volatility for BVC normalisation (20-bar)
            vol_window = min(20, max(5, n // 10))
            rolling_std = np.full(n, np.nan)
            for i in range(vol_window, n):
                rolling_std[i] = np.std(returns[i - vol_window + 1: i + 1])

            # Back-fill initial NaNs with first valid value
            first_valid = np.nanmean(rolling_std[vol_window: min(vol_window + 10, n)])
            if np.isnan(first_valid) or first_valid <= 0:
                first_valid = 0.01
            rolling_std = np.where(np.isnan(rolling_std), first_valid, rolling_std)
            rolling_std = np.maximum(rolling_std, 1e-8)

            # Z-score of return normalised by rolling vol
            z_scores = returns / rolling_std

            # CDF approximation (fast sigmoid proxy for Φ(z)):
            #   Φ(z) ≈ 1 / (1 + exp(-1.7 * z))
            # This is the standard BVC approach.
            buy_pct = 1.0 / (1.0 + np.exp(-1.7 * np.clip(z_scores, -5.0, 5.0)))

            v_buy = volume * buy_pct
            v_sell = volume * (1.0 - buy_pct)

            # ------------------------------------------------------------------
            # Step 2: Rolling VPIN
            #
            # VPIN = mean(|V_buy_i - V_sell_i|) / mean(V_i)  over window
            # Normalised to [0, 1]; 0.5 = random, >0.5 = informed flow
            # ------------------------------------------------------------------
            order_imbalance = np.abs(v_buy - v_sell)

            vpin_raw = np.full(n, np.nan)
            for i in range(sample_length - 1, n):
                window_imb = order_imbalance[i - sample_length + 1: i + 1]
                window_vol = volume[i - sample_length + 1: i + 1]
                total_vol = np.sum(window_vol)
                if total_vol > 0:
                    vpin_raw[i] = np.sum(window_imb) / total_vol
                else:
                    vpin_raw[i] = 0.5

            # Back-fill NaNs
            vpin_raw = np.where(np.isnan(vpin_raw), 0.5, vpin_raw)

            # Clip to [0, 1]
            vpin_raw = np.clip(vpin_raw, 0.0, 1.0)

            df['vpin'] = vpin_raw

            # ------------------------------------------------------------------
            # Step 3: Percentile rank for regime-invariant interpretation
            # ------------------------------------------------------------------
            rank_window = min(252, n)
            vpin_series = pd.Series(vpin_raw, index=df.index)
            vpin_pct = vpin_series.rolling(rank_window, min_periods=sample_length).rank(pct=True)
            df['vpin_percentile'] = vpin_pct.fillna(0.5).values

            # Buy volume fraction (useful for downstream flow analysis)
            df['buy_volume_pct'] = buy_pct

        except Exception as e:
            # Degrade gracefully
            df['vpin'] = 0.5
            df['vpin_percentile'] = 0.5
            df['buy_volume_pct'] = 0.5

        return df

    def _calculate_price_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate price pattern indicators"""
        # Support and Resistance levels (simple version)
        if len(df) >= 20:
            # Local highs and lows in a rolling window
            window = 10
            # Causal: use trailing window only (avoid look-ahead from centered windows)
            df['local_high'] = df['high'].rolling(window=window, center=False).max()
            df['local_low'] = df['low'].rolling(window=window, center=False).min()

            # Distance from local extremes
            df['dist_from_high'] = (df['local_high'] - df['close']) / df['close']
            df['dist_from_low'] = (df['close'] - df['local_low']) / df['close']

        # Price position within daily range
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['price_position'] = df['price_position'].fillna(0.5)  # If high == low

        # Gap detection
        if len(df) > 1:
            prev_close = df['close'].shift(1)
            df['gap_up'] = (df['open'] > prev_close) & ((df['open'] - prev_close) / prev_close > 0.02)
            df['gap_down'] = (df['open'] < prev_close) & ((prev_close - df['open']) / prev_close > 0.02)

        return df

    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index - uses TA-Lib when available"""
        from .talib_indicators import calculate_rsi
        return calculate_rsi(close, period)

    def _calculate_macd(self, close: pd.Series, fast: int, slow: int, signal: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD - uses TA-Lib when available"""
        from .talib_indicators import calculate_macd
        return calculate_macd(close, fast, slow, signal)

    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series,
                            k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator - uses TA-Lib when available"""
        from .talib_indicators import calculate_stochastic
        return calculate_stochastic(high, low, close, k_period, d_period)

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """Calculate Average True Range - uses TA-Lib when available"""
        from .talib_indicators import calculate_atr
        return calculate_atr(high, low, close, period)

    def _calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate ADX - uses TA-Lib when available"""
        from .talib_indicators import calculate_adx
        return calculate_adx(high, low, close, period)

    def get_indicator_summary(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Get summary of indicators for a specific symbol"""
        symbol_df = df[df['symbol'] == symbol]
        if symbol_df.empty:
            return {}

        latest = symbol_df.iloc[-1]
        summary = {
            'symbol': symbol,
            'timestamp': latest['timestamp'],
            'price': latest['close'],
            'indicators': {}
        }

        # RSI
        if 'rsi' in latest:
            rsi_val = latest['rsi']
            if not pd.isna(rsi_val):
                summary['indicators']['rsi'] = {
                    'value': rsi_val,
                    'signal': 'overbought' if rsi_val > 70 else 'oversold' if rsi_val < 30 else 'neutral'
                }

        # MACD
        if 'macd' in latest and 'macd_signal' in latest:
            macd_val = latest['macd']
            macd_signal_val = latest['macd_signal']
            if not pd.isna(macd_val) and not pd.isna(macd_signal_val):
                summary['indicators']['macd'] = {
                    'macd': macd_val,
                    'signal': macd_signal_val,
                    'crossover': 'bullish' if macd_val > macd_signal_val else 'bearish'
                }

        # Bollinger Bands
        if 'bb_position' in latest:
            bb_pos = latest['bb_position']
            if not pd.isna(bb_pos):
                summary['indicators']['bollinger'] = {
                    'position': bb_pos,
                    'signal': 'overbought' if bb_pos > 0.8 else 'oversold' if bb_pos < 0.2 else 'neutral'
                }

        # Moving Average Trends
        ma_signals = []
        for period in self.config.sma_periods:
            ma_col = f'sma_{period}'
            if ma_col in latest:
                ma_val = latest[ma_col]
                if not pd.isna(ma_val):
                    ma_signals.append('bullish' if latest['close'] > ma_val else 'bearish')

        if ma_signals:
            bullish_count = ma_signals.count('bullish')
            summary['indicators']['moving_average_trend'] = {
                'bullish_signals': bullish_count,
                'total_signals': len(ma_signals),
                'overall': 'bullish' if bullish_count > len(ma_signals) / 2 else 'bearish'
            }

        return summary

    # ========================================================================================
    # CORE ENGINE INTERFACE COMPLIANCE METHODS
    # ========================================================================================

    def get_indicator_summary(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Core Engine compatible interface for getting indicator summary

        This method provides the interface expected by our integration tests
        and other core_engine components.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol

        Returns:
            Dictionary with key indicators and signals
        """
        try:
            if df.empty:
                return {}

            # Calculate indicators using our existing method
            indicators_df = self.calculate_all_indicators(df)

            if indicators_df.empty:
                return {}

            # Get the latest values for the specific symbol
            symbol_data = indicators_df[indicators_df['symbol'] == symbol] if 'symbol' in indicators_df.columns else indicators_df

            if symbol_data.empty:
                return {}

            latest = symbol_data.iloc[-1]

            # Build summary with core_engine expected format
            summary = {
                'symbol': symbol,
                'timestamp': latest.get('timestamp', pd.Timestamp.now()),

                # Key indicators (matching our integration test expectations)
                'rsi': latest.get('rsi', np.nan),
                'macd': latest.get('macd', np.nan),
                'macd_signal': latest.get('macd_signal', np.nan),
                'macd_histogram': latest.get('macd_histogram', np.nan),

                # Moving averages
                'sma_20': latest.get('sma_20', np.nan),
                'sma_50': latest.get('sma_50', np.nan),
                'ema_9': latest.get('ema_9', np.nan),
                'ema_21': latest.get('ema_21', np.nan),

                # Volatility indicators
                'bb_upper': latest.get('bb_upper', np.nan),
                'bb_lower': latest.get('bb_lower', np.nan),
                'bb_position': latest.get('bb_position', np.nan),
                'atr': latest.get('atr', np.nan),

                # Volume indicators
                'volume_ratio': latest.get('volume_ratio', np.nan),

                # Signals (following core_engine patterns)
                'signals': self._extract_simple_signals(latest)
            }

            return summary

        except Exception as e:
            self.logger.error(f"Error generating indicator summary for {symbol}: {e}")
            return {}

    def _extract_simple_signals(self, latest_data: pd.Series) -> Dict[str, str]:
        """Extract simple trading signals from indicators"""
        signals = {}

        try:
            # RSI signals
            rsi = latest_data.get('rsi')
            if not pd.isna(rsi):
                if rsi > 70:
                    signals['rsi'] = 'overbought'
                elif rsi < 30:
                    signals['rsi'] = 'oversold'
                else:
                    signals['rsi'] = 'neutral'

            # MACD signals
            macd = latest_data.get('macd')
            macd_signal = latest_data.get('macd_signal')
            if not pd.isna(macd) and not pd.isna(macd_signal):
                signals['macd'] = 'bullish' if macd > macd_signal else 'bearish'

            # Bollinger Bands signals
            bb_position = latest_data.get('bb_position')
            if not pd.isna(bb_position):
                if bb_position > 0.8:
                    signals['bollinger'] = 'overbought'
                elif bb_position < 0.2:
                    signals['bollinger'] = 'oversold'
                else:
                    signals['bollinger'] = 'neutral'

        except Exception as e:
            self.logger.warning(f"Error extracting signals: {e}")

        return signals

    # ========================================================================================
    # TIER 2 ENHANCEMENT #4: MULTI-TIMEFRAME & MACRO INDICATORS
    # ========================================================================================

    def calculate_multi_timeframe_indicators(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, MultiTimeframeIndicatorResult]:
        """
        Calculate indicators across multiple timeframes

        Args:
            data_dict: Dictionary with timeframe as key and DataFrame as value

        Returns:
            Dictionary of MultiTimeframeIndicatorResult by symbol
        """
        if not self.config.enable_multi_timeframe:
            return {}

        try:
            results = {}

            # Group data by symbol
            symbol_data = self._group_data_by_symbol(data_dict)

            for symbol, timeframe_data in symbol_data.items():
                try:
                    # Calculate indicators for each timeframe
                    timeframe_indicators = {}

                    for timeframe, df in timeframe_data.items():
                        if timeframe in self.config.timeframes and not df.empty:
                            indicators = self._calculate_timeframe_indicators(df, timeframe)
                            timeframe_indicators[timeframe] = indicators

                    if timeframe_indicators:
                        # Calculate consensus and alignment
                        consensus_signals = self._calculate_timeframe_consensus(timeframe_indicators)
                        alignment_score = self._calculate_timeframe_alignment(timeframe_indicators)
                        dominant_tf = self._determine_dominant_timeframe(timeframe_indicators)

                        results[symbol] = MultiTimeframeIndicatorResult(
                            symbol=symbol,
                            timestamp=pd.Timestamp.now(),
                            timeframe_indicators=timeframe_indicators,
                            consensus_signals=consensus_signals,
                            timeframe_alignment=alignment_score,
                            dominant_timeframe=dominant_tf,
                            metadata={'calculation_timestamp': pd.Timestamp.now()}
                        )

                except Exception as e:
                    self.logger.warning(f"Error calculating multi-timeframe indicators for {symbol}: {e}")

            return results

        except Exception as e:
            self.logger.error(f"Error in multi-timeframe indicator calculation: {e}")
            return {}

    def calculate_macro_regime_indicators(self, macro_data: Dict[str, pd.DataFrame]) -> MacroRegimeIndicators:
        """
        Calculate macro regime indicators from cross-asset data

        Args:
            macro_data: Dictionary with macro symbol as key and DataFrame as value

        Returns:
            MacroRegimeIndicators object
        """
        if not self.config.enable_macro_indicators:
            return MacroRegimeIndicators(timestamp=pd.Timestamp.now())

        try:
            # VIX regime analysis
            vix_regime = self._analyze_vix_regime(macro_data.get('VIX'))

            # Yield curve analysis
            yield_curve_regime = self._analyze_yield_curve_regime(
                macro_data.get('TNX'), macro_data.get('TLT')
            )

            # Dollar strength analysis
            dollar_strength = self._analyze_dollar_strength(macro_data.get('DXY'))

            # Commodity trend analysis
            commodity_trend = self._analyze_commodity_trend(
                macro_data.get('GLD'), macro_data.get('USO')
            )

            # Credit spread regime
            credit_spread_regime = self._analyze_credit_spreads(
                macro_data.get('HYG'), macro_data.get('LQD')
            )

            # Cross-asset correlation
            cross_asset_corr = self._calculate_cross_asset_correlation(macro_data)

            # Overall macro regime score
            macro_score = self._calculate_macro_regime_score(
                vix_regime, yield_curve_regime, dollar_strength,
                commodity_trend, credit_spread_regime
            )

            # Confidence in macro assessment
            regime_confidence = self._calculate_macro_confidence(macro_data)

            return MacroRegimeIndicators(
                timestamp=pd.Timestamp.now(),
                vix_regime=vix_regime,
                yield_curve_regime=yield_curve_regime,
                dollar_strength=dollar_strength,
                commodity_trend=commodity_trend,
                credit_spread_regime=credit_spread_regime,
                cross_asset_correlation=cross_asset_corr,
                macro_regime_score=macro_score,
                regime_confidence=regime_confidence
            )

        except Exception as e:
            self.logger.error(f"Error calculating macro regime indicators: {e}")
            return MacroRegimeIndicators(timestamp=pd.Timestamp.now())

    def _group_data_by_symbol(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Group multi-timeframe data by symbol"""
        symbol_data = {}

        for key, df in data_dict.items():
            if '_' in key:  # Format: SYMBOL_TIMEFRAME
                symbol, timeframe = key.rsplit('_', 1)
                if symbol not in symbol_data:
                    symbol_data[symbol] = {}
                symbol_data[symbol][timeframe] = df
            else:
                # Assume single symbol, multiple timeframes
                if 'symbol' in df.columns:
                    for symbol in df['symbol'].unique():
                        symbol_df = df[df['symbol'] == symbol].copy()
                        if symbol not in symbol_data:
                            symbol_data[symbol] = {}
                        symbol_data[symbol]['1D'] = symbol_df  # Default timeframe

        return symbol_data

    def _calculate_timeframe_indicators(self, df: pd.DataFrame, timeframe: str) -> Dict[str, float]:
        """Calculate indicators for specific timeframe"""
        try:
            # Get timeframe-specific periods
            rsi_period = self.config.timeframe_rsi_periods.get(timeframe, 14)
            ma_periods = self.config.timeframe_ma_periods.get(timeframe, [20, 50])

            indicators = {}

            if len(df) >= max(rsi_period, max(ma_periods)):
                # RSI
                rsi = self._calculate_rsi(df['close'], rsi_period)
                if not rsi.empty:
                    indicators[f'rsi_{timeframe}'] = rsi.iloc[-1]

                # Moving averages
                for period in ma_periods:
                    if len(df) >= period:
                        sma = df['close'].rolling(period).mean()
                        if not sma.empty:
                            indicators[f'sma_{period}_{timeframe}'] = sma.iloc[-1]

                # MACD
                macd_line, macd_signal, macd_hist = self._calculate_macd(
                    df['close'], self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
                )
                if not macd_line.empty:
                    indicators[f'macd_{timeframe}'] = macd_line.iloc[-1]
                    indicators[f'macd_signal_{timeframe}'] = macd_signal.iloc[-1]
                    indicators[f'macd_hist_{timeframe}'] = macd_hist.iloc[-1]

                # Bollinger Bands
                if len(df) >= self.config.bb_period:
                    sma = df['close'].rolling(window=self.config.bb_period).mean()
                    std = df['close'].rolling(window=self.config.bb_period).std()

                    bb_upper = sma + (std * self.config.bb_std)
                    bb_middle = sma
                    bb_lower = sma - (std * self.config.bb_std)

                    if not bb_middle.empty:
                        current_price = df['close'].iloc[-1]
                        bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
                        indicators[f'bb_position_{timeframe}'] = bb_position

                # ATR (volatility)
                if len(df) >= self.config.atr_period and 'high' in df.columns and 'low' in df.columns:
                    atr = self._calculate_atr(df['high'], df['low'], df['close'], self.config.atr_period)
                    if not atr.empty:
                        indicators[f'atr_{timeframe}'] = atr.iloc[-1]

            return indicators

        except Exception as e:
            self.logger.warning(f"Error calculating {timeframe} indicators: {e}")
            return {}

    def _calculate_timeframe_consensus(self, timeframe_indicators: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Calculate consensus signals across timeframes"""
        consensus = {}

        try:
            # RSI consensus
            rsi_values = []
            for tf, indicators in timeframe_indicators.items():
                rsi_key = f'rsi_{tf}'
                if rsi_key in indicators:
                    rsi_values.append(indicators[rsi_key])

            if rsi_values:
                avg_rsi = np.mean(rsi_values)
                if avg_rsi > 70:
                    consensus['rsi_consensus'] = 'overbought'
                elif avg_rsi < 30:
                    consensus['rsi_consensus'] = 'oversold'
                else:
                    consensus['rsi_consensus'] = 'neutral'

            # MACD consensus
            macd_signals = []
            for tf, indicators in timeframe_indicators.items():
                macd_key = f'macd_hist_{tf}'
                if macd_key in indicators:
                    macd_signals.append('bullish' if indicators[macd_key] > 0 else 'bearish')

            if macd_signals:
                bullish_count = macd_signals.count('bullish')
                if bullish_count > len(macd_signals) / 2:
                    consensus['macd_consensus'] = 'bullish'
                elif bullish_count < len(macd_signals) / 2:
                    consensus['macd_consensus'] = 'bearish'
                else:
                    consensus['macd_consensus'] = 'neutral'

            return consensus

        except Exception as e:
            self.logger.warning(f"Error calculating timeframe consensus: {e}")
            return {}

    def _calculate_timeframe_alignment(self, timeframe_indicators: Dict[str, Dict[str, float]]) -> float:
        """Calculate alignment score across timeframes (0-1)"""
        try:
            if len(timeframe_indicators) < 2:
                return 1.0

            # Compare RSI alignment
            rsi_values = []
            for tf, indicators in timeframe_indicators.items():
                rsi_key = f'rsi_{tf}'
                if rsi_key in indicators:
                    rsi_values.append(indicators[rsi_key])

            if len(rsi_values) >= 2:
                rsi_std = np.std(rsi_values)
                rsi_alignment = max(0, 1 - (rsi_std / 50))  # Normalize by max possible std
                return rsi_alignment

            raise ValueError("Insufficient RSI data for timeframe alignment calculation")

        except Exception as e:
            self.logger.error(f"Error calculating timeframe alignment: {e}")
            raise

    def _determine_dominant_timeframe(self, timeframe_indicators: Dict[str, Dict[str, float]]) -> str:
        """Determine the most influential timeframe"""
        # Hierarchy: 1D > 1W > 1H > 5min
        hierarchy = ["1D", "1W", "1H", "5min"]

        for tf in hierarchy:
            if tf in timeframe_indicators and timeframe_indicators[tf]:
                return tf

        # Return first available timeframe
        return list(timeframe_indicators.keys())[0] if timeframe_indicators else "1D"

    def _analyze_vix_regime(self, vix_data: Optional[pd.DataFrame]) -> str:
        """Analyze VIX regime"""
        if vix_data is None or vix_data.empty:
            return "normal"

        try:
            current_vix = vix_data['close'].iloc[-1]

            if current_vix > 30:
                return "extreme"
            elif current_vix > 20:
                return "elevated"
            elif current_vix < 12:
                return "low"
            else:
                return "normal"

        except Exception as e:
            self.logger.warning(f"Error analyzing VIX regime: {e}")
            return "normal"

    def _analyze_yield_curve_regime(self, tnx_data: Optional[pd.DataFrame],
                                  tlt_data: Optional[pd.DataFrame]) -> str:
        """Analyze yield curve regime"""
        if tnx_data is None or tnx_data.empty:
            return "normal"

        try:
            # Simplified yield curve analysis using 10-year yield trend
            recent_yields = tnx_data['close'].tail(20)
            yield_trend = (recent_yields.iloc[-1] - recent_yields.iloc[0]) / recent_yields.iloc[0]

            if yield_trend > 0.1:
                return "steep"
            elif yield_trend < -0.1:
                return "flat"
            else:
                return "normal"

        except Exception as e:
            self.logger.warning(f"Error analyzing yield curve regime: {e}")
            return "normal"

    def _analyze_dollar_strength(self, dxy_data: Optional[pd.DataFrame]) -> float:
        """Analyze dollar strength (-1 to 1)"""
        if dxy_data is None or dxy_data.empty:
            return 0.0

        try:
            # Calculate dollar strength based on recent trend
            recent_dxy = dxy_data['close'].tail(20)
            dxy_change = (recent_dxy.iloc[-1] - recent_dxy.iloc[0]) / recent_dxy.iloc[0]

            # Normalize to -1 to 1 range
            return np.clip(dxy_change * 10, -1, 1)

        except Exception as e:
            self.logger.warning(f"Error analyzing dollar strength: {e}")
            return 0.0

    def _analyze_commodity_trend(self, gld_data: Optional[pd.DataFrame],
                               uso_data: Optional[pd.DataFrame]) -> str:
        """Analyze commodity trend"""
        try:
            trends = []

            # Gold trend
            if gld_data is not None and not gld_data.empty:
                gld_change = (gld_data['close'].iloc[-1] - gld_data['close'].iloc[-20]) / gld_data['close'].iloc[-20]
                trends.append(gld_change)

            # Oil trend
            if uso_data is not None and not uso_data.empty:
                uso_change = (uso_data['close'].iloc[-1] - uso_data['close'].iloc[-20]) / uso_data['close'].iloc[-20]
                trends.append(uso_change)

            if trends:
                avg_trend = np.mean(trends)
                if avg_trend > 0.05:
                    return "bullish"
                elif avg_trend < -0.05:
                    return "bearish"

            return "neutral"

        except Exception as e:
            self.logger.warning(f"Error analyzing commodity trend: {e}")
            return "neutral"

    def _analyze_credit_spreads(self, hyg_data: Optional[pd.DataFrame],
                              lqd_data: Optional[pd.DataFrame]) -> str:
        """Analyze credit spread regime"""
        try:
            if hyg_data is None or lqd_data is None or hyg_data.empty or lqd_data.empty:
                return "normal"

            # Calculate HYG/LQD ratio as credit spread proxy
            hyg_return = (hyg_data['close'].iloc[-1] - hyg_data['close'].iloc[-20]) / hyg_data['close'].iloc[-20]
            lqd_return = (lqd_data['close'].iloc[-1] - lqd_data['close'].iloc[-20]) / lqd_data['close'].iloc[-20]

            spread_proxy = lqd_return - hyg_return  # Higher = wider spreads

            if spread_proxy > 0.02:
                return "wide"
            elif spread_proxy > 0.05:
                return "stressed"
            elif spread_proxy < -0.02:
                return "tight"
            else:
                return "normal"

        except Exception as e:
            self.logger.warning(f"Error analyzing credit spreads: {e}")
            return "normal"

    def _calculate_cross_asset_correlation(self, macro_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate cross-asset correlation strength"""
        try:
            returns_data = {}

            for symbol, df in macro_data.items():
                if df is not None and not df.empty and len(df) >= 20:
                    returns = df['close'].pct_change(fill_method=None).dropna()
                    if len(returns) >= 10:
                        returns_data[symbol] = returns.tail(20)

            if len(returns_data) >= 2:
                # Calculate average correlation
                correlations = []
                symbols = list(returns_data.keys())

                for i in range(len(symbols)):
                    for j in range(i + 1, len(symbols)):
                        corr = returns_data[symbols[i]].corr(returns_data[symbols[j]])
                        if not np.isnan(corr):
                            correlations.append(abs(corr))

                if correlations:
                    return np.mean(correlations)

            return 0.0

        except Exception as e:
            self.logger.warning(f"Error calculating cross-asset correlation: {e}")
            return 0.0

    def _calculate_macro_regime_score(self, vix_regime: str, yield_curve_regime: str,
                                    dollar_strength: float, commodity_trend: str,
                                    credit_spread_regime: str) -> float:
        """Calculate overall macro regime score (-1 to 1)"""
        try:
            score = 0.0

            # VIX contribution
            vix_scores = {"low": 0.3, "normal": 0.0, "elevated": -0.3, "extreme": -0.7}
            score += vix_scores.get(vix_regime, 0.0)

            # Yield curve contribution
            yield_scores = {"steep": 0.2, "normal": 0.0, "flat": -0.2, "inverted": -0.5}
            score += yield_scores.get(yield_curve_regime, 0.0)

            # Dollar strength (moderate strength is positive)
            score += dollar_strength * 0.3

            # Commodity trend
            commodity_scores = {"bullish": 0.2, "neutral": 0.0, "bearish": -0.2}
            score += commodity_scores.get(commodity_trend, 0.0)

            # Credit spreads
            credit_scores = {"tight": 0.3, "normal": 0.0, "wide": -0.3, "stressed": -0.7}
            score += credit_scores.get(credit_spread_regime, 0.0)

            return np.clip(score, -1, 1)

        except Exception as e:
            self.logger.warning(f"Error calculating macro regime score: {e}")
            return 0.0

    def _calculate_macro_confidence(self, macro_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate confidence in macro regime assessment"""
        try:
            data_quality_scores = []

            for symbol, df in macro_data.items():
                if df is not None and not df.empty:
                    # Score based on data availability and quality
                    if len(df) >= 20:
                        data_quality_scores.append(1.0)
                    elif len(df) >= 10:
                        data_quality_scores.append(0.7)
                    else:
                        data_quality_scores.append(0.3)
                else:
                    data_quality_scores.append(0.0)

            if data_quality_scores:
                return np.mean(data_quality_scores)

            return 0.0

        except Exception as e:
            self.logger.warning(f"Error calculating macro confidence: {e}")
            return 0.0

    # ========================================
    # STANDARDIZED DATA CONSUMPTION METHODS
    # ========================================

    def process_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for processing indicators data"""
        # This component produces indicators, so this is a pass-through
        return indicators

    def use_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for using indicators data (alias)"""
        return self.process_indicators(indicators)

    def analyze_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for analyzing indicators data (alias)"""
        return self.process_indicators(indicators)

    def process_market_data(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for processing market data (consumption interface)"""
        # This component consumes market data to produce indicators
        return market_data

    def analyze_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for analyzing data (consumption interface)"""
        return self.process_market_data(data)

    def consume_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for consuming data (consumption interface)"""
        return self.process_market_data(data)

# ========================================================================================
# BACKWARD COMPATIBILITY AND ALIASES
# ========================================================================================

# Alias for backward compatibility with existing code
TechnicalIndicators = EnhancedTechnicalIndicators
IndicatorConfig = EnhancedIndicatorConfig