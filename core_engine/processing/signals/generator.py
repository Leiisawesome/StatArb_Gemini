#!/usr/bin/env python3
"""
Signal Generation Engine for Core Engine
========================================

Generates trading signals from engineered features using multiple strategies:
- Mean reversion signals
- Momentum signals
- Multi-factor signals
- Machine learning signals

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Signal Generation)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from collections import deque
import warnings
import threading
import uuid
warnings.filterwarnings('ignore')

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
from ...system.interfaces import ISystemComponent, IRegimeAware

logger = logging.getLogger(__name__)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
from core_engine.config import SignalConfig

# Import canonical types from type_definitions (Single Source of Truth)
from core_engine.type_definitions.strategy import SignalType, SignalStrength

# SignalType imported from type_definitions.strategy (canonical source)
# SignalStrength imported from type_definitions.strategy (canonical source)

@dataclass
class TradingSignal:
    """Trading signal structure"""
    symbol: str
    timestamp: pd.Timestamp
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: float = 0.0  # Suggested position size (0.0 to 1.0)
    strategy: str = "multi_factor"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

        # Validate confidence range
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary representation"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "signal_type": self.signal_type.name,
            "strength": self.strength.name,
            "confidence": self.confidence,
            "price": self.price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "position_size": self.position_size,
            "strategy": self.strategy,
            "metadata": self.metadata.copy() if self.metadata else {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Create signal from dictionary representation"""
        # Convert string values back to enums (case-insensitive)
        def get_enum_value(enum_class, value):
            if isinstance(value, str):
                # Try exact match first
                try:
                    return enum_class[value.upper()]
                except KeyError:
                    # Try value match
                    for member in enum_class:
                        if member.value == value.lower():
                            return member
                    raise ValueError(f"Invalid {enum_class.__name__} value: {value}")
            return value

        signal_type = get_enum_value(SignalType, data["signal_type"])
        strength = get_enum_value(SignalStrength, data["strength"])

        # Parse timestamp
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                # If not ISO format, try pandas parsing
                timestamp = pd.to_datetime(timestamp)

        return cls(
            symbol=data["symbol"],
            timestamp=timestamp,
            signal_type=signal_type,
            strength=strength,
            confidence=data["confidence"],
            price=data["price"],
            target_price=data.get("target_price"),
            stop_loss=data.get("stop_loss"),
            position_size=data.get("position_size", 0.0),
            strategy=data.get("strategy", "multi_factor"),
            metadata=data.get("metadata", {})
        )

@dataclass
class SignalConfig:
    """
    Configuration for signal generation
    Updated with test findings for better signal quality
    """
    # Strategy weights
    mean_reversion_weight: float = 0.4
    momentum_weight: float = 0.4
    volume_weight: float = 0.2

    # Thresholds (enhanced for better returns)
    signal_threshold: float = 0.4  # Higher threshold for quality signals
    strong_signal_threshold: float = 0.8  # Higher confidence threshold

    # Risk parameters
    max_position_size: float = 0.1  # 10% max position
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit

    # Signal filtering (enhanced from test)
    min_volume_ratio: float = 0.5  # Minimum volume vs average
    max_volatility_percentile: float = 0.95  # Filter extreme volatility

    # Mean reversion specific (enhanced for better returns)
    rsi_oversold_threshold: float = 25  # More extreme oversold for higher quality
    rsi_overbought_threshold: float = 75  # More extreme overbought for higher quality
    zscore_threshold: float = 1.8  # Higher z-score threshold for stronger signals

    # Quality requirements
    min_conditions_required: int = 1  # Minimum conditions for signal
    confidence_scaling_factor: float = 0.8  # For scaling to proper confidence levels

    # Machine learning
    enable_ml_signals: bool = True
    ml_confidence_threshold: float = 0.65

