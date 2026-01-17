#!/usr/bin/env python3
"""
Feature Engineering Module for Core Engine
==========================================

Transforms technical indicators into trading features for signal generation.
Creates normalized, scaled, and cross-sectional features suitable for ML models.

Author: StatArb_Gemini Core Engine
Version: 1.1.0 (Performance Optimized)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from sklearn.preprocessing import StandardScaler, RobustScaler
from scipy import stats
import warnings
import threading
import uuid
from datetime import datetime
warnings.filterwarnings('ignore')

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
from ...system.interfaces import ISystemComponent, IRegimeAware

logger = logging.getLogger(__name__)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
from core_engine.config import FeatureConfig

try:
    import bottleneck as bn
    HAS_BOTTLENECK = True
except ImportError:
    HAS_BOTTLENECK = False

# Import JIT utilities for performance optimization
from core_engine.utils.jit_utils import (
    jit_rolling_rank, 
    jit_rolling_mad_zscore, 
    jit_rolling_stats,
    jit_cs_rank,
    jit_cs_zscore
)

class EnhancedFeatureEngineer(ISystemComponent, IRegimeAware):
    """
    Enhanced Feature Engineering with ISystemComponent & IRegimeAware Integration

    Institutional-grade feature engineering with orchestrator integration:
    - Implements ISystemComponent for lifecycle management (Rule 1)
    - Implements IRegimeAware for regime adaptation (Rule 2)
    - Normalization and scaling with professional standards
    - Lag features for temporal patterns
    - Cross-sectional features for relative analysis
    - Rolling statistics and momentum features
    - Health monitoring and performance tracking
    - Regime-aware feature engineering
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        # Handle both FeatureConfig objects and dictionaries
        # Rule 1 Section 7: Use centralized configuration from core_engine.config
        if isinstance(config, dict):
            try:
                from core_engine.config import FeatureConfig as CentralizedFeatureConfig
                self.config = CentralizedFeatureConfig(**{k: v for k, v in config.items() if hasattr(CentralizedFeatureConfig, k)})
            except ImportError:
                # Fallback during migration
                self.config = FeatureConfig(**{k: v for k, v in config.items() if k in FeatureConfig.__dataclass_fields__})
        else:
            self.config = config or FeatureConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False

        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        self.start_time = None

        # PHASE 3: Regime awareness (Rule 2 Regime-First)
        self.regime_engine: Optional[Any] = None  # EnhancedRegimeEngine reference
        self.current_regime: Optional[Any] = None  # Current regime context

        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedFeatureEngineer',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_feature_engineering': 0,
                'successful_feature_engineering': 0,
                'failed_feature_engineering': 0,
                'average_processing_time': 0.0,
                'features_created_count': 0
            }
        }

        # Scalers for different feature types
        self.scalers: Dict[str, Any] = {}

        # Feature metadata
        self.feature_columns: List[str] = []
        self.target_columns: List[str] = []

        # Threading
        self._lock = threading.Lock()

        self.logger.info(f"🚀 Enhanced Feature Engineer initialized with component ID: {self.component_id}")
        self.liquidity_engine: Optional[Any] = None
        self.current_liquidity: Optional[Dict[str, Any]] = None
        self._base_normalization_method = self.config.normalization_method
        self._base_lookback_periods = list(self.config.lookback_periods)

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedFeatureEngineer",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=16  # PHASE 3: After Indicators(15), before Signals(17)
        )

        self.logger.info(f"✅ EnhancedFeatureEngineer registered with orchestrator: {self.component_id}")
        return self.component_id

    def set_liquidity_engine(self, liquidity_engine: Any) -> None:
        """Inject liquidity engine reference for downstream adjustments"""
        self.liquidity_engine = liquidity_engine
        self.logger.debug("✅ Liquidity engine reference set for feature engineer")

    # ========================================
    # PHASE 3: REGIME AWARENESS (RULE 2 - IRegimeAware Interface)
    # ========================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine reference for regime-aware feature engineering (Rule 2 Regime-First)
        Part of IRegimeAware interface implementation.
        """
        self.regime_engine = regime_engine
        self.logger.info(f"✅ RegimeEngine injected into FeatureEngineer (IRegimeAware, Rule 2)")

    async def on_regime_change(self, new_regime_context: Any) -> None:
        """
        Handle regime change event - IRegimeAware interface method
        Callback for regime changes from the EnhancedRegimeEngine.
        Adapt feature engineering to new market regime.

        Args:
            new_regime_context: New regime context with updated information
        """
        previous_regime = self.current_regime.primary_regime.value if (self.current_regime and hasattr(self.current_regime, 'primary_regime') and hasattr(self.current_regime.primary_regime, 'value')) else (self.current_regime.primary_regime if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None)
        self.current_regime = new_regime_context

        regime_name = new_regime_context.primary_regime.value if (hasattr(new_regime_context, 'primary_regime') and hasattr(new_regime_context.primary_regime, 'value')) else (new_regime_context.primary_regime if hasattr(new_regime_context, 'primary_regime') else str(new_regime_context))
        self.logger.info(f"🔄 Features adapting to regime change: {previous_regime} → {regime_name}")

        # Adapt feature engineering to regime
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
        - High volatility → More robust scaling, longer lookback periods
        - Low volatility → Standard scaling, shorter lookback periods
        - Trending → Momentum features prioritized
        - Range-bound → Mean-reversion features prioritized

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

            # Adapt normalization method based on volatility
            if volatility_regime == 'high_volatility':
                self.config.normalization_method = 'robust'  # More robust to outliers
                self.config.lookback_periods = [10, 20, 40]  # Longer periods
                adaptations['adjustments'].append({
                    'normalization': 'robust',
                    'lookback_periods': [10, 20, 40],
                    'reason': 'high_volatility'
                })
                self.logger.info(f"📊 Features adapted for high volatility: robust scaling, longer lookbacks")
            elif volatility_regime == 'low_volatility':
                self.config.normalization_method = 'standard'  # Standard scaling
                self.config.lookback_periods = [5, 10, 20]  # Shorter periods
                adaptations['adjustments'].append({
                    'normalization': 'standard',
                    'lookback_periods': [5, 10, 20],
                    'reason': 'low_volatility'
                })
                self.logger.info(f"📊 Features adapted for low volatility: standard scaling, shorter lookbacks")
            else:
                # Use existing configuration without modification
                adaptations['adjustments'].append({
                    'normalization': self.config.normalization_method,
                    'lookback_periods': self.config.lookback_periods,
                    'reason': 'normal_volatility'
                })

            # Clear scalers when regime changes (force refitting)
            if self.scalers:
                scaler_count = len(self.scalers)
                self.scalers.clear()
                adaptations['scalers_cleared'] = True
                adaptations['scaler_count_cleared'] = scaler_count
                self.logger.info(f"🗑️ Feature scalers cleared ({scaler_count}) for regime adaptation")

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
            self.logger.warning("⚠️ Regime engine not configured for FeatureEngineer")
        else:
            self.logger.debug("✅ Regime engine properly configured")
        return is_valid

    def adapt_to_liquidity(self, liquidity_context: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust feature engineering parameters based on liquidity conditions"""
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

        if score <= 40:
            self.config.normalization_method = 'robust'
            self.config.lookback_periods = [max(p, p + 5) for p in self._base_lookback_periods]
            adjustments['mode'] = 'low_liquidity'
        elif score >= 80:
            self.config.normalization_method = self._base_normalization_method
            self.config.lookback_periods = [max(3, int(p * 0.8)) for p in self._base_lookback_periods]
            adjustments['mode'] = 'high_liquidity'
        else:
            self.config.normalization_method = self._base_normalization_method
            self.config.lookback_periods = list(self._base_lookback_periods)
            adjustments['mode'] = 'normal'

        self.current_liquidity = liquidity_context
        adjustments['normalization_method'] = self.config.normalization_method
        adjustments['lookback_periods'] = self.config.lookback_periods
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
        """Initialize the Enhanced Feature Engineer"""
        try:
            self.logger.info("🔄 Initializing Enhanced Feature Engineer...")

            # Initialize feature engineering engines
            await self._initialize_feature_engines()

            # Initialize monitoring
            await self._initialize_monitoring_system()

            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'

            self.logger.info("✅ Enhanced Feature Engineer initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Feature Engineer initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False

    async def start(self) -> bool:
        """Start the Enhanced Feature Engineer"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Feature Engineer: not initialized")
            return False

        try:
            self.logger.info("🚀 Starting Enhanced Feature Engineer...")

            # Start monitoring
            await self._start_monitoring()

            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'

            self.logger.info("✅ Enhanced Feature Engineer started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Feature Engineer start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def stop(self) -> bool:
        """Stop the Enhanced Feature Engineer"""
        try:
            self.logger.info("🛑 Stopping Enhanced Feature Engineer...")

            # Stop monitoring
            await self._stop_monitoring()

            # Clear scalers
            self.scalers.clear()

            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'

            self.logger.info("✅ Enhanced Feature Engineer stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Enhanced Feature Engineer stop failed: {e}")
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

            # Check feature engines health
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
                'scalers_count': len(self.scalers),
                'feature_columns_count': len(self.feature_columns),
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
                'use_normalization': self.config.use_normalization,
                'normalization_method': self.config.normalization_method,
                'enable_cross_sectional': self.config.enable_cross_sectional,
                'max_features': self.config.max_features,
                'lookback_periods': self.config.lookback_periods,
                'lag_periods': self.config.lag_periods
            },
            'health_metrics': self.health_metrics
        }

    # Enhanced Internal Methods

    async def _initialize_feature_engines(self) -> None:
        """Initialize feature engineering engines"""
        try:
            self.logger.info("🔧 Initializing feature engineering engines...")

            # Initialize scalers based on configuration
            if self.config.use_normalization:
                if self.config.normalization_method == "standard":
                    self.scalers['default'] = StandardScaler()
                elif self.config.normalization_method == "robust":
                    self.scalers['default'] = RobustScaler()
                else:
                    raise ValueError(f"Unsupported normalization method: {self.config.normalization_method}")

            self.logger.info("✅ Feature engineering engines initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize feature engines: {e}")
            raise

    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")

            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_feature_engineering': 0,
                'successful_feature_engineering': 0,
                'failed_feature_engineering': 0,
                'average_processing_time': 0.0,
                'features_created_count': 0
            }

            self.logger.info("✅ Monitoring system initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise

    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for feature engineer
            self.logger.info("✅ Monitoring systems started")

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise

    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for feature engineer
            self.logger.info("✅ Monitoring systems stopped")

        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise

    async def _check_engines_health(self) -> bool:
        """Check health of feature engineering engines"""
        try:
            # Basic health check - verify core functionality
            test_data = pd.DataFrame({
                'symbol': ['TEST'] * 5,
                'timestamp': pd.date_range('2024-01-01', periods=5),
                'close': [100, 101, 102, 103, 104],
                'rsi': [50, 55, 60, 65, 70]
            })

            # Test basic feature creation
            result = self._create_lag_features(test_data)
            return len(result.columns) >= len(test_data.columns)

        except Exception as e:
            self.logger.warning(f"Engine health check failed: {e}")
            return False

    def create_features(
        self,
        data: Union[Dict[str, pd.DataFrame], pd.DataFrame],
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Create trading features for multiple symbols or a single DataFrame with context awareness.

        Args:
            data: Symbol-to-DataFrame mapping or single DataFrame.
            regime_context: Optional regime context.
            liquidity_context: Optional liquidity context.

        Returns:
            Processed data with engineered features.
        """
        # Handle single DataFrame input
        if isinstance(data, pd.DataFrame):
            return self._create_features_for_single_df(
                data,
                regime_context=regime_context,
                liquidity_context=liquidity_context
            )

        # Handle dictionary input
        result = {}

        for symbol, df in data.items():
            if df.empty:
                continue

            # Create features for this symbol
            df = self._create_symbol_features(
                df,
                regime_context=regime_context,
                liquidity_context=liquidity_context
            )

            # Create cross-sectional features if enabled
            if self.config.enable_cross_sectional:
                df = self._create_cross_sectional_features(df)

            # Normalize features if enabled
            if self.config.use_normalization:
                df = self._normalize_features(df)

            result[symbol] = df

        return result

    def _create_features_for_single_df(
        self,
        df: pd.DataFrame,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Create features for a single DataFrame, ensuring timestamp sort."""
        if df.empty:
            return df

        if 'timestamp' not in df.columns:
            return df
            
        df = df.sort_values('timestamp')

        # Create symbol features
        df = self._create_symbol_features(
            df,
            regime_context=regime_context,
            liquidity_context=liquidity_context
        )

        # Create cross-sectional features if multiple symbols present
        if self.config.enable_cross_sectional and 'symbol' in df.columns and df['symbol'].nunique() > 1:
            df = self._create_cross_sectional_features(df)

        # Normalize features if enabled
        if self.config.use_normalization:
            df = self._normalize_features(df)

        return df

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Alias for create_features."""
        return self.create_features(df)

    def _create_symbol_features(
        self,
        df: pd.DataFrame,
        regime_context: Optional[Any] = None,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Create features using a stateless-compatible pattern."""
        # Basic price features
        df = self._create_price_features(df)

        # Momentum features
        df = self._create_momentum_features(df)

        # Composite momentum features (Phase 4A)
        df = self._create_composite_momentum_features(df)

        # Volatility features
        df = self._create_volatility_features(df)

        # Volume features
        df = self._create_volume_features(df)

        # Technical indicator features
        df = self._create_indicator_features(df)

        # Lag features
        df = self._create_lag_features(df)

        # Rolling statistics
        df = self._create_rolling_features(df)

        return df

    def _create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features with minimal fragmentation (Hotspot 1)"""
        new_columns = {}
        
        # Returns at different horizons
        for period in [1, 2, 3, 5, 10]:
            if len(df) > period:
                new_columns[f'return_{period}d'] = df['close'].pct_change(periods=period, fill_method=None)
        
        # Log returns (handle invalid values)
        price_ratio = df['close'] / df['close'].shift(1)
        positive_mask = price_ratio > 0
        log_return = np.full(len(df), np.nan)
        if positive_mask.any():
            log_return[positive_mask] = np.log(price_ratio[positive_mask])
        new_columns['log_return'] = log_return
        
        # OHLC ratios
        new_columns['hl_range'] = (df['high'] - df['low']) / df['close']
        new_columns['oc_range'] = (df['open'] - df['close']) / df['close']
        new_columns['hl_ratio'] = df['high'] / df['low']
        new_columns['body_size'] = np.abs(df['close'] - df['open']) / df['close']
        new_columns['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        new_columns['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # Gap features
        new_columns['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        # Price momentum
        new_columns['price_acceleration'] = pd.Series(log_return, index=df.index).diff()
        
        # Volatility proxies
        if 'return_1d' in new_columns:
            new_columns['daily_vol'] = new_columns['return_1d'].rolling(20).std()
        
        # Concatenate once to avoid fragmentation
        df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
        return df

    def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features"""
        # Price momentum features (percentage change over different periods)
        # These are CRITICAL for momentum strategies
        for period in [10, 20, 50]:
            if len(df) > period:
                df[f'momentum_{period}'] = df['close'].pct_change(periods=period, fill_method=None)

        # Trend strength (based on price consistency)
        # Measures how consistently price moves in one direction
        if len(df) >= 20:
            # Calculate trend strength as the ratio of cumulative return to cumulative absolute return
            returns_raw = df['close'].pct_change(fill_method=None)
            cumulative_return = returns_raw.rolling(20).sum()
            cumulative_abs_return = returns_raw.abs().rolling(20).sum()

            # Avoid division by zero
            df['trend_strength'] = 0.0
            mask = cumulative_abs_return > 0.001
            df.loc[mask, 'trend_strength'] = (cumulative_return[mask] / cumulative_abs_return[mask]).abs()

        # ADX-based trend strength (if ADX available)
        if 'adx' in df.columns:
            # Normalize ADX to 0-1 scale
            df['adx_normalized'] = df['adx'] / 100.0
            # ADX trend signal: >25 indicates trending market
            df['adx_trending'] = (df['adx'] > 25).astype(int)

        # RSI-based features
        if 'rsi' in df.columns:
            df['rsi_normalized'] = (df['rsi'] - 50) / 50  # Center at 0
            df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            df['rsi_momentum'] = df['rsi'].diff()

        # MACD features
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            df['macd_divergence'] = df['macd'] - df['macd_signal']
            df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
            if 'macd_histogram' in df.columns:
                df['macd_hist_momentum'] = df['macd_histogram'].diff()

        # Stochastic features
        if 'stoch_k' in df.columns:
            df['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
            df['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
            if 'stoch_d' in df.columns:
                df['stoch_crossover'] = (df['stoch_k'] > df['stoch_d']).astype(int)

        # Rate of change features
        roc_cols = [col for col in df.columns if col.startswith('roc_')]
        for col in roc_cols:
            df[f'{col}_normalized'] = df[col] / df[col].rolling(20).std()

        return df

    def _create_composite_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create composite momentum features (Phase 4A - Option A)

        Combines multiple momentum indicators into robust composite signals:
        - composite_z: MAD-based Z-score aggregation (outlier-resistant)
        - composite_pct: Percentile ranking (0-100 scale)

        Uses 10 momentum indicators for comprehensive momentum assessment:
        1. Short-term momentum (10-day)
        2. Medium-term momentum (20-day)
        3. Long-term momentum (50-day)
        4. RSI (Relative Strength Index)
        5. MACD histogram
        6. Stochastic K
        7. ROC (Rate of Change)
        8. ADX (Trend Strength)
        9. Trend strength (directional consistency)
        10. Volume ratio (confirmation)

        Returns:
            DataFrame with composite_z and composite_pct columns added
        """

        try:
            # Initialize composite features with default values
            df['composite_z'] = 0.0
            df['composite_pct'] = 50.0  # Neutral percentile

            # Minimum data requirement
            if len(df) < 50:
                self.logger.debug("Insufficient data for composite features (need 50+ bars)")
                return df

            # Step 1: Collect 10 momentum indicators
            momentum_indicators = []
            indicator_names = []

            # 1. Short-term momentum (10-day)
            if 'momentum_10' in df.columns:
                momentum_indicators.append(df['momentum_10'])
                indicator_names.append('momentum_10')

            # 2. Medium-term momentum (20-day)
            if 'momentum_20' in df.columns:
                momentum_indicators.append(df['momentum_20'])
                indicator_names.append('momentum_20')

            # 3. Long-term momentum (50-day)
            if 'momentum_50' in df.columns:
                momentum_indicators.append(df['momentum_50'])
                indicator_names.append('momentum_50')

            # 4. RSI (centered at 0)
            if 'rsi_normalized' in df.columns:
                momentum_indicators.append(df['rsi_normalized'])
                indicator_names.append('rsi_normalized')
            elif 'rsi' in df.columns:
                # Center RSI: (RSI - 50) / 50  → range: -1 to +1
                momentum_indicators.append((df['rsi'] - 50) / 50)
                indicator_names.append('rsi_centered')

            # 5. MACD histogram (momentum divergence)
            if 'macd_divergence' in df.columns:
                # Normalize MACD divergence by recent volatility
                macd_std = df['macd_divergence'].rolling(20).std()
                normalized_macd = np.where(macd_std > 0, df['macd_divergence'] / macd_std, 0)
                momentum_indicators.append(pd.Series(normalized_macd, index=df.index))
                indicator_names.append('macd_normalized')
            elif 'macd_histogram' in df.columns:
                macd_std = df['macd_histogram'].rolling(20).std()
                normalized_macd_hist = np.where(macd_std > 0, df['macd_histogram'] / macd_std, 0)
                momentum_indicators.append(pd.Series(normalized_macd_hist, index=df.index))
                indicator_names.append('macd_hist_normalized')

            # 6. Stochastic K (centered at 50)
            if 'stoch_k' in df.columns:
                momentum_indicators.append((df['stoch_k'] - 50) / 50)
                indicator_names.append('stoch_k_centered')

            # 7. ROC (Rate of Change)
            if 'roc_10' in df.columns:
                momentum_indicators.append(df['roc_10'] / 100)  # Convert from % to decimal
                indicator_names.append('roc_10')
            elif 'roc' in df.columns:
                momentum_indicators.append(df['roc'] / 100)
                indicator_names.append('roc')

            # 8. ADX (trend strength, normalized)
            if 'adx_normalized' in df.columns:
                # ADX shows trend strength (not direction), use with directional momentum
                momentum_indicators.append(df['adx_normalized'])
                indicator_names.append('adx_normalized')
            elif 'adx' in df.columns:
                momentum_indicators.append(df['adx'] / 100)
                indicator_names.append('adx_scaled')

            # 9. Trend strength (directional consistency)
            if 'trend_strength' in df.columns:
                momentum_indicators.append(df['trend_strength'])
                indicator_names.append('trend_strength')

            # 10. Volume ratio (momentum confirmation)
            if 'volume_ratio' in df.columns:
                # Center volume ratio: (ratio - 1) → 0 means average volume
                momentum_indicators.append(df['volume_ratio'] - 1.0)
                indicator_names.append('volume_ratio_centered')

            # Requirement: Need at least 5 indicators for robust composite
            if len(momentum_indicators) < 5:
                self.logger.warning(f"Insufficient indicators for composite: {len(momentum_indicators)}/10 available")
                return df

            self.logger.debug(f"Building composite from {len(momentum_indicators)} indicators: {indicator_names}")

            # Step 2: Calculate MAD-based Z-scores for each indicator (outlier-resistant)
            z_scores = []
            for indicator in momentum_indicators:
                z_score = self._calculate_mad_zscore(indicator)
                z_scores.append(z_score)

            # Step 3: Weight and aggregate Z-scores
            # Equal weighting for simplicity (can be adjusted based on strategy performance)
            weights = np.ones(len(z_scores)) / len(z_scores)

            # Calculate weighted composite Z-score
            composite_z_values = np.zeros(len(df))
            for z_score, weight in zip(z_scores, weights):
                composite_z_values += z_score.fillna(0).values * weight

            df['composite_z'] = composite_z_values

            # Step 4: Calculate composite percentile (0-100 scale)
            # P0 PERF FIX: Use JIT-optimized rolling rank instead of slow Python loop with rankdata
            window = min(252, len(df))  # Up to 1 year of data

            # Vectorized rolling percentile using JIT kernel
            # jit_rolling_rank returns 0-1, so multiply by 100
            df['composite_pct'] = jit_rolling_rank(df['composite_z'].values, window) * 100.0
            df['composite_pct'] = df['composite_pct'].fillna(50.0)

            # Verify composite_pct range is correct
            pct_min, pct_max = df['composite_pct'].min(), df['composite_pct'].max()
            if pct_min < 0 or pct_max > 100:
                self.logger.warning(f"⚠️ composite_pct range [{pct_min:.1f}, {pct_max:.1f}] outside expected [0, 100]")

            # Fill NaN with neutral values
            df['composite_z'] = df['composite_z'].fillna(0.0)
            df['composite_pct'] = df['composite_pct'].fillna(50.0)

            self.logger.debug(f"Composite features created: z_range=[{df['composite_z'].min():.2f}, {df['composite_z'].max():.2f}], "
                            f"pct_range=[{df['composite_pct'].min():.1f}, {df['composite_pct'].max():.1f}]")

        except Exception as e:
            self.logger.error(f"Error creating composite momentum features: {e}")
            # Ensure columns exist with default values
            if 'composite_z' not in df.columns:
                df['composite_z'] = 0.0
            if 'composite_pct' not in df.columns:
                df['composite_pct'] = 50.0

        return df

    def _calculate_mad_zscore(self, series: pd.Series) -> pd.Series:
        """
        Calculate MAD-based Z-score (Median Absolute Deviation)

        More robust than standard Z-score for data with outliers.
        Z-score = (X - median) / (1.4826 * MAD)
        where MAD = median(|X - median|)

        Args:
            series: Pandas Series of indicator values

        Returns:
            Series of MAD-based Z-scores
        """
        try:
            # Use rolling window for adaptive calculation
            window = min(252, len(series))  # Up to 1 year
            
            # PERF: Avoid pandas rolling.apply (very slow). Use jit_utils implementation.
            # If Numba is not installed, njit_conditional returns the pure-Python function,
            # which is still typically faster than pandas apply for large windows.

            z_scores = pd.Series(
                jit_rolling_mad_zscore(series.values, window, min_periods=20),
                index=series.index
            )
            
            return z_scores.fillna(0.0)

        except Exception as e:
            self.logger.warning(f"Error calculating MAD Z-score: {e}, using fallback")
            # Fallback to standard Z-score
            mean = series.rolling(window, min_periods=20).mean()
            std = series.rolling(window, min_periods=20).std()
            z_score = (series - mean) / std.replace(0, 1)  # Avoid division by zero
            return z_score.fillna(0.0)

    def _create_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features with minimal fragmentation (Hotspot 1)"""
        new_columns = {}
        
        # Bollinger Band features
        if 'bb_position' in df.columns:
            if 'bb_middle' in df.columns:
                # Calculate proper z-score: (close - mean) / std
                lookback = 20
                rolling_std = df['close'].rolling(window=lookback, min_periods=5).std()
                mask = rolling_std > 0.001
                zscore = pd.Series(0.0, index=df.index)
                zscore[mask] = (df.loc[mask, 'close'] - df.loc[mask, 'bb_middle']) / rolling_std[mask]
                new_columns['zscore'] = zscore
            else:
                new_columns['zscore'] = (df['bb_position'] - 0.5) * 2
            
            # Use existing bb_width if available from indicators phase
            if 'bb_width' in df.columns:
                try:
                    bbw = pd.to_numeric(df['bb_width'], errors='coerce').fillna(0)
                    new_columns['bb_squeeze'] = (bbw < bbw.rolling(20).quantile(0.2)).astype(int)
                except Exception:
                    new_columns['bb_squeeze'] = 0

        # ATR features - MOVED: atr_percentile and atr_normalized are handled in _create_indicator_features
        # to ensure no duplication and single-pass processing.
        
        # Historical volatility features
        vol_cols = [col for col in df.columns if col.startswith('volatility_')]
        for col in vol_cols:
            period = col.split('_')[1]
            try:
                clean_vol = pd.to_numeric(df[col], errors='coerce').fillna(0)
                rolling_quantile = clean_vol.rolling(60).quantile(0.7)
                new_columns[f'vol_regime_{period}'] = (clean_vol > rolling_quantile.fillna(0)).astype(int)
            except Exception as e:
                self.logger.warning(f"Error calculating volatility regime for {col}: {e}")
                new_columns[f'vol_regime_{period}'] = 0

        # Volatility clustering
        if 'log_return' in df.columns:
            try:
                log_returns_abs = pd.to_numeric(df['log_return'], errors='coerce').abs().fillna(0)
                rolling_quantile = log_returns_abs.rolling(20).quantile(0.8)
                new_columns['vol_clustering'] = (log_returns_abs > rolling_quantile.fillna(0)).astype(int)
            except Exception as e:
                self.logger.warning(f"Error calculating volatility clustering: {e}")
                new_columns['vol_clustering'] = 0
        else:
            new_columns['vol_clustering'] = 0

        # Concatenate once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
            
        return df

    def _create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features with minimal fragmentation (Hotspot 1)"""
        if 'volume' not in df.columns:
            return df
            
        new_columns = {}
        
        # Volume momentum
        new_columns['volume_change'] = df['volume'].pct_change(fill_method=None)
        new_columns['volume_acceleration'] = new_columns['volume_change'].diff()

        # Volume-price relationship
        if 'return_1d' in df.columns:
            new_columns['volume_price_trend'] = new_columns['volume_change'] * df['return_1d']

        # Volume breakouts
        if 'volume_sma' in df.columns:
            new_columns['volume_breakout'] = (df['volume'] > 2 * df['volume_sma']).astype(int)

        # OBV features
        if 'obv' in df.columns:
            new_columns['obv_momentum'] = df['obv'].pct_change(fill_method=None)
            if 'return_1d' in df.columns:
                new_columns['obv_divergence'] = np.sign(df['return_1d']) != np.sign(new_columns['obv_momentum'])

        # Concatenate once to avoid fragmentation
        df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
        return df

    def _create_indicator_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features from technical indicators with minimal fragmentation (Hotspot 1)"""
        new_columns = {}
        
        sma_cols = [col for col in df.columns if col.startswith('sma_')]
        ema_cols = [col for col in df.columns if col.startswith('ema_')]

        # Distance from moving averages
        for col in sma_cols + ema_cols:
            dist_col = f'{col}_distance'
            if dist_col not in df.columns:
                new_columns[dist_col] = (df['close'] - df[col]) / df[col]
            
            above_col = f'{col}_above'
            if above_col not in df.columns:
                new_columns[above_col] = (df['close'] > df[col]).astype(int)

        # Moving average slope
        for col in sma_cols[:2]:
            slope_col = f'{col}_slope'
            if slope_col not in df.columns:
                new_columns[slope_col] = df[col].pct_change(fill_method=None)

        # Golden/Death cross signals
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            if 'golden_cross' not in df.columns:
                new_columns['golden_cross'] = ((df['sma_20'] > df['sma_50']) &
                                              (df['sma_20'].shift(1) <= df['sma_50'].shift(1))).astype(int)
            if 'death_cross' not in df.columns:
                new_columns['death_cross'] = ((df['sma_20'] < df['sma_50']) &
                                             (df['sma_20'].shift(1) >= df['sma_50'].shift(1))).astype(int)

        # Bollinger Bands features
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            # Only add if not already present from technical indicators phase
            if 'bb_width' not in df.columns:
                new_columns['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']
            
            if 'bb_breakout_up' not in df.columns:
                new_columns['bb_breakout_up'] = ((df['close'] > df['bb_upper']) &
                                               (df['close'].shift(1) <= df['bb_upper'].shift(1))).astype(int)
            if 'bb_breakout_down' not in df.columns:
                new_columns['bb_breakout_down'] = ((df['close'] < df['bb_lower']) &
                                                 (df['close'].shift(1) >= df['bb_lower'].shift(1))).astype(int)

        # ATR features
        if 'atr' in df.columns:
            if 'atr_normalized' not in df.columns:
                new_columns['atr_normalized'] = df['atr'] / df['close']
            
            if 'atr_percentile' not in df.columns:
                try:
                    clean_atr = pd.to_numeric(df['atr'], errors='coerce').fillna(0)
                    new_columns['atr_percentile'] = jit_rolling_rank(clean_atr.values, 50)
                except Exception as e:
                    self.logger.warning(f"Error calculating ATR percentile: {e}")
                    new_columns['atr_percentile'] = 0.5

        # Concatenate once
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
            
        return df

    def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create lagged features for temporal patterns.

        Args:
            df: DataFrame with input data.

        Returns:
            DataFrame with lagged features added.
        """
        key_features = ['close', 'return_1d', 'volume_change', 'hl_ratio']

        # Collect all new columns to avoid fragmentation
        new_columns = {}

        for feature in key_features:
            if feature in df.columns:
                for lag in self.config.lag_periods:
                    try:
                        new_columns[f'{feature}_lag_{lag}'] = df[feature].shift(lag)
                    except Exception as e:
                        self.logger.warning(f"Error creating lag feature {feature}_lag_{lag}: {e}")
                        new_columns[f'{feature}_lag_{lag}'] = np.nan

        # Add all columns at once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        return df

    def _create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create rolling features for temporal patterns.
        Optimized with JIT and Bottleneck (Hotspot 1 & 5).
        """
        key_features = ['close', 'return_1d', 'volume_change', 'hl_ratio']
        new_columns = {}

        for feature in key_features:
            if feature in df.columns:
                values = df[feature].values
                for period in self.config.lookback_periods:
                    try:
                        # Consistently use JIT kernels for financial calculation parity (ddof=1)
                        # and proper NaN handling for rolling windows.
                        m, s, sk = jit_rolling_stats(values, period)
                        new_columns[f'{feature}_mean_{period}'] = m
                        new_columns[f'{feature}_std_{period}'] = s
                        
                        # Rank and Skew still use Numba as they aren't in Bottleneck
                        new_columns[f'{feature}_rank_{period}'] = jit_rolling_rank(values, period)
                        
                        # Only compute skew for longer windows to ensure stability
                        if period >= 20:
                            new_columns[f'{feature}_skew_{period}'] = sk

                    except Exception as e:
                        self.logger.warning(f"Error creating rolling feature {feature} for period {period}: {e}")

        # Add all columns at once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        return df

    def _create_cross_sectional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create cross-sectional (relative) features.
        Optimized for performance by minimizing groupby operations and using 
        vectorized transforms (Hotspot 2).
        """
        # Key features for cross-sectional analysis
        cs_features = ['return_1d', 'rsi', 'volume_ratio', 'atr_normalized']
        new_columns = {}
        
        # Check if we actually have multiple symbols to rank
        has_multiple_symbols = False
        if 'symbol' in df.columns and df['symbol'].nunique() > 1:
            has_multiple_symbols = True
            
        if not has_multiple_symbols:
            # Single symbol case: Cross-sectional features are neutral/placeholders
            for feature in cs_features:
                if feature in df.columns:
                    new_columns[f'{feature}_cs_rank'] = 0.5
                    new_columns[f'{feature}_cs_zscore'] = 0.0
                    new_columns[f'{feature}_cs_quintile'] = 3
            if new_columns:
                df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
            return df

        # Multi-symbol case: Institutional-grade optimized path
        grouped = df.groupby('timestamp')

        for feature in cs_features:
            if feature in df.columns:
                try:
                    # PERF: Use .transform with built-in strings is faster than lambda
                    # Cross-sectional rank (normalized to 0-1)
                    new_columns[f'{feature}_cs_rank'] = grouped[feature].rank(pct=True)

                    # Z-score relative to universe - Vectorized (Hotspot 2 fix)
                    means = grouped[feature].transform('mean')
                    stds = grouped[feature].transform('std')
                    
                    # Avoid division by zero and handle infinity
                    zscores = (df[feature] - means) / stds.replace(0, np.nan)
                    new_columns[f'{feature}_cs_zscore'] = zscores.fillna(0.0)

                    # Quintile assignment - Vectorized (Hotspot 2 fix)
                    # Maps 0.0-0.2->1, 0.2-0.4->2, etc.
                    ranks = new_columns[f'{feature}_cs_rank']
                    new_columns[f'{feature}_cs_quintile'] = (ranks * 5).apply(np.ceil).fillna(3).astype(int).clip(1, 5)
                except Exception as e:
                    self.logger.warning(f"Error calculating cross-sectional features for {feature}: {e}")

        # Add all columns at once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        return df

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features using configured method
        CRITICAL: Preserve raw trading indicators for signal generation
        """
        # Identify feature columns (exclude metadata AND core trading indicators)
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']

        # CRITICAL: Preserve core trading indicators that strategies need
        # Use actual column names from indicators engine
        trading_indicators = [
            'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_5', 'ema_9', 'ema_10', 'ema_20', 'ema_21', 'ema_50', 'ema_200',
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_width', 'bb_position',  # Actual BB column names
            'rsi', 'rsi_14', 'rsi_21',  # Include both possible RSI names
            'macd', 'macd_signal', 'macd_histogram',
            'atr', 'atr_14', 'adx', 'adx_14', 'cci', 'cci_20',
            'williams_r', 'williams_r_14',
            'stoch_k', 'stoch_d', 'obv', 'vwap',
            # Additional indicators that might exist
            'momentum', 'roc', 'trix', 'ultimate_oscillator'
        ]

        # Columns to preserve (don't normalize)
        preserve_cols = metadata_cols + trading_indicators

        # Only normalize derived features, not core trading indicators
        feature_cols = [col for col in df.columns
                       if col not in preserve_cols
                       and not col.endswith('_quintile')
                       and not col.startswith('price_')  # Preserve price-based indicators
                       and not col.startswith('return_')]  # Preserve return calculations

        if not feature_cols:
            return df

        # Choose scaler
        if self.config.normalization_method == "standard":
            scaler = StandardScaler()
        elif self.config.normalization_method == "robust":
            scaler = RobustScaler()
        else:  # minmax
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()

        # Fit and transform features
        try:
            # Handle NaN and infinity values
            feature_data = df[feature_cols].copy()

            # Replace infinity values with NaN, then fill with 0
            feature_data = feature_data.replace([np.inf, -np.inf], np.nan)
            feature_data = feature_data.fillna(0)

            # Check for any remaining problematic values (handle different data types)
            try:
                has_inf = np.any(np.isinf(feature_data.select_dtypes(include=[np.number]).values))
                has_nan = np.any(np.isnan(feature_data.select_dtypes(include=[np.number]).values))
            except (TypeError, ValueError):
                # Fallback for mixed data types
                has_inf = False
                has_nan = False
                for col in feature_data.columns:
                    if feature_data[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                        col_data = pd.to_numeric(feature_data[col], errors='coerce')
                        if np.any(np.isinf(col_data)) or np.any(np.isnan(col_data)):
                            has_inf = True
                            has_nan = True
                            break

            if has_inf or has_nan:
                self.logger.warning("Still have inf/nan values after cleaning, using median fill")
                for col in feature_data.columns:
                    if feature_data[col].dtype in ['float64', 'float32']:
                        try:
                            # Convert to numeric and handle _NoValueType
                            clean_col = pd.to_numeric(feature_data[col], errors='coerce')
                            clean_col = clean_col.replace([np.inf, -np.inf], np.nan)
                            median_val = clean_col.median()
                            if pd.isna(median_val) or not np.isfinite(median_val):
                                median_val = 0.0
                            feature_data[col] = feature_data[col].replace([np.inf, -np.inf, np.nan], median_val)
                        except (TypeError, ValueError) as e:
                            self.logger.warning(f"Error calculating median for {col}: {e}, using 0.0")
                            feature_data[col] = feature_data[col].replace([np.inf, -np.inf, np.nan], 0.0)

            # Fit scaler on cleaned data
            scaled_features = scaler.fit_transform(feature_data)

            # Replace original features with scaled versions
            df[feature_cols] = scaled_features

            # Store scaler for future use
            self.scalers['main'] = scaler

            # Data integrity validation after normalization
            self._validate_data_integrity(df)

            self.logger.info(f"Normalized {len(feature_cols)} features using {self.config.normalization_method} scaling")
            self.logger.info(f"Preserved {len(preserve_cols)} core trading indicators")

        except Exception as e:
            self.logger.error(f"Feature normalization failed: {e}")

        return df

    def _validate_data_integrity(self, df: pd.DataFrame):
        """
        Validate data integrity after feature engineering
        CRITICAL: Catch data corruption that could cause trading errors
        """
        try:
            # Check core trading indicators are preserved
            core_indicators = ['close', 'sma_20', 'bb_upper_20', 'bb_lower_20', 'rsi_14']

            for indicator in core_indicators:
                if indicator in df.columns:
                    values = df[indicator].dropna()
                    if len(values) > 0:
                        # Check for reasonable price ranges
                        if indicator in ['close', 'sma_20', 'bb_upper_20', 'bb_lower_20']:
                            try:
                                min_val = values.min()
                                max_val = values.max()

                                # Check if values are numeric and not NaN
                                if pd.isna(min_val) or pd.isna(max_val) or not np.isfinite(min_val) or not np.isfinite(max_val):
                                    self.logger.warning(f"⚠️ Invalid values found in {indicator}, skipping validation")
                                    continue

                                if min_val < 1.0:  # Prices should be > $1
                                    self.logger.error(f"❌ DATA CORRUPTION: {indicator} has values < $1.00 (min: {min_val:.4f})")
                                    raise ValueError(f"Data corruption detected in {indicator}")

                                if max_val > 10000.0:  # Reasonable upper bound
                                    self.logger.warning(f"⚠️ UNUSUAL VALUES: {indicator} has very high values (max: {max_val:.2f})")
                            except (ValueError, TypeError) as e:
                                self.logger.warning(f"⚠️ Error validating {indicator}: {e}, skipping validation")
                                continue

                        # Check RSI is in valid range
                        elif indicator == 'rsi_14':
                            try:
                                min_val = values.min()
                                max_val = values.max()

                                # Check if values are numeric and not NaN
                                if pd.isna(min_val) or pd.isna(max_val) or not np.isfinite(min_val) or not np.isfinite(max_val):
                                    self.logger.warning(f"⚠️ Invalid values found in {indicator}, skipping validation")
                                    continue

                                if min_val < 0 or max_val > 100:
                                    self.logger.error(f"❌ DATA CORRUPTION: RSI out of range [0,100] (range: {min_val:.2f}-{max_val:.2f})")
                                    raise ValueError(f"RSI data corruption detected")
                            except (ValueError, TypeError) as e:
                                self.logger.warning(f"⚠️ Error validating {indicator}: {e}, skipping validation")
                                continue

            # Check for extreme z-score issues
            if 'close' in df.columns and 'sma_20' in df.columns:
                latest_close = df['close'].iloc[-1]
                latest_sma = df['sma_20'].iloc[-1]

                if abs(latest_close - latest_sma) / latest_close > 0.5:  # >50% deviation
                    self.logger.warning(f"⚠️ EXTREME DEVIATION: Close ${latest_close:.2f} vs SMA ${latest_sma:.2f}")

            self.logger.debug("✅ Data integrity validation passed")

        except Exception as e:
            self.logger.error(f"❌ Data integrity validation failed: {e}")
            raise

    def _update_feature_metadata(self, df: pd.DataFrame):
        """Update feature column metadata"""
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        self.feature_columns = [col for col in df.columns if col not in metadata_cols]

        # Identify potential target columns (future returns)
        self.target_columns = [col for col in df.columns if 'return_' in col and '_lag_' not in col]

    def get_feature_importance(self, df: pd.DataFrame, target_col: str = 'return_1d') -> pd.DataFrame:
        """Calculate feature importance using correlation with target"""
        if target_col not in df.columns:
            self.logger.warning(f"Target column {target_col} not found")
            return pd.DataFrame()

        # Calculate correlations
        # Use feature_columns if populated, otherwise derive from df
        if self.feature_columns:
            feature_cols = [col for col in self.feature_columns if col != target_col]
        else:
            # Derive feature columns from DataFrame
            metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            feature_cols = [col for col in df.columns if col not in metadata_cols and col != target_col]

        correlations = []

        for col in feature_cols:
            if col in df.columns:
                corr = df[col].corr(df[target_col])
                correlations.append({
                    'feature': col,
                    'correlation': corr,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0
                })

        if not correlations:
            return pd.DataFrame()

        importance_df = pd.DataFrame(correlations)
        importance_df = importance_df.sort_values('abs_correlation', ascending=False)

        return importance_df

    def select_features(self, df: pd.DataFrame, importance_df: pd.DataFrame) -> pd.DataFrame:
        """Select top features based on importance"""
        if importance_df.empty:
            return df

        # Apply threshold
        selected_features = importance_df[
            importance_df['abs_correlation'] >= self.config.feature_importance_threshold
        ]['feature'].tolist()

        # Apply max features limit
        if self.config.max_features and len(selected_features) > self.config.max_features:
            selected_features = selected_features[:self.config.max_features]

        # Keep metadata columns and selected features
        metadata_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        keep_cols = metadata_cols + selected_features + self.target_columns
        keep_cols = [col for col in keep_cols if col in df.columns]

        result = df[keep_cols].copy()

        self.logger.info(f"Selected {len(selected_features)} features from {len(self.feature_columns)} total")
        return result

    # ========================================
    # STANDARDIZED DATA CONSUMPTION METHODS
    # ========================================

    def process_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for processing features data"""
        return features

    def use_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for using features data (alias)"""
        return self.process_features(features)

    def analyze_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for analyzing features data (alias)"""
        return self.process_features(features)

    def process_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for processing indicators data (consumption interface)"""
        # This component consumes indicators to produce features
        return indicators

    def use_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for using indicators data (consumption interface)"""
        return self.process_indicators(indicators)

    def analyze_indicators(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """Standardized method for analyzing indicators data (consumption interface)"""
        return self.process_indicators(indicators)

    # ========================================
    # STREAMING MODE METHODS (Paper Trading Evolution)
    # ========================================

    def fit_scalers(self, historical_df: pd.DataFrame) -> None:
        """
        Fit scalers on historical data for streaming use.

        Call this offline with 30+ RTH days of data before paper trading.
        The scalers will be used by transform_single() during streaming.

        Args:
            historical_df: DataFrame with features (output of create_features)
        """

        # Identify numeric feature columns (exclude metadata)
        metadata_cols = {'timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'date'}
        feature_cols = [
            col for col in historical_df.columns
            if col not in metadata_cols and historical_df[col].dtype in ['float64', 'float32', 'int64', 'int32']
        ]

        if not feature_cols:
            self.logger.warning("No feature columns found for scaler fitting")
            return

        # Fit scalers based on config
        with self._lock:
            if self.config.normalization_method == 'zscore':
                scaler = StandardScaler()
            else:
                scaler = RobustScaler()

            # Extract feature data, drop NaN rows
            feature_data = historical_df[feature_cols].dropna()

            if len(feature_data) < 100:
                self.logger.warning(f"Only {len(feature_data)} rows for scaler fitting, recommend 1000+")

            # Fit the scaler
            scaler.fit(feature_data)

            self.scalers['main'] = scaler
            self.feature_columns = feature_cols

            self.logger.info(f"Fitted scalers on {len(feature_cols)} features with {len(feature_data)} samples")

    def save_scalers(self, path: str) -> None:
        """
        Save fitted scalers to file for later loading.

        Args:
            path: Path to save scalers (e.g., 'scalers.pkl')
        """
        import pickle

        with self._lock:
            state = {
                'scalers': self.scalers,
                'feature_columns': self.feature_columns,
                'config_normalization': self.config.normalization_method,
            }

            with open(path, 'wb') as f:
                pickle.dump(state, f)

            self.logger.info(f"Saved scalers to {path}")

    def load_scalers(self, path: str) -> None:
        """
        Load pre-fitted scalers from file.

        Args:
            path: Path to saved scalers
        """
        import pickle

        with self._lock:
            with open(path, 'rb') as f:
                state = pickle.load(f)

            self.scalers = state['scalers']
            self.feature_columns = state['feature_columns']

            self.logger.info(f"Loaded scalers from {path} with {len(self.feature_columns)} features")

    def transform_single(self, row: Dict[str, float]) -> Dict[str, float]:
        """
        Transform a single row of indicator/feature values using pre-fitted scalers.

        This is the streaming-mode transform method. NO fitting is performed.
        Scalers must be loaded via load_scalers() before calling this.

        Args:
            row: Dict of feature_name -> raw_value

        Returns:
            Dict of feature_name -> scaled_value

        Raises:
            RuntimeError: If scalers not loaded
        """
        with self._lock:
            if 'main' not in self.scalers:
                raise RuntimeError(
                    "Scalers not fitted/loaded. Call fit_scalers() or load_scalers() first."
                )

            scaler = self.scalers['main']

            # Build feature vector in correct column order
            feature_vector = []
            valid_features = []

            for col in self.feature_columns:
                if col in row:
                    value = row[col]
                    if pd.notna(value) and np.isfinite(value):
                        feature_vector.append(value)
                        valid_features.append(col)
                    else:
                        # Use 0 for missing/invalid (will become mean after scaling)
                        feature_vector.append(0.0)
                        valid_features.append(col)
                else:
                    # Feature not present, use 0
                    feature_vector.append(0.0)
                    valid_features.append(col)

            if not feature_vector:
                return {}

            # Transform
            try:
                scaled = scaler.transform([feature_vector])[0]

                # Build result dict
                result = {}
                for i, col in enumerate(self.feature_columns):
                    result[col] = float(scaled[i])

                return result

            except Exception as e:
                self.logger.error(f"Transform error: {e}")
                return {}

    def get_feature_names(self) -> List[str]:
        """Get list of feature names expected by transform_single()."""
        return list(self.feature_columns)