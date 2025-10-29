#!/usr/bin/env python3
"""
Feature Engineering Module for Core Engine
==========================================

Transforms technical indicators into trading features for signal generation.
Creates normalized, scaled, and cross-sectional features suitable for ML models.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Feature Engineering)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, RobustScaler
import warnings
import threading
import uuid
from datetime import datetime
warnings.filterwarnings('ignore')

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
from ...system.interfaces import ISystemComponent, IRegimeAware, RegimeContext
from core_engine.exceptions import ConfigurationRequiredError

logger = logging.getLogger(__name__)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
from core_engine.config import FeatureConfig

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
        previous_regime = self.current_regime.primary_regime.value if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None
        self.current_regime = new_regime_context
        
        regime_name = new_regime_context.primary_regime.value if hasattr(new_regime_context, 'primary_regime') else str(new_regime_context)
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
            'previous_regime': str(self.current_regime.primary_regime.value) if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None,
            'new_regime': str(regime_context.primary_regime.value) if hasattr(regime_context, 'primary_regime') else 'unknown',
            'adjustments': [],
            'success': True
        }
        
        try:
            regime_name = regime_context.primary_regime.value if hasattr(regime_context, 'primary_regime') else str(regime_context)
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
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create trading features from indicators DataFrame
        
        Args:
            df: DataFrame with indicators (from TechnicalIndicators)
            
        Returns:
            DataFrame with engineered features
        """
        if df.empty:
            return df
        
        # Ensure timestamp column exists (handle both column and index formats)
        df_copy = df.copy()
        if 'timestamp' not in df_copy.columns and df_copy.index.name == 'timestamp':
            df_copy = df_copy.reset_index()
        elif 'timestamp' not in df_copy.columns:
            self.logger.error("DataFrame must have 'timestamp' column or index")
            return df
        
        self.logger.info(f"Creating features for {len(df_copy['symbol'].unique())} symbols")
        
        # Process each symbol separately, then combine
        result_dfs = []
        
        for symbol in df_copy['symbol'].unique():
            symbol_df = df_copy[df_copy['symbol'] == symbol].copy().sort_values('timestamp')
            
            if len(symbol_df) < 10:  # Need minimum data for feature engineering
                self.logger.warning(f"Insufficient data for {symbol}, skipping feature engineering")
                continue
            
            # Create features for this symbol
            symbol_df = self._create_symbol_features(symbol_df)
            result_dfs.append(symbol_df)
        
        if not result_dfs:
            return pd.DataFrame()
        
        # Combine all symbols
        result = pd.concat(result_dfs, ignore_index=True)
        
        # Create cross-sectional features
        if self.config.enable_cross_sectional:
            result = self._create_cross_sectional_features(result)
        
        # Normalize features
        if self.config.use_normalization:
            result = self._normalize_features(result)
        
        # Store feature metadata
        self._update_feature_metadata(result)
        
        self.logger.info(f"Created {len(self.feature_columns)} features for {len(result)} records")
        return result
    
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading features from indicators DataFrame (alias for create_features)
        
        Args:
            df: DataFrame with indicators (from TechnicalIndicators)
            
        Returns:
            DataFrame with engineered features
        """
        return self.create_features(df)
    
    def _create_symbol_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for a single symbol"""
        # Basic price features
        df = self._create_price_features(df)
        
        # Momentum features
        df = self._create_momentum_features(df)
        
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
        """Create price-based features"""
        # Returns at different horizons
        for period in [1, 2, 3, 5, 10]:
            if len(df) > period:
                df[f'return_{period}d'] = df['close'].pct_change(period)
        
        # Log returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # OHLC ratios
        df['hl_ratio'] = (df['high'] - df['low']) / df['close']
        df['oc_ratio'] = (df['open'] - df['close']) / df['close']
        df['body_size'] = np.abs(df['close'] - df['open']) / df['close']
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # Price momentum
        df['price_acceleration'] = df['log_return'].diff()
        
        return df
    
    def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features"""
        # Price momentum features (percentage change over different periods)
        # These are CRITICAL for momentum strategies
        for period in [10, 20, 50]:
            if len(df) > period:
                df[f'momentum_{period}'] = df['close'].pct_change(period)
        
        # Trend strength (based on price consistency)
        # Measures how consistently price moves in one direction
        if len(df) >= 20:
            # Calculate trend strength as the ratio of cumulative return to cumulative absolute return
            returns_20 = df['close'].pct_change().rolling(20)
            cumulative_return = returns_20.sum()
            cumulative_abs_return = returns_20.apply(lambda x: x.abs().sum())
            
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
    
    def _create_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features"""
        # Bollinger Band features
        if 'bb_position' in df.columns:
            df['bb_squeeze'] = (df['bb_width'] < df['bb_width'].rolling(20).quantile(0.2)).astype(int)
            df['bb_breakout_up'] = ((df['close'] > df['bb_upper']) & 
                                   (df['close'].shift(1) <= df['bb_upper'].shift(1))).astype(int)
            df['bb_breakout_down'] = ((df['close'] < df['bb_lower']) & 
                                     (df['close'].shift(1) >= df['bb_lower'].shift(1))).astype(int)
        
        # ATR features
        if 'atr' in df.columns:
            df['atr_normalized'] = df['atr'] / df['close']
            df['atr_percentile'] = df['atr'].rolling(50).rank(pct=True)
        
        # Historical volatility features
        vol_cols = [col for col in df.columns if col.startswith('volatility_')]
        for col in vol_cols:
            period = col.split('_')[1]
            df[f'vol_regime_{period}'] = (df[col] > df[col].rolling(60).quantile(0.7)).astype(int)
        
        # Volatility clustering
        df['vol_clustering'] = (df['log_return'].abs() > 
                               df['log_return'].abs().rolling(20).quantile(0.8)).astype(int)
        
        return df
    
    def _create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        if 'volume' not in df.columns:
            return df
        
        # Volume momentum
        df['volume_change'] = df['volume'].pct_change()
        df['volume_acceleration'] = df['volume_change'].diff()
        
        # Volume-price relationship
        df['volume_price_trend'] = df['volume_change'] * df['return_1d']
        
        # Volume breakouts
        if 'volume_sma' in df.columns:
            df['volume_breakout'] = (df['volume'] > 2 * df['volume_sma']).astype(int)
        
        # OBV features
        if 'obv' in df.columns:
            df['obv_momentum'] = df['obv'].pct_change()
            df['obv_divergence'] = np.sign(df['return_1d']) != np.sign(df['obv_momentum'])
        
        return df
    
    def _create_indicator_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features from technical indicators"""
        # Moving average features
        sma_cols = [col for col in df.columns if col.startswith('sma_')]
        ema_cols = [col for col in df.columns if col.startswith('ema_')]
        
        # Distance from moving averages
        for col in sma_cols + ema_cols:
            df[f'{col}_distance'] = (df['close'] - df[col]) / df[col]
            df[f'{col}_above'] = (df['close'] > df[col]).astype(int)
        
        # Moving average slope
        for col in sma_cols[:2]:  # Only for shorter periods to avoid overfitting
            df[f'{col}_slope'] = df[col].pct_change()
        
        # Golden/Death cross signals
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            df['golden_cross'] = ((df['sma_20'] > df['sma_50']) & 
                                 (df['sma_20'].shift(1) <= df['sma_50'].shift(1))).astype(int)
            df['death_cross'] = ((df['sma_20'] < df['sma_50']) & 
                                (df['sma_20'].shift(1) >= df['sma_50'].shift(1))).astype(int)
        
        return df
    
    def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create lagged features for temporal patterns"""
        # Key features to lag
        key_features = ['return_1d', 'rsi', 'volume_change', 'atr_normalized']

        # Collect all new columns to avoid fragmentation
        new_columns = {}

        for feature in key_features:
            if feature in df.columns:
                for lag in self.config.lag_periods:
                    new_columns[f'{feature}_lag_{lag}'] = df[feature].shift(lag)

        # Add all columns at once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        return df
    
    def _create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create rolling statistics features"""
        base_features = ['return_1d', 'volume_change', 'hl_ratio']

        # Collect all new columns to avoid fragmentation
        new_columns = {}

        for feature in base_features:
            if feature in df.columns:
                for period in self.config.lookback_periods:
                    if len(df) >= period:
                        # Rolling statistics - collect all at once
                        new_columns[f'{feature}_mean_{period}'] = df[feature].rolling(period).mean()
                        new_columns[f'{feature}_std_{period}'] = df[feature].rolling(period).std()
                        new_columns[f'{feature}_skew_{period}'] = df[feature].rolling(period).skew()
                        new_columns[f'{feature}_rank_{period}'] = df[feature].rolling(period).rank(pct=True)

        # Add all columns at once to avoid fragmentation
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        return df
    
    def _create_cross_sectional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create cross-sectional (relative) features"""
        # Group by timestamp for cross-sectional analysis
        grouped = df.groupby('timestamp')

        # Key features for cross-sectional analysis
        cs_features = ['return_1d', 'rsi', 'volume_ratio', 'atr_normalized']

        # Collect all new columns to avoid fragmentation
        new_columns = {}

        for feature in cs_features:
            if feature in df.columns:
                # Cross-sectional rank
                new_columns[f'{feature}_cs_rank'] = grouped[feature].rank(pct=True)

                # Z-score relative to universe
                new_columns[f'{feature}_cs_zscore'] = grouped[feature].transform(
                    lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
                )

                # Quintile assignment
                new_columns[f'{feature}_cs_quintile'] = grouped[feature].transform(
                    lambda x: pd.qcut(x, min(5, len(x.unique())), labels=list(range(1, min(6, len(x.unique())+1))), duplicates='drop') if len(x.unique()) > 1 else 1
                )

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
                        median_val = feature_data[col].replace([np.inf, -np.inf], np.nan).median()
                        if np.isnan(median_val):
                            median_val = 0.0
                        feature_data[col] = feature_data[col].replace([np.inf, -np.inf, np.nan], median_val)
            
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
                            if values.min() < 1.0:  # Prices should be > $1
                                self.logger.error(f"❌ DATA CORRUPTION: {indicator} has values < $1.00 (min: {values.min():.4f})")
                                raise ValueError(f"Data corruption detected in {indicator}")
                            
                            if values.max() > 10000.0:  # Reasonable upper bound
                                self.logger.warning(f"⚠️ UNUSUAL VALUES: {indicator} has very high values (max: {values.max():.2f})")
                        
                        # Check RSI is in valid range
                        elif indicator == 'rsi_14':
                            if values.min() < 0 or values.max() > 100:
                                self.logger.error(f"❌ DATA CORRUPTION: RSI out of range [0,100] (range: {values.min():.2f}-{values.max():.2f})")
                                raise ValueError(f"RSI data corruption detected")
            
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
        feature_cols = [col for col in self.feature_columns if col != target_col]
        correlations = []
        
        for col in feature_cols:
            if col in df.columns:
                corr = df[col].corr(df[target_col])
                correlations.append({
                    'feature': col,
                    'correlation': corr,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0
                })
        
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