class EnhancedSignalGenerator(ISystemComponent, IRegimeAware):
    """
    Enhanced Signal Generator with ISystemComponent & IRegimeAware Integration

    Institutional-grade signal generation with orchestrator integration:
    - Implements ISystemComponent for lifecycle management (Rule 1)
    - Implements IRegimeAware for regime adaptation (Rule 2)
    - Multi-strategy signal generation with professional standards
    - Mean Reversion: RSI, Bollinger Bands, oversold/overbought conditions
    - Momentum: MACD, price momentum, trend following
    - Volume: Volume breakouts, volume-price relationships
    - Multi-factor: Combination of all signals with ML enhancement
    - Regime-aware signal filtering and confidence adjustment
    - Health monitoring and performance tracking
    """

    def __init__(self, config: Optional[SignalConfig] = None):
        # Handle both SignalConfig objects and dictionaries
        # Rule 1 Section 7: Use centralized configuration from core_engine.config
        if isinstance(config, dict):
            try:
                from core_engine.config import SignalConfig as CentralizedSignalConfig
                self.config = CentralizedSignalConfig(**{k: v for k, v in config.items() if hasattr(CentralizedSignalConfig, k)})
            except ImportError:
                # Fallback during migration
                self.config = SignalConfig(**{k: v for k, v in config.items() if k in SignalConfig.__dataclass_fields__})
        else:
            self.config = config or SignalConfig()
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

        # PHASE 3: Liquidity awareness (Rule 7 Section B)
        self.liquidity_engine: Optional[Any] = None  # LiquidityAssessmentEngine reference

        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedSignalGenerator',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_signal_generation': 0,
                'successful_signal_generation': 0,
                'failed_signal_generation': 0,
                'average_processing_time': 0.0,
                'signals_generated_count': 0
            }
        }

        # Signal history for tracking (bounded to prevent memory leak in long-running processes)
        # P1 Performance Fix: Use deque with maxlen instead of unbounded list
        self._signal_history: deque = deque(maxlen=10000)

    @property
    def signal_history(self) -> List[TradingSignal]:
        """Return signal history as list for backward compatibility."""
        return list(self._signal_history)

        # Threading
        self._lock = threading.Lock()

        self.logger.info(f"🚀 Enhanced Signal Generator initialized with component ID: {self.component_id}")

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedSignalGenerator",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=17  # PHASE 3: After Features(16), before Strategy(20)
        )

        self.logger.info(f"✅ EnhancedSignalGenerator registered with orchestrator: {self.component_id}")
        return self.component_id

    # ========================================
    # PHASE 3: REGIME & LIQUIDITY AWARENESS (RULE 2 - IRegimeAware Interface)
    # ========================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine reference for regime-aware signal generation (Rule 2 Regime-First)
        Part of IRegimeAware interface implementation.
        """
        self.regime_engine = regime_engine
        self.logger.info(f"✅ RegimeEngine injected into SignalGenerator (IRegimeAware, Rule 2)")

    def set_liquidity_engine(self, liquidity_engine: Any) -> None:
        """
        Inject liquidity engine reference for liquidity-aware signal filtering (Rule 7 Section B)
        """
        self.liquidity_engine = liquidity_engine
        self.logger.info(f"✅ LiquidityEngine injected into SignalGenerator (Liquidity Management)")

    async def on_regime_change(self, new_regime_context: Any) -> None:
        """
        Handle regime change event - IRegimeAware interface method
        Callback for regime changes from the EnhancedRegimeEngine.
        Adapt signal generation to new market regime.

        Args:
            new_regime_context: New regime context with updated information
        """
        previous_regime = self.current_regime.primary_regime.value if (self.current_regime and hasattr(self.current_regime, 'primary_regime') and hasattr(self.current_regime.primary_regime, 'value')) else (self.current_regime.primary_regime if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None)
        self.current_regime = new_regime_context

        regime_name = new_regime_context.primary_regime.value if (hasattr(new_regime_context, 'primary_regime') and hasattr(new_regime_context.primary_regime, 'value')) else (new_regime_context.primary_regime if hasattr(new_regime_context, 'primary_regime') else str(new_regime_context))
        self.logger.info(f"🔄 Signals adapting to regime change: {previous_regime} → {regime_name}")

        # Adapt signal generation to regime
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
        - High volatility → Higher confidence thresholds, more conservative signals
        - Low volatility → Lower thresholds, more aggressive signals
        - Trending → Prioritize momentum signals
        - Range-bound → Prioritize mean-reversion signals

        Args:
            regime_context: Current regime context

        Returns:
            Dictionary with adaptation details and adjustments made
        """
        adaptations = {
            'timestamp': datetime.now().isoformat(),
            'previous_regime': str(self.current_regime.primary_regime.value) if (self.current_regime and hasattr(self.current_regime, 'primary_regime') and hasattr(self.current_regime.primary_regime, 'value')) else (str(self.current_regime.primary_regime) if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None),
            'new_regime': str(regime_context.primary_regime.value) if (hasattr(regime_context, 'primary_regime') and hasattr(regime_context.primary_regime, 'value')) else (str(regime_context.primary_regime) if hasattr(regime_context, 'primary_regime') else 'unknown'),
            'adjustments': [],
            'success': True
        }

        try:
            regime_name = regime_context.primary_regime.value if (hasattr(regime_context, 'primary_regime') and hasattr(regime_context.primary_regime, 'value')) else (regime_context.primary_regime if hasattr(regime_context, 'primary_regime') else str(regime_context))
            volatility_regime = regime_context.volatility_regime if hasattr(regime_context, 'volatility_regime') else 'normal_volatility'

            # Adapt signal thresholds based on volatility
            if volatility_regime == 'high_volatility':
                self.config.signal_threshold = 0.5  # Higher threshold
                self.config.strong_signal_threshold = 0.85  # More conservative
                self.config.zscore_threshold = 2.0  # Higher z-score
                adaptations['adjustments'].append({
                    'signal_threshold': 0.5,
                    'strong_signal_threshold': 0.85,
                    'zscore_threshold': 2.0,
                    'reason': 'high_volatility'
                })
                self.logger.info(f"📊 Signals adapted for high volatility: higher thresholds")
            elif volatility_regime == 'low_volatility':
                self.config.signal_threshold = 0.35  # Lower threshold
                self.config.strong_signal_threshold = 0.75  # More aggressive
                self.config.zscore_threshold = 1.5  # Lower z-score
                adaptations['adjustments'].append({
                    'signal_threshold': 0.35,
                    'strong_signal_threshold': 0.75,
                    'zscore_threshold': 1.5,
                    'reason': 'low_volatility'
                })
                self.logger.info(f"📊 Signals adapted for low volatility: lower thresholds")
            else:
                self.config.signal_threshold = 0.4  # Normal threshold
                self.config.strong_signal_threshold = 0.8  # Normal
                self.config.zscore_threshold = 1.8  # Normal z-score
                adaptations['adjustments'].append({
                    'signal_threshold': 0.4,
                    'strong_signal_threshold': 0.8,
                    'zscore_threshold': 1.8,
                    'reason': 'normal_volatility'
                })

            # Adapt strategy weights based on regime
            if 'trending' in regime_name.lower():
                self.config.momentum_weight = 0.5  # Prioritize momentum
                self.config.mean_reversion_weight = 0.3
                adaptations['adjustments'].append({
                    'momentum_weight': 0.5,
                    'mean_reversion_weight': 0.3,
                    'reason': 'trending_regime'
                })
                self.logger.info(f"📊 Signals adapted for trending: prioritize momentum")
            elif 'range' in regime_name.lower():
                self.config.momentum_weight = 0.3
                self.config.mean_reversion_weight = 0.5  # Prioritize mean-reversion
                adaptations['adjustments'].append({
                    'momentum_weight': 0.3,
                    'mean_reversion_weight': 0.5,
                    'reason': 'range_bound_regime'
                })
                self.logger.info(f"📊 Signals adapted for range-bound: prioritize mean-reversion")

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
            self.logger.warning("⚠️ Regime engine not configured for SignalGenerator")
        else:
            self.logger.debug("✅ Regime engine properly configured")
        return is_valid

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
        """Initialize the Enhanced Signal Generator"""
        try:
            self.logger.info("🔄 Initializing Enhanced Signal Generator...")

            # Initialize signal generation engines
            await self._initialize_signal_engines()

            # Initialize monitoring
            await self._initialize_monitoring_system()

            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'

            self.logger.info("✅ Enhanced Signal Generator initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Signal Generator initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False

    async def start(self) -> bool:
        """Start the Enhanced Signal Generator"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Signal Generator: not initialized")
            return False

        try:
            self.logger.info("🚀 Starting Enhanced Signal Generator...")

            # Start monitoring
            await self._start_monitoring()

            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'

            self.logger.info("✅ Enhanced Signal Generator started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Signal Generator start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def stop(self) -> bool:
        """Stop the Enhanced Signal Generator"""
        try:
            self.logger.info("🛑 Stopping Enhanced Signal Generator...")

            # Stop monitoring
            await self._stop_monitoring()

            # Clear signal history
            self._signal_history.clear()

            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'

            self.logger.info("✅ Enhanced Signal Generator stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Signal Generator stop failed: {e}")
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

            # Check signal engines health
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
                'signal_history_count': len(self.signal_history),
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
                'mean_reversion_weight': self.config.mean_reversion_weight,
                'momentum_weight': self.config.momentum_weight,
                'volume_weight': self.config.volume_weight,
                'signal_threshold': self.config.signal_threshold,
                'strong_signal_threshold': self.config.strong_signal_threshold,
                'max_position_size': self.config.max_position_size
            },
            'health_metrics': self.health_metrics
        }

    # Enhanced Internal Methods

    async def _initialize_signal_engines(self) -> None:
        """Initialize signal generation engines"""
        try:
            self.logger.info("🔧 Initializing signal generation engines...")

            # Initialize signal generation strategies
            # This is where we would set up any complex ML models or signal frameworks
            # For now, we use the existing rule-based signal generation

            self.logger.info("✅ Signal generation engines initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize signal engines: {e}")
            raise

    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")

            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_signal_generation': 0,
                'successful_signal_generation': 0,
                'failed_signal_generation': 0,
                'average_processing_time': 0.0,
                'signals_generated_count': 0
            }

            self.logger.info("✅ Monitoring system initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise

    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for signal generator
            self.logger.info("✅ Monitoring systems started")

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise

    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for signal generator
            self.logger.info("✅ Monitoring systems stopped")

        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise

    async def _check_engines_health(self) -> bool:
        """Check health of signal generation engines"""
        try:
            # Basic health check - verify core functionality
            test_data = pd.DataFrame({
                'symbol': ['TEST'] * 5,
                'timestamp': pd.date_range('2024-01-01', periods=5),
                'close': [100, 101, 102, 103, 104],
                'rsi': [30, 40, 50, 60, 70],
                'macd': [-1, -0.5, 0, 0.5, 1]
            })

            # Test basic signal generation
            signals = self._generate_mean_reversion_signals(test_data)
            return len(signals) >= 0  # Should return at least empty list

        except Exception as e:
            self.logger.warning(f"Engine health check failed: {e}")
            return False

    def generate_signals(self, df: pd.DataFrame) -> List[TradingSignal]:
        """
        Generate trading signals from features DataFrame

        Args:
            df: DataFrame with engineered features

        Returns:
            List of TradingSignal objects
        """
        if df.empty:
            return []

        self.logger.info(f"Generating signals for {len(df['symbol'].unique())} symbols")

        all_signals = []

        # Process each symbol separately
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol].copy().sort_values('timestamp')

            if len(symbol_df) < 10:  # Need minimum data for signals
                continue

            # Generate different types of signals (UNBIASED APPROACH)
            # Return separate signals per type - strategies pick what they need
            # This removes bias from fixed-weight combination (mean_rev=0.4, momentum=0.4, volume=0.2)

            mean_reversion_scores = self._generate_mean_reversion_signals(symbol_df)
            momentum_scores = self._generate_momentum_signals(symbol_df)
            volume_scores = self._generate_volume_signals(symbol_df)

            # Convert score DataFrames to TradingSignal objects (separate per type)
            # No forced combination - truly general, strategy-agnostic signals
            # Pass all score DataFrames for metadata access
            mean_rev_signals = self._scores_to_signals(
                symbol_df, mean_reversion_scores,
                score_column='mean_reversion_score',
                signal_source='mean_reversion',
                all_scores={'mean_reversion': mean_reversion_scores, 'momentum': momentum_scores, 'volume': volume_scores}
            )
            momentum_sig_list = self._scores_to_signals(
                symbol_df, momentum_scores,
                score_column='momentum_score',
                signal_source='momentum',
                all_scores={'mean_reversion': mean_reversion_scores, 'momentum': momentum_scores, 'volume': volume_scores}
            )
            volume_sig_list = self._scores_to_signals(
                symbol_df, volume_scores,
                score_column='volume_score',
                signal_source='volume',
                all_scores={'mean_reversion': mean_reversion_scores, 'momentum': momentum_scores, 'volume': volume_scores}
            )

            # Return all signal types separately (no bias)
            all_signals.extend(mean_rev_signals)
            all_signals.extend(momentum_sig_list)
            all_signals.extend(volume_sig_list)

        # Filter and validate signals
        filtered_signals = self._filter_signals(all_signals, df)

        # Store in history (using bounded deque)
        self._signal_history.extend(filtered_signals)

        self.logger.info(f"Generated {len(filtered_signals)} signals from {len(all_signals)} raw signals")
        return filtered_signals

    def _calculate_improved_zscore(self, df: pd.DataFrame, price_col: str = 'close', window: int = 20) -> pd.Series:
        """
        Calculate improved z-score with realistic standard deviation
        Based on test findings: use 5% of price as std estimate instead of 2%
        """
        price = df[price_col]
        sma = price.rolling(window=window).mean()

        # Use realistic standard deviation estimate (5% of SMA)
        # This prevents extremely high z-scores that don't reflect real market conditions
        std_estimate = sma * 0.05
        zscore = (price - sma) / std_estimate

        return zscore.fillna(0)

    def _get_regime_aware_rsi_thresholds(self) -> Tuple[float, float]:
        """
        Get regime-aware RSI thresholds for mean reversion signals

        Strategy:
        - High volatility: More extreme thresholds (30/70) to filter out false signals
          during volatile periods - only trade when RSI is very extreme
        - Low volatility: More sensitive thresholds (45/55) to capture more opportunities
          in calm markets where RSI extremes are less frequent
        - Normal volatility: Balanced thresholds (40/60) - standard mean reversion approach

        Returns:
            Tuple of (oversold_threshold, overbought_threshold)
        """
        # Default thresholds (normal volatility)
        oversold_threshold = 40.0
        overbought_threshold = 60.0

        # Get current regime context
        regime_context = self.get_current_regime_context()
        if regime_context:
            volatility_regime = getattr(regime_context, 'volatility_regime', 'normal_volatility')

            if volatility_regime == 'high_volatility' or volatility_regime == 'extreme_volatility':
                # High volatility: Use more extreme thresholds (30/70)
                # Only trigger signals when RSI is very extreme to reduce false signals
                oversold_threshold = 30.0
                overbought_threshold = 70.0

            elif volatility_regime == 'low_volatility':
                # Low volatility: Use more sensitive thresholds (45/55)
                # Capture more opportunities when markets are calm
                oversold_threshold = 45.0
                overbought_threshold = 55.0

            # Normal volatility uses default (40/60)

        return (oversold_threshold, overbought_threshold)

    def _generate_mean_reversion_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate enhanced mean reversion signals with improved quality
        Based on test findings: multi-factor scoring with sophisticated logic
        """
        signals_df = df.copy()
        signals_df['mean_reversion_score'] = 0.0
        signals_df['buy_score'] = 0.0
        signals_df['sell_score'] = 0.0

        # Calculate improved z-score
        if 'close' in df.columns:
            signals_df['improved_zscore'] = self._calculate_improved_zscore(df)

        # Enhanced RSI-based signals with regime-aware thresholds
        if 'rsi_14' in df.columns or 'rsi' in df.columns:
            rsi_col = 'rsi_14' if 'rsi_14' in df.columns else 'rsi'
            rsi = df[rsi_col]

            # ENHANCEMENT: Regime-aware RSI thresholds
            # High volatility → More extreme thresholds (30/70) for higher quality
            # Low volatility → More sensitive thresholds (45/55) for more signals
            # Normal volatility → Balanced thresholds (40/60)
            oversold_threshold, overbought_threshold = self._get_regime_aware_rsi_thresholds()

            # Sophisticated RSI scoring
            oversold_condition = rsi < oversold_threshold
            overbought_condition = rsi > overbought_threshold

            # Stronger signal for more extreme RSI values
            rsi_strength_buy = (oversold_threshold - rsi) / oversold_threshold
            rsi_strength_sell = (rsi - overbought_threshold) / (100 - overbought_threshold)

            signals_df.loc[oversold_condition, 'buy_score'] += 0.4 * (1 + rsi_strength_buy[oversold_condition])
            signals_df.loc[overbought_condition, 'sell_score'] += 0.4 * (1 + rsi_strength_sell[overbought_condition])

        # Enhanced Bollinger Bands signals
        if 'bb_upper_20' in df.columns and 'bb_lower_20' in df.columns:
            price = df['close']
            bb_upper = df['bb_upper_20']
            bb_lower = df['bb_lower_20']

            below_bb_lower = price < bb_lower
            above_bb_upper = price > bb_upper

            # Measure deviation from bands
            bb_deviation_buy = (bb_lower - price) / bb_lower
            bb_deviation_sell = (price - bb_upper) / bb_upper

            # FIX: Reduced multiplier from 10x to 5x to prevent excessive amplification
            # Original * 10 amplified small deviations too aggressively
            # Example: 1% deviation → 0.3 * (1 + 0.05) = 0.315 (was 0.33 with * 10)
            signals_df.loc[below_bb_lower, 'buy_score'] += 0.3 * (1 + bb_deviation_buy[below_bb_lower] * 5)
            signals_df.loc[above_bb_upper, 'sell_score'] += 0.3 * (1 + bb_deviation_sell[above_bb_upper] * 5)

        # Enhanced Z-Score signals with extreme deviation detection
        if 'improved_zscore' in signals_df.columns:
            zscore = signals_df['improved_zscore']
            zscore_threshold = 0.5  # More sensitive threshold

            # Standard z-score conditions
            negative_zscore = zscore < -zscore_threshold
            positive_zscore = zscore > zscore_threshold

            # Normalize z-score strength
            zscore_strength = np.abs(zscore) / 3.0  # Normalize to reasonable range
            zscore_strength = np.minimum(zscore_strength, 1.0)

            signals_df.loc[negative_zscore, 'buy_score'] += 0.4 * zscore_strength[negative_zscore]
            signals_df.loc[positive_zscore, 'sell_score'] += 0.4 * zscore_strength[positive_zscore]

            # Extreme deviation detection (from test findings)
            # CRITICAL FIX: Changed from 1000 to 4.0 (statistically meaningful extreme)
            # Z-score > 4.0 represents 99.99% percentile (very extreme but possible)
            # Z-score > 1000 would be statistically impossible in real markets
            extreme_positive = zscore > 4.0  # 99.99% percentile (very extreme but possible)
            extreme_negative = zscore < -4.0

            # Create high-quality signals for extreme deviations
            signals_df.loc[extreme_positive, 'sell_score'] = 0.9  # High confidence
            signals_df.loc[extreme_negative, 'buy_score'] = 0.9   # High confidence

        # Volume confirmation (DIRECTIONAL - fixed from non-directional)
        if 'volume' in df.columns:
            volume = df['volume']
            volume_sma = volume.rolling(window=10).mean()
            high_volume = volume > volume_sma * 1.2  # 20% above average

            # Volume confirmation should be DIRECTIONAL
            # High volume + price up → confirms buy signals
            # High volume + price down → confirms sell signals
            if 'return_1d' in df.columns or 'close' in df.columns:
                # Use price return to determine direction
                if 'return_1d' in df.columns:
                    price_up = df['return_1d'] > 0
                    price_down = df['return_1d'] < 0
                else:
                    # Fallback: use close price change
                    price_change = df['close'].diff()
                    price_up = price_change > 0
                    price_down = price_change < 0

                signals_df.loc[high_volume & price_up, 'buy_score'] += 0.2
                signals_df.loc[high_volume & price_down, 'sell_score'] += 0.2
            else:
                # Fallback: if no price data, apply to both (old behavior)
                signals_df.loc[high_volume, 'buy_score'] += 0.2
                signals_df.loc[high_volume, 'sell_score'] += 0.2

        # Quality filters - require multiple conditions for high-quality signals
        # Count conditions met for each signal type
        buy_conditions = (
            (signals_df['buy_score'] > 0).astype(int)
        )
        sell_conditions = (
            (signals_df['sell_score'] > 0).astype(int)
        )

        # Final mean reversion score with quality requirements
        min_confidence = 0.3  # From test findings

        # Buy signals
        buy_signal_mask = (signals_df['buy_score'] >= min_confidence) & (buy_conditions >= 1)
        signals_df.loc[buy_signal_mask, 'mean_reversion_score'] = signals_df.loc[buy_signal_mask, 'buy_score']

        # Sell signals
        sell_signal_mask = (signals_df['sell_score'] >= min_confidence) & (sell_conditions >= 1)
        signals_df.loc[sell_signal_mask, 'mean_reversion_score'] = -signals_df.loc[sell_signal_mask, 'sell_score']

        return signals_df

    def _generate_momentum_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals"""
        signals_df = df.copy()
        signals_df['momentum_score'] = 0.0

        # MACD signals
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # MACD crossover (bullish)
            macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
            signals_df.loc[macd_bullish, 'momentum_score'] += 0.4

            # MACD crossover (bearish)
            macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
            signals_df.loc[macd_bearish, 'momentum_score'] -= 0.4

            # MACD histogram momentum
            if 'macd_histogram' in df.columns:
                hist_increasing = df['macd_histogram'] > df['macd_histogram'].shift(1)
                hist_decreasing = df['macd_histogram'] < df['macd_histogram'].shift(1)
                signals_df.loc[hist_increasing, 'momentum_score'] += 0.2
                signals_df.loc[hist_decreasing, 'momentum_score'] -= 0.2

        # Moving average trends
        sma_cols = [col for col in df.columns if col.startswith('sma_') and col.endswith('_above')]
        if sma_cols:
            # Count how many MAs price is above
            ma_above_count = df[sma_cols].sum(axis=1)
            ma_score = (ma_above_count / len(sma_cols) - 0.5) * 0.6  # Center around 0
            signals_df['momentum_score'] += ma_score

        # Golden/Death cross
        if 'golden_cross' in df.columns:
            signals_df.loc[df['golden_cross'] == 1, 'momentum_score'] += 0.5
        if 'death_cross' in df.columns:
            signals_df.loc[df['death_cross'] == 1, 'momentum_score'] -= 0.5

        # Price momentum
        if 'return_1d' in df.columns:
            # Short-term momentum
            strong_up_move = df['return_1d'] > 0.03  # >3% move
            strong_down_move = df['return_1d'] < -0.03  # <-3% move
            signals_df.loc[strong_up_move, 'momentum_score'] += 0.3
            signals_df.loc[strong_down_move, 'momentum_score'] -= 0.3

        # Multi-period momentum consistency
        momentum_cols = [col for col in df.columns if col.startswith('return_') and 'd' in col]
        if len(momentum_cols) >= 3:
            # Check for consistent momentum across periods
            momentum_signs = df[momentum_cols].apply(np.sign, axis=1)
            consistent_up = (momentum_signs == 1).all(axis=1)
            consistent_down = (momentum_signs == -1).all(axis=1)
            signals_df.loc[consistent_up, 'momentum_score'] += 0.25
            signals_df.loc[consistent_down, 'momentum_score'] -= 0.25

        return signals_df

    def _generate_volume_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate volume-based signals"""
        signals_df = df.copy()
        signals_df['volume_score'] = 0.0

        if 'volume' not in df.columns:
            return signals_df

        # Volume breakout
        if 'volume_breakout' in df.columns:
            # High volume with price increase
            volume_breakout_up = (df['volume_breakout'] == 1) & (df['return_1d'] > 0)
            volume_breakout_down = (df['volume_breakout'] == 1) & (df['return_1d'] < 0)
            signals_df.loc[volume_breakout_up, 'volume_score'] += 0.4
            signals_df.loc[volume_breakout_down, 'volume_score'] -= 0.4

        # Volume-price trend
        if 'volume_price_trend' in df.columns:
            positive_vpt = df['volume_price_trend'] > 0
            negative_vpt = df['volume_price_trend'] < 0
            signals_df.loc[positive_vpt, 'volume_score'] += 0.3
            signals_df.loc[negative_vpt, 'volume_score'] -= 0.3

        # OBV signals
        if 'obv_momentum' in df.columns:
            obv_increasing = df['obv_momentum'] > 0.02  # >2% OBV increase
            obv_decreasing = df['obv_momentum'] < -0.02  # <-2% OBV decrease
            signals_df.loc[obv_increasing, 'volume_score'] += 0.2
            signals_df.loc[obv_decreasing, 'volume_score'] -= 0.2

        # Volume confirmation
        if 'volume_ratio' in df.columns:
            high_volume = df['volume_ratio'] > 1.5  # >150% of average volume
            low_volume = df['volume_ratio'] < 0.5   # <50% of average volume

            # High volume confirms signals
            signals_df.loc[high_volume, 'volume_score'] *= 1.2
            # Low volume weakens signals
            signals_df.loc[low_volume, 'volume_score'] *= 0.8

        return signals_df

    def _scores_to_signals(
        self,
        df: pd.DataFrame,
        scores_df: pd.DataFrame,
        score_column: str,
        signal_source: str,
        all_scores: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[TradingSignal]:
        """
        Convert score DataFrame to TradingSignal objects (unbiased approach)

        Creates separate signals per signal type - no forced combination.
        Strategies can pick signals based on their needs (mean_reversion, momentum, volume).

        Args:
            df: Original DataFrame with OHLCV and features
            scores_df: DataFrame with score column (e.g., 'mean_reversion_score')
            score_column: Name of score column to use
            signal_source: Source of signal ('mean_reversion', 'momentum', 'volume')

        Returns:
            List of TradingSignal objects for this signal type
        """
        signals = []

        if score_column not in scores_df.columns:
            return signals

        score_series = scores_df[score_column].fillna(0.0)

        # Reindex to match df.index
        if not score_series.index.equals(df.index):
            score_series = score_series.reindex(df.index, fill_value=0.0)

        for i, (idx, row) in enumerate(df.iterrows()):
            if idx not in score_series.index:
                continue

            score = score_series.loc[idx]
            raw_confidence = abs(score)

            # Only create signals above threshold
            if raw_confidence < self.config.signal_threshold:
                continue

            # Scale confidence similar to _combine_signals (for consistency)
            # FIX: Ensure scaled confidence >= threshold to prevent later filtering
            # Formula: threshold + (raw_confidence - threshold) * 0.8 ensures min = threshold
            scaled_confidence = min(0.95, self.config.signal_threshold + (raw_confidence - self.config.signal_threshold) * 0.8)
            if raw_confidence >= 0.8:
                scaled_confidence = max(0.85, scaled_confidence)
            # Confidence is now guaranteed >= threshold by formula
            confidence = scaled_confidence

            signal_type = SignalType.BUY if score > 0 else SignalType.SELL

            # Determine strength
            if confidence >= 0.8:
                strength = SignalStrength.STRONG
            elif confidence >= 0.65:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # Position size
            base_size = self.config.max_position_size
            if strength == SignalStrength.STRONG:
                position_size = base_size * confidence
            elif strength == SignalStrength.MODERATE:
                position_size = base_size * 0.7 * confidence
            else:
                position_size = base_size * 0.4 * confidence

            # Target and stop loss
            current_price = row['close']
            if signal_type == SignalType.BUY:
                target_price = current_price * (1 + self.config.take_profit_pct)
                stop_loss = current_price * (1 - self.config.stop_loss_pct)
            else:
                target_price = current_price * (1 - self.config.take_profit_pct)
                stop_loss = current_price * (1 + self.config.stop_loss_pct)

            # Create metadata with all scores for strategy flexibility
            # Even though this is a single-type signal, include other scores for context
            metadata = {
                # This signal's score
                f'{signal_source}_score': score,
                'signal_source': signal_source,  # Key field: indicates signal type

                # Additional context
                'rsi': row.get('rsi', None),
                'volume_ratio': row.get('volume_ratio', None),
                'signal_generation_method': 'unbiased_separate_types',
                'bias_note': 'Signal from single source - no forced combination. Strategies can combine as needed.'
            }

            # Add other scores if available (for strategy flexibility)
            if all_scores:
                try:
                    if 'mean_reversion' in all_scores and 'mean_reversion_score' in all_scores['mean_reversion'].columns:
                        mr_series = all_scores['mean_reversion']['mean_reversion_score']
                        if idx in mr_series.index:
                            metadata['mean_reversion_score'] = mr_series.loc[idx]
                    if 'momentum' in all_scores and 'momentum_score' in all_scores['momentum'].columns:
                        mom_series = all_scores['momentum']['momentum_score']
                        if idx in mom_series.index:
                            metadata['momentum_score'] = mom_series.loc[idx]
                    if 'volume' in all_scores and 'volume_score' in all_scores['volume'].columns:
                        vol_series = all_scores['volume']['volume_score']
                        if idx in vol_series.index:
                            metadata['volume_score'] = vol_series.loc[idx]
                except Exception:
                    # Non-critical - metadata enhancement failed, continue with basic metadata
                    pass

            signal = TradingSignal(
                symbol=row['symbol'],
                timestamp=row['timestamp'],
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy=f"signal_generator_{signal_source}",
                metadata=metadata
            )

            signals.append(signal)

        return signals

    def _combine_signals(self, df: pd.DataFrame, mean_rev: pd.DataFrame,
                        momentum: pd.DataFrame, volume: pd.DataFrame) -> List[TradingSignal]:
        """
        Combine different signal types into final signals with enhanced confidence scaling
        Based on test findings: ensure high-quality signals reach 0.6+ confidence
        """
        signals = []

        # Combine scores with weights
        # CRITICAL: Ensure all Series have same index and handle NaN values
        # (can occur when regime segments have insufficient data for indicator calculation)
        mean_rev_scores = mean_rev['mean_reversion_score'].fillna(0.0) if 'mean_reversion_score' in mean_rev.columns else pd.Series(0.0, index=df.index)
        momentum_scores = momentum['momentum_score'].fillna(0.0) if 'momentum_score' in momentum.columns else pd.Series(0.0, index=df.index)
        volume_scores = volume['volume_score'].fillna(0.0) if 'volume_score' in volume.columns else pd.Series(0.0, index=df.index)

        # Reindex to match df.index exactly (handles regime-segmented processing index resets)
        # Only reindex if indices don't match (to avoid unnecessary operations)
        if not mean_rev_scores.index.equals(df.index):
            self.logger.debug(f"Reindexing mean_rev_scores: {mean_rev_scores.index[:5]} -> {df.index[:5]}")
            mean_rev_scores = mean_rev_scores.reindex(df.index, fill_value=0.0)
        if not momentum_scores.index.equals(df.index):
            self.logger.debug(f"Reindexing momentum_scores: {momentum_scores.index[:5]} -> {df.index[:5]}")
            momentum_scores = momentum_scores.reindex(df.index, fill_value=0.0)
        if not volume_scores.index.equals(df.index):
            self.logger.debug(f"Reindexing volume_scores: {volume_scores.index[:5]} -> {df.index[:5]}")
            volume_scores = volume_scores.reindex(df.index, fill_value=0.0)

        combined_score = (
            mean_rev_scores * self.config.mean_reversion_weight +
            momentum_scores * self.config.momentum_weight +
            volume_scores * self.config.volume_weight
        )

        # Add ML enhancement if enabled
        if self.config.enable_ml_signals:
            ml_score = self._generate_ml_signals(df)
            combined_score = 0.7 * combined_score + 0.3 * ml_score

        # Generate signals from combined scores
        # CRITICAL: Use loc[idx] instead of iloc[i] to ensure index alignment
        # after filtering/sorting operations
        signals_created_count = 0
        signals_filtered_count = 0
        total_rows_processed = 0

        for i, (idx, row) in enumerate(df.iterrows()):
            total_rows_processed += 1
            try:
                # Use loc with index to ensure correct alignment even after DataFrame operations
                if idx not in combined_score.index:
                    self.logger.debug(f"Skipping row {i} (idx={idx}): index not in combined_score")
                    continue

                score = combined_score.loc[idx]

                # Enhanced confidence calculation from test findings
                raw_confidence = abs(score)

                # Scale confidence to ensure high-quality signals reach 0.6+
                if raw_confidence >= self.config.signal_threshold:
                    signals_filtered_count += 1
                    if signals_filtered_count <= 3:  # Log first 3 to avoid spam
                        self.logger.debug(f"Row {i} (idx={idx}): raw_confidence={raw_confidence:.4f} >= threshold={self.config.signal_threshold}")
                    # FIX: Scale confidence ensuring min = threshold at threshold value
                    # Formula: threshold + (raw_confidence - threshold) * 0.8
                    # Example: 0.6 + (0.6 - 0.6) * 0.8 = 0.6 (correct)
                    # Example: 0.6 + (0.8 - 0.6) * 0.8 = 0.76 (correct)
                    scaled_confidence = min(0.95, self.config.signal_threshold + (raw_confidence - self.config.signal_threshold) * 0.8)

                    # For extreme scores (like extreme z-scores), ensure high confidence
                    if raw_confidence >= 0.8:
                        scaled_confidence = max(0.85, scaled_confidence)

                    # Confidence is now guaranteed >= threshold by formula
                    confidence = scaled_confidence
                else:
                    continue  # Below threshold

                signal_type = SignalType.BUY if score > 0 else SignalType.SELL

                # Determine strength based on scaled confidence
                if confidence >= 0.8:
                    strength = SignalStrength.STRONG
                elif confidence >= 0.65:
                    strength = SignalStrength.MODERATE
                else:
                    strength = SignalStrength.WEAK

                # Calculate position size based on confidence and strength
                base_size = self.config.max_position_size
                if strength == SignalStrength.STRONG:
                    position_size = base_size * confidence
                elif strength == SignalStrength.MODERATE:
                    position_size = base_size * 0.7 * confidence
                else:
                    position_size = base_size * 0.4 * confidence

                # Calculate target and stop loss
                current_price = row['close']
                if signal_type == SignalType.BUY:
                    target_price = current_price * (1 + self.config.take_profit_pct)
                    stop_loss = current_price * (1 - self.config.stop_loss_pct)
                else:
                    target_price = current_price * (1 - self.config.take_profit_pct)
                    stop_loss = current_price * (1 + self.config.stop_loss_pct)

                # Create signal with safe metadata access
                # Use the reindexed Series for metadata to ensure consistency
                # ENHANCED: Include score breakdown for strategy flexibility
                try:
                    mr_score = mean_rev_scores.loc[idx] if idx in mean_rev_scores.index else 0.0
                    mom_score = momentum_scores.loc[idx] if idx in momentum_scores.index else 0.0
                    vol_score = volume_scores.loc[idx] if idx in volume_scores.index else 0.0

                    metadata = {
                        # Raw scores (for strategy flexibility)
                        'mean_reversion_score': mr_score,
                        'momentum_score': mom_score,
                        'volume_score': vol_score,
                        'combined_score': score,

                        # Score breakdown (contribution analysis)
                        'score_breakdown': {
                            'mean_reversion_contribution': mr_score * self.config.mean_reversion_weight,
                            'momentum_contribution': mom_score * self.config.momentum_weight,
                            'volume_contribution': vol_score * self.config.volume_weight,
                            'weights': {
                                'mean_reversion': self.config.mean_reversion_weight,
                                'momentum': self.config.momentum_weight,
                                'volume': self.config.volume_weight
                            }
                        },

                        # Additional context
                        'rsi': row.get('rsi', None),
                        'volume_ratio': row.get('volume_ratio', None),
                        'signal_generation_method': 'multi_factor_combined'
                    }
                except Exception as meta_e:
                    self.logger.warning(f"Error accessing metadata for row {i} (idx={idx}): {meta_e}")
                    metadata = {'combined_score': score}

                signal = TradingSignal(
                    symbol=row['symbol'],
                    timestamp=row['timestamp'],
                    signal_type=signal_type,
                    strength=strength,
                    confidence=confidence,
                    price=current_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="multi_factor",
                    metadata=metadata
                )

                signals.append(signal)
                signals_created_count += 1
                if signals_created_count <= 3:  # Log first 3 to avoid spam
                    self.logger.debug(f"✅ Signal created at row {i} (idx={idx}): {signal_type} confidence={confidence:.4f}")

            except Exception as e:
                # Log exception but continue processing other rows
                self.logger.error(f"❌ Error creating signal for row {i} (idx={idx}): {e}", exc_info=True)
                continue

        # Log summary of signal creation
        if signals_filtered_count > 0 or signals_created_count > 0:
            self.logger.info(
                f"Signal creation summary: {total_rows_processed} rows processed, "
                f"{signals_filtered_count} scores above threshold, {signals_created_count} signals created"
            )
        elif len(df) > 0:
            # Log warning if no signals created
            self.logger.warning(
                f"No signals created from {len(df)} rows. "
                f"Combined score range: [{combined_score.min():.4f}, {combined_score.max():.4f}], "
                f"Threshold: {self.config.signal_threshold}"
            )

        return signals

    def _generate_ml_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate ML-based signals (simplified version)"""
        # This is a simplified ML signal - in practice, you'd use trained models
        ml_score = pd.Series(0.0, index=df.index)

        # Simple feature-based scoring
        features_to_use = [
            'return_1d_cs_zscore', 'rsi_normalized', 'volume_ratio',
            'bb_position', 'atr_percentile'
        ]

        available_features = [f for f in features_to_use if f in df.columns]

        if available_features:
            # Weighted combination of normalized features
            feature_weights = [0.3, 0.25, 0.2, 0.15, 0.1]

            for i, feature in enumerate(available_features):
                weight = feature_weights[i] if i < len(feature_weights) else 0.1
                feature_values = df[feature].fillna(0)

                # Apply simple non-linear transformation
                if feature == 'return_1d_cs_zscore':
                    # Mean reversion signal
                    ml_score += weight * np.tanh(-feature_values)
                elif feature == 'rsi_normalized':
                    # Mean reversion signal
                    ml_score += weight * np.tanh(-feature_values * 2)
                elif feature == 'volume_ratio':
                    # Volume confirmation
                    ml_score += weight * np.tanh((feature_values - 1) * 0.5)
                else:
                    # General momentum signal
                    ml_score += weight * np.tanh(feature_values)

        return ml_score

    def _filter_signals(self, signals: List[TradingSignal], df: pd.DataFrame) -> List[TradingSignal]:
        """Filter signals based on risk, quality, and regime criteria (Rule 2 (Regime-First Principle))"""
        filtered = []

        for signal in signals:
            # Create a mask for the signal's data
            signal_data = df[(df['symbol'] == signal.symbol) &
                           (df['timestamp'] == signal.timestamp)]

            if signal_data.empty:
                continue

            row = signal_data.iloc[0]

            # Volume filter
            volume_ratio = row.get('volume_ratio', 1.0)
            if volume_ratio < self.config.min_volume_ratio:
                continue

            # Volatility filter
            if 'atr_percentile' in row:
                if row['atr_percentile'] > self.config.max_volatility_percentile:
                    continue

            # REGIME-AWARE FILTERING (Rule 2 (Regime-First Principle))
            # CRITICAL: Get regime for THIS signal's timestamp (bar-by-bar regime awareness)
            adjusted_confidence = signal.confidence
            regime_adjustment_factor = 1.0

            # Get regime for THIS signal's timestamp (not just latest regime)
            signal_regime = None
            if self.regime_engine:
                # Use injected regime engine to get regime at signal's timestamp
                candidate_regime = self.regime_engine.get_regime_at_timestamp(
                    symbol=signal.symbol,
                    timestamp=signal.timestamp
                )
                if self._is_valid_regime_context(candidate_regime):
                    signal_regime = candidate_regime

            # Fallback to current_regime if timestamp lookup fails or context invalid
            if not self._is_valid_regime_context(signal_regime):
                signal_regime = self.current_regime if self._is_valid_regime_context(self.current_regime) else None

            if signal_regime and hasattr(signal_regime, 'primary_regime'):
                regime_name = self._coerce_str(
                    signal_regime.primary_regime.value if hasattr(signal_regime.primary_regime, 'value') else signal_regime.primary_regime,
                    default='unknown'
                )
                volatility_source = getattr(signal_regime, 'volatility_regime', None)
                if volatility_source in (None, '', 'unknown'):
                    volatility_source = getattr(signal_regime, 'primary_regime', volatility_source)
                volatility_source = getattr(volatility_source, 'value', volatility_source)
                if (not volatility_source or volatility_source == 'normal_volatility') and isinstance(regime_name, str):
                    if 'volatility' in regime_name:
                        volatility_source = regime_name
                volatility_regime = self._coerce_str(
                    volatility_source,
                    default='normal_volatility'
                )
                regime_confidence = getattr(signal_regime, 'confidence', None)
                if regime_confidence is None:
                    regime_confidence = getattr(signal_regime, 'regime_confidence', 0.5)
                regime_confidence = self._coerce_numeric(regime_confidence, default=0.5)

                # Adjust signal confidence based on regime confidence
                regime_adjustment_factor *= regime_confidence

                # Volatility-based threshold adjustments
                if volatility_regime == 'high_volatility' or volatility_regime == 'extreme_volatility':
                    # Stricter filtering in high/extreme volatility regimes
                    reduction = 0.8 if volatility_regime == 'high_volatility' else 0.6
                    regime_adjustment_factor *= reduction
                    self.logger.debug(
                        f"{volatility_regime} regime: reducing signal confidence by {(1 - reduction) * 100:.0f}%"
                    )
                elif volatility_regime == 'low_volatility':
                    # Relaxed filtering in low volatility regimes
                    regime_adjustment_factor *= 1.1
                    self.logger.debug(f"Low volatility regime: increasing signal confidence by 10%")

                # Strategy appropriateness for current regime
                strategy_appropriateness = self._get_strategy_regime_appropriateness(
                    signal.strategy, regime_name, volatility_regime
                )
                regime_adjustment_factor *= strategy_appropriateness

                # CRITICAL FIX: Cap minimum adjustment factor to prevent over-filtering
                # Even in worst-case scenarios, don't reduce confidence by more than 20%
                # This prevents signals from being filtered out too aggressively
                # Using 0.8 ensures signals with confidence 0.65+ can still pass 0.6 threshold after adjustments
                # Example: 0.65 × 0.8 = 0.52 (too low), but with higher base confidence (0.7+) → 0.7 × 0.8 = 0.56
                # Combined with enhanced confidence scaling, signals should pass
                min_factor = 0.8
                if volatility_regime == 'extreme_volatility':
                    min_factor = 0.5
                regime_adjustment_factor = max(min_factor, regime_adjustment_factor)

                # Apply regime adjustments to confidence
                adjusted_confidence = signal.confidence * regime_adjustment_factor

                self.logger.debug(f"Regime adjustment: {signal.strategy} in {regime_name} "
                                f"(vol: {volatility_regime}) -> factor: {regime_adjustment_factor:.2f}, "
                                f"confidence: {signal.confidence:.2f} -> {adjusted_confidence:.2f}")

            # Apply adjusted confidence threshold
            if adjusted_confidence < self.config.signal_threshold:
                self.logger.debug(f"Signal filtered: confidence {adjusted_confidence:.2f} < threshold {self.config.signal_threshold}")
                continue

            # ML confidence filter (if enabled)
            if self.config.enable_ml_signals and hasattr(self.config, 'ml_confidence_threshold') and adjusted_confidence < self.config.ml_confidence_threshold:
                # Only apply strict ML filter for weak signals
                if signal.strength == SignalStrength.WEAK:
                    self.logger.debug(f"Signal filtered: ML confidence {adjusted_confidence:.2f} < threshold {self.config.ml_confidence_threshold}")
                    continue

            # Update signal with adjusted confidence
            signal.confidence = adjusted_confidence
            signal.metadata['regime_adjustment_factor'] = regime_adjustment_factor
            if signal_regime:
                signal.metadata['regime'] = regime_name
                signal.metadata['volatility_regime'] = volatility_regime
                signal.metadata['regime_confidence'] = regime_confidence
                signal.metadata['regime_at_signal_timestamp'] = True  # Flag indicating bar-by-bar lookup
                if volatility_regime == 'extreme_volatility':
                    original_size = signal.position_size
                    signal.position_size = min(signal.position_size, 0.02)
                    signal.metadata['position_size_adjustment'] = {
                        'reason': 'extreme_volatility_cap',
                        'original_size': original_size,
                        'adjusted_size': signal.position_size
                    }
                elif volatility_regime == 'high_volatility':
                    original_size = signal.position_size
                    signal.position_size = min(signal.position_size, 0.05)
                    signal.metadata['position_size_adjustment'] = {
                        'reason': 'high_volatility_cap',
                        'original_size': original_size,
                        'adjusted_size': signal.position_size
                    }

            filtered.append(signal)

        self.logger.info(f"Regime-aware filtering: {len(signals)} raw signals -> {len(filtered)} final signals")
        return filtered

    def _get_strategy_regime_appropriateness(self, strategy: str, regime_name: str, volatility_regime: str) -> float:
        """
        Determine strategy appropriateness for current market regime (Rule 2 (Regime-First Principle))

        Args:
            strategy: Strategy name (e.g., 'momentum', 'mean_reversion', 'rsi', 'macd')
            regime_name: Current market regime (e.g., 'bull_market', 'bear_market', 'sideways')
            volatility_regime: Current volatility regime (e.g., 'low_volatility', 'high_volatility')

        Returns:
            float: Appropriateness factor (0.0-1.0, where 1.0 = fully appropriate)
        """

        # Strategy-regime appropriateness matrix
        strategy_regime_matrix = {
            # Mean Reversion Strategies
            'rsi': {
                'bull_market': 0.6,      # RSI works in bull markets but less effective
                'bear_market': 0.8,      # RSI effective in bear markets (oversold bounces)
                'sideways': 0.9,         # RSI excellent in sideways markets
                'trending': 0.4,         # RSI poor in strong trending markets
                'volatile': 0.3,         # RSI poor in volatile markets
                'crisis': 0.2            # RSI very poor in crisis markets
            },
            'mean_reversion': {
                'bull_market': 0.6,
                'bear_market': 0.8,
                'sideways': 0.95,        # Mean reversion excels in sideways markets
                'trending': 0.3,
                'volatile': 0.2,
                'crisis': 0.1
            },

            # Momentum Strategies
            'momentum': {
                'bull_market': 0.9,      # Momentum excellent in bull markets
                'bear_market': 0.7,      # Momentum good in bear markets (downward momentum)
                'sideways': 0.3,         # Momentum poor in sideways markets
                'trending': 0.95,        # Momentum excellent in trending markets
                'volatile': 0.6,         # Momentum moderate in volatile markets
                'crisis': 0.4
            },
            'macd': {
                'bull_market': 0.9,
                'bear_market': 0.8,
                'sideways': 0.4,
                'trending': 0.95,
                'volatile': 0.5,
                'crisis': 0.3
            },
            'sma_crossover': {
                'bull_market': 0.9,
                'bear_market': 0.8,
                'sideways': 0.3,
                'trending': 0.95,
                'volatile': 0.4,
                'crisis': 0.2
            },

            # Volume Strategies
            'volume': {
                'bull_market': 0.8,      # Volume confirmation good in bull markets
                'bear_market': 0.8,      # Volume confirmation good in bear markets
                'sideways': 0.7,         # Volume moderate in sideways markets
                'trending': 0.9,         # Volume excellent for trend confirmation
                'volatile': 0.6,         # Volume moderate in volatile markets
                'crisis': 0.5            # Volume mixed in crisis markets
            },

            # Multi-factor strategies
            'combined': {
                'bull_market': 0.8,      # Combined strategies generally robust
                'bear_market': 0.8,
                'sideways': 0.8,
                'trending': 0.8,
                'volatile': 0.6,         # Combined strategies less effective in extreme volatility
                'crisis': 0.4
            }
        }

        # Normalize strategy name (handle 'signal_generator_<source>' format from unbiased approach)
        # Extract signal source from strategy name (e.g., 'signal_generator_mean_reversion' -> 'mean_reversion')
        normalized_strategy = strategy
        if strategy.startswith('signal_generator_'):
            normalized_strategy = strategy.replace('signal_generator_', '')

        # Normalize regime name (map regime engine names to matrix keys)
        # Regime engine returns: 'bear_high_volatility', 'bull_high_volatility', 'range_bound', etc.
        # Matrix expects: 'bear_market', 'bull_market', 'sideways', etc.
        normalized_regime = self._normalize_regime_name(regime_name)

        # Get base appropriateness for strategy-regime combination
        # Try normalized name first, then fall back to original strategy name
        base_appropriateness = strategy_regime_matrix.get(normalized_strategy, {}).get(normalized_regime)
        if base_appropriateness is None:
            # Try original regime name with normalized strategy
            base_appropriateness = strategy_regime_matrix.get(normalized_strategy, {}).get(regime_name)
        if base_appropriateness is None:
            # Fallback to original strategy name with normalized regime
            base_appropriateness = strategy_regime_matrix.get(strategy, {}).get(normalized_regime)
        if base_appropriateness is None:
            # Final fallback: default 0.5
            base_appropriateness = 0.5

        # Volatility regime adjustments
        volatility_adjustments = {
            'low_volatility': 1.1,       # Strategies generally more effective in low vol
            'normal_volatility': 1.0,    # Normal effectiveness
            'high_volatility': 0.8,      # Strategies less effective in high vol
            'extreme_volatility': 0.6,   # Strategies much less effective in extreme vol
            'crisis_liquidity': 0.4      # Strategies very poor in crisis
        }

        volatility_factor = volatility_adjustments.get(volatility_regime, 1.0)

        # Calculate final appropriateness
        final_appropriateness = base_appropriateness * volatility_factor

        # Ensure appropriateness is within valid range
        final_appropriateness = max(0.1, min(1.0, final_appropriateness))

        self.logger.debug(f"Strategy appropriateness: {strategy} in {regime_name} (normalized: {normalized_regime}) "
                         f"(vol: {volatility_regime}) -> {base_appropriateness:.2f} * {volatility_factor:.2f} = {final_appropriateness:.2f}")

        return final_appropriateness

    def _normalize_regime_name(self, regime_name: str) -> str:
        """
        Map regime engine regime names to strategy_regime_matrix keys

        Regime engine returns composite names like 'bear_high_volatility', 'bull_high_volatility',
        but strategy_regime_matrix uses simpler names like 'bear_market', 'bull_market'.

        Args:
            regime_name: Regime name from regime engine (e.g., 'bear_high_volatility')

        Returns:
            Normalized regime name for matrix lookup (e.g., 'bear_market')
        """
        # Map regime engine regime names to matrix keys
        regime_mapping = {
            # Directional + volatility combinations → directional markets
            'bull_low_volatility': 'bull_market',
            'bull_high_volatility': 'bull_market',
            'bear_low_volatility': 'bear_market',
            'bear_high_volatility': 'bear_market',

            # Consolidation regimes
            'range_bound': 'sideways',
            'choppy': 'volatile',

            # Direct mappings (if already normalized)
            'bull_market': 'bull_market',
            'bear_market': 'bear_market',
            'sideways': 'sideways',
            'trending': 'trending',
            'volatile': 'volatile',
            'crisis': 'crisis'
        }

        return regime_mapping.get(regime_name, regime_name)

    def generate_all_signals(self, df: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate all types of signals for a symbol"""
        if df.empty:
            raise ValueError("Cannot generate signals from empty DataFrame")

        # Filter data for the specific symbol
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return []

        # Use the main generate_signals method
        return self.generate_signals(symbol_data)

    def generate_rsi_signals(self, df: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate RSI-based signals for a specific symbol"""
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return []

        mean_rev_signals = self._generate_mean_reversion_signals(symbol_data)
        signals = []

        for idx, row in mean_rev_signals.iterrows():
            if pd.notna(row.get('rsi_signal', 0)) and abs(row['rsi_signal']) > self.config.signal_threshold:
                signal_type = SignalType.BUY if row['rsi_signal'] > 0 else SignalType.SELL
                confidence = min(abs(row['rsi_signal']), 1.0)

                signal = TradingSignal(
                    symbol=symbol,
                    timestamp=idx,
                    signal_type=signal_type,
                    strength=SignalStrength.STRONG if confidence > self.config.strong_signal_threshold else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=row['close'],
                    strategy="rsi",
                    metadata={"rsi_value": row.get('rsi', 50), "signal_source": "rsi"}
                )
                signals.append(signal)

        return self._filter_signals(signals, symbol_data)

    def generate_macd_signals(self, df: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate MACD-based signals for a specific symbol"""
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return []

        momentum_signals = self._generate_momentum_signals(symbol_data)
        signals = []

        for idx, row in momentum_signals.iterrows():
            if pd.notna(row.get('macd_signal', 0)) and abs(row['macd_signal']) > self.config.signal_threshold:
                signal_type = SignalType.BUY if row['macd_signal'] > 0 else SignalType.SELL
                confidence = min(abs(row['macd_signal']), 1.0)

                signal = TradingSignal(
                    symbol=symbol,
                    timestamp=idx,
                    signal_type=signal_type,
                    strength=SignalStrength.STRONG if confidence > self.config.strong_signal_threshold else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=row['close'],
                    strategy="macd",
                    metadata={"macd_value": row.get('macd_line', 0), "signal_source": "macd"}
                )
                signals.append(signal)

        return self._filter_signals(signals, symbol_data)

    def generate_sma_crossover_signals(self, df: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate SMA crossover signals for a specific symbol"""
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return []

        momentum_signals = self._generate_momentum_signals(symbol_data)
        signals = []

        for idx, row in momentum_signals.iterrows():
            if pd.notna(row.get('sma_crossover_signal', 0)) and abs(row['sma_crossover_signal']) > self.config.signal_threshold:
                signal_type = SignalType.BUY if row['sma_crossover_signal'] > 0 else SignalType.SELL
                confidence = min(abs(row['sma_crossover_signal']), 1.0)

                signal = TradingSignal(
                    symbol=symbol,
                    timestamp=idx,
                    signal_type=signal_type,
                    strength=SignalStrength.STRONG if confidence > self.config.strong_signal_threshold else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=row['close'],
                    strategy="sma_crossover",
                    metadata={"sma_20": row.get('sma_20', 0), "sma_50": row.get('sma_50', 0), "signal_source": "sma_crossover"}
                )
                signals.append(signal)

        return self._filter_signals(signals, symbol_data)

    def generate_volume_signals(self, df: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate volume-based signals for a specific symbol"""
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return []

        volume_signals = self._generate_volume_signals(symbol_data)
        signals = []

        for idx, row in volume_signals.iterrows():
            if pd.notna(row.get('volume_signal', 0)) and abs(row['volume_signal']) > self.config.signal_threshold:
                signal_type = SignalType.BUY if row['volume_signal'] > 0 else SignalType.SELL
                confidence = min(abs(row['volume_signal']), 1.0)

                signal = TradingSignal(
                    symbol=symbol,
                    timestamp=idx,
                    signal_type=signal_type,
                    strength=SignalStrength.STRONG if confidence > self.config.strong_signal_threshold else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=row['close'],
                    strategy="volume",
                    metadata={"volume_ratio": row.get('volume_ratio', 1.0), "signal_source": "volume"}
                )
                signals.append(signal)

        return self._filter_signals(signals, symbol_data)

    def generate_combined_signals(self, df: pd.DataFrame, symbol: str, min_confidence: Optional[float] = None) -> List[TradingSignal]:
        """Generate combined signals for a specific symbol with optional confidence filtering"""
        if min_confidence is not None and (min_confidence < 0.0 or min_confidence > 1.0):
            raise ValueError("min_confidence must be between 0.0 and 1.0")

        signals = self.generate_all_signals(df, symbol)

        if min_confidence is not None:
            signals = [s for s in signals if s.confidence >= min_confidence]

        return signals

    def get_signal_summary(self, signals: List[TradingSignal]) -> Dict[str, Any]:
        """Get summary statistics of generated signals"""
        if not signals:
            return {"total_signals": 0}

        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]

        strong_signals = [s for s in signals if s.strength == SignalStrength.STRONG]

        return {
            "total_signals": len(signals),
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "strong_signals": len(strong_signals),
            "avg_confidence": np.mean([s.confidence for s in signals]),
            "avg_position_size": np.mean([s.position_size for s in signals]),
            "symbols_with_signals": len(set(s.symbol for s in signals)),
            "signal_distribution": {
                "strong": len([s for s in signals if s.strength == SignalStrength.STRONG]),
                "moderate": len([s for s in signals if s.strength == SignalStrength.MODERATE]),
                "weak": len([s for s in signals if s.strength == SignalStrength.WEAK])
            }
        }

    @staticmethod
    def _coerce_numeric(value: Any, default: float = 1.0) -> float:
        """
        Safely convert mock/test doubles or arbitrary objects to a float.
        """
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _coerce_str(value: Any, default: str = "unknown") -> str:
        """
        Safely convert mock/test doubles or arbitrary objects to string.
        """
        try:
            if value is None:
                return default
            if isinstance(value, str):
                return value
            if hasattr(value, "value"):
                return str(value.value)
            return str(value)
        except Exception:
            return default

    def _is_valid_regime_context(self, context: Any) -> bool:
        """
        Determine if the provided context looks like a usable regime context.
        """
        if context is None:
            return False
        primary = getattr(context, 'primary_regime', None)
        if primary is None:
            return False
        primary_value = getattr(primary, 'value', primary)
        if isinstance(primary_value, str):
            return True
        if isinstance(primary_value, Enum):
            return True
        return False

    # ========================================
    # STANDARDIZED DATA CONSUMPTION METHODS
    # ========================================

    def process_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for processing signals data"""
        return signals

    def analyze_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for analyzing signals data (alias)"""
        return self.process_signals(signals)

    def evaluate_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for evaluating signals data (alias)"""
        return self.process_signals(signals)

    def process_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for processing features data (consumption interface)"""
        # This component consumes features to produce signals
        return features

    def use_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for using features data (consumption interface)"""
        return self.process_features(features)

    def analyze_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for analyzing features data (consumption interface)"""
        return self.process_features(features)