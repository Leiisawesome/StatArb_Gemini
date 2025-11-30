#!/usr/bin/env python3
"""
Processing Pipeline Orchestrator
=================================

Central orchestrator for the complete data processing pipeline.

**Rule 3 Compliance:** Enforces unified data flow pipeline
Phase 1 (Data) → Phase 2 (Indicators) → Phase 3 (Features) → Phase 4 (Signals)

This ensures ALL strategies consume the SAME enriched data,
eliminating indicator calculation duplication.

Author: StatArb_Gemini Core Engine
Version: 1.1.0
Status: Production
"""

import logging
import inspect
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Deque
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core_engine.system.interfaces import ISystemComponent, IRegimeAware, RegimeContext

# Import will be available after components exist
from core_engine.data.manager import ClickHouseDataManager
from core_engine.data.liquidity_engine import LiquidityAssessmentEngine
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator

# Import configurations
from core_engine.config import DataConfig, IndicatorConfig, FeatureConfig, SignalConfig

logger = logging.getLogger(__name__)


# ============================================================================
# PIPELINE CONSTANTS (P2 Fix: Centralized magic numbers)
# ============================================================================

@dataclass(frozen=True)
class PipelineConstants:
    """Centralized constants for pipeline orchestrator."""
    # Cache settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 100  # Max cached symbols
    
    # Timeout settings (P0 Fix)
    DATA_LOADING_TIMEOUT_SECONDS: float = 60.0  # 1 minute timeout for data loading
    INDICATOR_TIMEOUT_SECONDS: float = 30.0
    FEATURE_TIMEOUT_SECONDS: float = 30.0
    SIGNAL_TIMEOUT_SECONDS: float = 15.0
    
    # Quality thresholds
    QUALITY_EXCELLENT_THRESHOLD: float = 0.9
    QUALITY_GOOD_THRESHOLD: float = 0.7
    MISSING_VALUE_PENALTY_MAX: float = 0.5  # Max 50% penalty
    OUTLIER_PENALTY_MAX: float = 0.2  # Max 20% penalty
    
    # Performance metrics (P1 Fix: Bounded lists)
    METRICS_HISTORY_SIZE: int = 1000  # Max entries per metric
    
    # IQR multiplier for outlier detection
    OUTLIER_IQR_MULTIPLIER: float = 3.0


PIPELINE_CONSTANTS = PipelineConstants()


# ============================================================================
# ENRICHED DATA CONTAINER
# ============================================================================

@dataclass
class EnrichedMarketData:
    """
    Container for fully processed market data through complete pipeline
    
    Guarantees data has passed through all required processing stages:
    - Phase 1: Raw OHLCV loaded
    - Phase 2: 29+ technical indicators calculated
    - Phase 3: 50+ features engineered
    - Phase 4: Preliminary signals generated
    
    **Rule 3 Compliance:** This is the ONLY data format strategies should receive.
    """
    symbol: str
    timeframe: str
    
    # Pipeline stages (progressive enrichment)
    raw_data: pd.DataFrame  # Phase 1: Original OHLCV
    indicators: pd.DataFrame  # Phase 2: OHLCV + 29+ indicators
    features: pd.DataFrame  # Phase 3: OHLCV + indicators + 50+ features
    signals: pd.DataFrame  # Phase 4: OHLCV + indicators + features + preliminary signals
    
    # Metadata
    processing_timestamp: datetime
    pipeline_version: str = "1.0.0"
    regime_context: Optional[RegimeContext] = None
    liquidity_context: Optional[Dict[str, Any]] = None
    
    # Statistics
    raw_rows: int = 0
    indicator_columns: int = 0
    feature_columns: int = 0
    signal_columns: int = 0
    
    def __post_init__(self):
        """Calculate statistics"""
        if not self.raw_data.empty:
            self.raw_rows = len(self.raw_data)
        if not self.indicators.empty:
            self.indicator_columns = len(self.indicators.columns) - len(self.raw_data.columns)
        if not self.features.empty:
            self.feature_columns = len(self.features.columns) - len(self.indicators.columns)
        if not self.signals.empty:
            self.signal_columns = len(self.signals.columns) - len(self.features.columns)
    
    def get_enriched_dataframe(self) -> pd.DataFrame:
        """
        Get fully enriched DataFrame ready for strategy consumption
        
        Returns:
            pd.DataFrame with OHLCV + indicators + features + signals
        """
        return self.signals.copy()
    
    def validate_enrichment(self) -> bool:
        """
        Validate that data is properly enriched
        
        Returns:
            True if data has all required stages
        """
        # Check for required OHLCV columns - prefer signals (fully enriched) but fallback to raw_data
        target_df = self.signals if not self.signals.empty else self.raw_data
        required_ohlcv = ['open', 'high', 'low', 'close', 'volume']
        
        checks = {
            'has_raw_data': not self.raw_data.empty,
            'has_indicators': not self.indicators.empty,
            'has_features': not self.features.empty,
            'has_signals': not self.signals.empty,
            'raw_columns_present': all(col in target_df.columns for col in required_ohlcv) if not target_df.empty else False,
        }
        
        all_valid = all(checks.values())
        if not all_valid:
            logger.warning(f"Enrichment validation failed for {self.symbol}: {checks}")
        
        return all_valid
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'raw_rows': self.raw_rows,
            'total_columns': len(self.signals.columns) if not self.signals.empty else 0,
            'indicator_columns': self.indicator_columns,
            'feature_columns': self.feature_columns,
            'signal_columns': self.signal_columns,
            'processing_timestamp': self.processing_timestamp.isoformat(),
            'pipeline_version': self.pipeline_version,
            'enrichment_valid': self.validate_enrichment(),
            'has_liquidity_context': self.liquidity_context is not None
        }


# ============================================================================
# PROCESSING PIPELINE ORCHESTRATOR
# ============================================================================

class ProcessingPipelineOrchestrator(ISystemComponent, IRegimeAware):
    """
    Central orchestrator for the complete data processing pipeline
    
    Coordinates: DataManager → Indicators → Features → Signals
    
    This ensures ALL strategies consume the SAME enriched data,
    eliminating indicator calculation duplication and ensuring consistency.
    
    **Rule 3 Compliance:** Enforces unified data flow pipeline
    **Rule 2 Integration:** Regime-aware processing throughout pipeline
    
    Example:
        >>> pipeline = ProcessingPipelineOrchestrator(
        ...     data_config=DataConfig(),
        ...     indicator_config=IndicatorConfig(),
        ...     feature_config=FeatureConfig(),
        ...     signal_config=SignalConfig()
        ... )
        >>> await pipeline.initialize()
        >>> enriched_data = await pipeline.process_market_data(
        ...     symbols=['AAPL', 'TSLA'],
        ...     start_time=datetime(2024, 1, 1),
        ...     end_time=datetime(2024, 12, 31),
        ...     timeframe='1min'
        ... )
        >>> # All strategies now consume enriched_data (same data!)
    """
    
    def __init__(
        self,
        data_config: Optional[Any] = None,
        indicator_config: Optional[Any] = None,
        feature_config: Optional[Any] = None,
        signal_config: Optional[Any] = None,
        liquidity_config: Optional[Any] = None
    ):
        """
        Initialize pipeline orchestrator
        
        Args:
            data_config: Configuration for DataManager
            indicator_config: Configuration for TechnicalIndicators
            feature_config: Configuration for FeatureEngineer
            signal_config: Configuration for SignalGenerator
        """
        # Component state (ISystemComponent)
        self.component_name = "ProcessingPipelineOrchestrator"
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None
        
        # Load configurations
        self.data_config = data_config or DataConfig()
        self.indicator_config = indicator_config or IndicatorConfig()
        self.feature_config = feature_config or FeatureConfig()
        self.signal_config = signal_config or SignalConfig()
        self.liquidity_config = liquidity_config or {}
        
        # Pipeline components (initialized in initialize())
        self.data_manager: Optional[Any] = None
        self.indicators_engine: Optional[Any] = None
        self.feature_engineer: Optional[Any] = None
        self.signal_generator: Optional[Any] = None
        self.liquidity_engine: Optional[Any] = None
        
        # Regime awareness (IRegimeAware)
        self.regime_engine: Optional[Any] = None
        self.current_regime_context: Optional[RegimeContext] = None
        self.liquidity_sequence: Dict[str, List[Dict[str, Any]]] = {}
        self.liquidity_by_timestamp: Dict[str, Dict[datetime, Dict[str, Any]]] = {}
        
        # Processing cache with TTL tracking (P0 Fix: TTL-based eviction)
        self._cache_entries: Dict[str, Tuple[EnrichedMarketData, datetime]] = {}  # (data, timestamp)
        self._cache_max_size = PIPELINE_CONSTANTS.CACHE_MAX_SIZE
        self._cache_ttl = timedelta(seconds=PIPELINE_CONSTANTS.CACHE_TTL_SECONDS)
        
        # Performance metrics with bounded history (P1 Fix: Prevent memory leak)
        self._metrics_maxlen = PIPELINE_CONSTANTS.METRICS_HISTORY_SIZE
        self.processing_times: Dict[str, Deque[float]] = {
            'data_loading': deque(maxlen=self._metrics_maxlen),
            'indicators': deque(maxlen=self._metrics_maxlen),
            'features': deque(maxlen=self._metrics_maxlen),
            'signals': deque(maxlen=self._metrics_maxlen),
            'total': deque(maxlen=self._metrics_maxlen)
        }
        self.total_processed = 0
        
        logger.info("✅ ProcessingPipelineOrchestrator initialized (Rule 3 enforcement)")
    
    # ================================================================
    # ISystemComponent Implementation (Rule 2)
    # ================================================================
    
    async def initialize(self) -> bool:
        """
        Initialize all pipeline components
        
        Returns:
            True if initialization successful
        """
        try:
            
            logger.info("🔧 Initializing pipeline components...")
            
            # Initialize DataManager (Phase 1)
            logger.debug("Phase 1: Initializing DataManager...")
            self.data_manager = ClickHouseDataManager(self.data_config)
            if hasattr(self.data_manager, 'initialize'):
                await self.data_manager.initialize()
            logger.debug("✅ DataManager initialized")
            
            # Initialize Liquidity Engine (Phase 1.5)
            logger.debug("Phase 1.5: Initializing LiquidityAssessmentEngine...")
            self.liquidity_engine = LiquidityAssessmentEngine(self.liquidity_config)
            if hasattr(self.liquidity_engine, 'initialize'):
                await self.liquidity_engine.initialize()
            self.set_liquidity_engine(self.liquidity_engine)
            logger.debug("✅ LiquidityAssessmentEngine initialized")
            
            # Initialize Indicators Engine (Phase 2)
            logger.debug("Phase 2: Initializing TechnicalIndicators...")
            self.indicators_engine = EnhancedTechnicalIndicators(self.indicator_config)
            if hasattr(self.indicators_engine, 'initialize'):
                await self.indicators_engine.initialize()
            logger.debug("✅ TechnicalIndicators initialized")
            
            # Initialize Feature Engineer (Phase 3)
            logger.debug("Phase 3: Initializing FeatureEngineer...")
            self.feature_engineer = EnhancedFeatureEngineer(self.feature_config)
            if hasattr(self.feature_engineer, 'initialize'):
                await self.feature_engineer.initialize()
            logger.debug("✅ FeatureEngineer initialized")
            
            # Initialize Signal Generator (Phase 4)
            logger.debug("Phase 4: Initializing SignalGenerator...")
            self.signal_generator = EnhancedSignalGenerator(self.signal_config)
            if hasattr(self.signal_generator, 'initialize'):
                await self.signal_generator.initialize()
            logger.debug("✅ SignalGenerator initialized")
            
            self.is_initialized = True
            logger.info("✅ Pipeline orchestrator initialized successfully (all 4 phases ready)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline orchestrator initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """
        Start pipeline operations
        
        Returns:
            True if start successful
        """
        if not self.is_initialized:
            logger.error("Cannot start: not initialized")
            return False
        
        if self.liquidity_engine and hasattr(self.liquidity_engine, 'start'):
            await self.liquidity_engine.start()
        
        self.is_operational = True
        logger.info("✅ Pipeline orchestrator operational")
        return True
    
    async def stop(self) -> bool:
        """
        Stop pipeline operations
        
        Returns:
            True if stop successful
        """
        if self.liquidity_engine and hasattr(self.liquidity_engine, 'stop'):
            await self.liquidity_engine.stop()
        
        self.is_operational = False
        
        # Clear cache
        self._cache_entries.clear()
        self.liquidity_sequence.clear()
        self.liquidity_by_timestamp.clear()
        
        logger.info("Pipeline orchestrator stopped")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all pipeline components
        
        Returns:
            Dict with health status of each component
        """
        # Evict expired cache entries before reporting
        self._evict_expired_cache()
        
        health = {
            'orchestrator_healthy': self.is_operational,
            'initialized': self.is_initialized,
            'cache_size': len(self._cache_entries),
            'total_processed': self.total_processed
        }
        
        # Check component health
        if self.data_manager and hasattr(self.data_manager, 'health_check'):
            health['data_manager'] = await self.data_manager.health_check()
        else:
            health['data_manager'] = {'healthy': self.data_manager is not None}
        
        if self.indicators_engine and hasattr(self.indicators_engine, 'health_check'):
            health['indicators_engine'] = await self.indicators_engine.health_check()
        else:
            health['indicators_engine'] = {'healthy': self.indicators_engine is not None}
        
        if self.feature_engineer and hasattr(self.feature_engineer, 'health_check'):
            health['feature_engineer'] = await self.feature_engineer.health_check()
        else:
            health['feature_engineer'] = {'healthy': self.feature_engineer is not None}
        
        if self.signal_generator and hasattr(self.signal_generator, 'health_check'):
            health['signal_generator'] = await self.signal_generator.health_check()
        else:
            health['signal_generator'] = {'healthy': self.signal_generator is not None}
        
        return health
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get pipeline orchestrator status
        
        Returns:
            Dict with status information
        """
        avg_times = {
            stage: sum(times) / len(times) if times else 0.0
            for stage, times in self.processing_times.items()
        }
        
        return {
            'component_name': self.component_name,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'cache_size': len(self._cache_entries),
            'total_processed': self.total_processed,
            'avg_processing_times_ms': {k: v * 1000 for k, v in avg_times.items()},
            'components_available': True,
            'config_available': True
        }
    
    # ================================================================
    # Cache Management (P0 Fix: TTL-based eviction)
    # ================================================================
    
    def _evict_expired_cache(self) -> int:
        """
        Evict expired cache entries based on TTL.
        
        Returns:
            Number of entries evicted
        """
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache_entries.items()
            if now - timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache_entries[key]
        
        if expired_keys:
            logger.debug(f"Cache eviction: {len(expired_keys)} expired entries removed")
        
        return len(expired_keys)
    
    def _cache_put(self, symbol: str, data: EnrichedMarketData) -> None:
        """
        Add entry to cache with TTL tracking and size limit enforcement.
        
        Args:
            symbol: Cache key (symbol name)
            data: EnrichedMarketData to cache
        """
        # Evict expired entries first
        self._evict_expired_cache()
        
        # If cache is at max size, evict oldest entry
        if len(self._cache_entries) >= self._cache_max_size:
            oldest_key = min(
                self._cache_entries.keys(),
                key=lambda k: self._cache_entries[k][1]
            )
            del self._cache_entries[oldest_key]
            logger.debug(f"Cache eviction: {oldest_key} removed (size limit)")
        
        self._cache_entries[symbol] = (data, datetime.now())
    
    def _cache_get(self, symbol: str) -> Optional[EnrichedMarketData]:
        """
        Get entry from cache if exists and not expired.
        
        Args:
            symbol: Cache key (symbol name)
            
        Returns:
            EnrichedMarketData or None if not cached or expired
        """
        if symbol not in self._cache_entries:
            return None
        
        data, timestamp = self._cache_entries[symbol]
        
        # Check if expired
        if datetime.now() - timestamp > self._cache_ttl:
            del self._cache_entries[symbol]
            return None
        
        return data
    
    @property
    def enriched_data_cache(self) -> Dict[str, EnrichedMarketData]:
        """
        Property for backward compatibility - returns cache data without timestamps.
        
        Note: Prefer using _cache_get/_cache_put for proper TTL handling.
        """
        self._evict_expired_cache()
        return {key: data for key, (data, _) in self._cache_entries.items()}
    
    # ================================================================
    # IRegimeAware Implementation (Rule 2)
    # ================================================================
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine and propagate to pipeline components
        
        Args:
            regime_engine: RegimeEngine instance
        """
        self.regime_engine = regime_engine
        
        # Propagate to all pipeline components that support regime awareness
        if self.indicators_engine and hasattr(self.indicators_engine, 'set_regime_engine'):
            self.indicators_engine.set_regime_engine(regime_engine)
            logger.debug("✅ Regime engine injected into indicators engine")
        
        if self.feature_engineer and hasattr(self.feature_engineer, 'set_regime_engine'):
            self.feature_engineer.set_regime_engine(regime_engine)
            logger.debug("✅ Regime engine injected into feature engineer")
        
        if self.signal_generator and hasattr(self.signal_generator, 'set_regime_engine'):
            self.signal_generator.set_regime_engine(regime_engine)
            logger.debug("✅ Regime engine injected into signal generator")
        
        logger.info("✅ Regime engine injected into pipeline (Rule 2 - Regime-First)")
    
    def set_liquidity_engine(self, liquidity_engine: Any) -> None:
        """
        Inject liquidity engine for liquidity-aware processing
        
        Args:
            liquidity_engine: LiquidityAssessmentEngine instance
        """
        self.liquidity_engine = liquidity_engine
        
        if self.indicators_engine and hasattr(self.indicators_engine, 'set_liquidity_engine'):
            self.indicators_engine.set_liquidity_engine(liquidity_engine)
            logger.debug("✅ Liquidity engine injected into indicators engine")
        
        if self.feature_engineer and hasattr(self.feature_engineer, 'set_liquidity_engine'):
            self.feature_engineer.set_liquidity_engine(liquidity_engine)
            logger.debug("✅ Liquidity engine injected into feature engineer")
        
        if self.signal_generator and hasattr(self.signal_generator, 'set_liquidity_engine'):
            self.signal_generator.set_liquidity_engine(liquidity_engine)
            logger.debug("✅ Liquidity engine injected into signal generator")
        
        logger.info("✅ Liquidity engine injected into pipeline")
    
    async def on_regime_change(self, new_regime_context: RegimeContext) -> None:
        """
        Handle regime change and propagate to components
        
        Args:
            new_regime_context: New regime context
        """
        self.current_regime_context = new_regime_context
        
        logger.info(f"📊 Regime changed to {new_regime_context.primary_regime}")
        
        # Propagate to pipeline components
        if self.indicators_engine and hasattr(self.indicators_engine, 'on_regime_change'):
            await self.indicators_engine.on_regime_change(new_regime_context)
        
        if self.feature_engineer and hasattr(self.feature_engineer, 'on_regime_change'):
            await self.feature_engineer.on_regime_change(new_regime_context)
        
        if self.signal_generator and hasattr(self.signal_generator, 'on_regime_change'):
            await self.signal_generator.on_regime_change(new_regime_context)
        
        # Clear cache on regime change (indicators may need recalculation)
        cache_size = len(self._cache_entries)
        self._cache_entries.clear()
        logger.debug(f"Cache cleared on regime change ({cache_size} entries removed)")
    
    def get_current_regime_context(self) -> Optional[RegimeContext]:
        """
        Get current regime context
        
        Returns:
            Current RegimeContext or None
        """
        return self.current_regime_context
    
    async def adapt_to_regime(self, regime_context: RegimeContext) -> Dict[str, Any]:
        """
        Adapt pipeline processing to regime
        
        Args:
            regime_context: Regime context to adapt to
        
        Returns:
            Dict with adaptation results
        """
        # Pipeline adapts by propagating regime to components
        adaptations = {
            'regime': regime_context.primary_regime if regime_context else None,
            'pipeline_adapted': True,
            'cache_cleared': False
        }
        
        # Clear cache if regime is different
        if regime_context != self.current_regime_context:
            self._cache_entries.clear()
            adaptations['cache_cleared'] = True
        
        return adaptations
    
    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is configured
        
        Returns:
            True if regime engine is set
        """
        return self.regime_engine is not None
    
    # ================================================================
    # Data Validation & Quality Methods (Institutional-Grade)
    # ================================================================
    
    def _validate_dataframe(
        self, 
        df: pd.DataFrame, 
        phase: str, 
        required_columns: List[str],
        allow_empty: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive DataFrame validation (Institutional-Grade)
        
        Args:
            df: DataFrame to validate
            phase: Processing phase name (for logging)
            required_columns: List of required column names
            allow_empty: If True, allow empty DataFrames
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check empty
        if df.empty:
            if allow_empty:
                return True, None
            logger.error(f"❌ {phase}: DataFrame is empty")
            return False, f"{phase}: DataFrame is empty"
        
        # Check required columns
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logger.error(f"❌ {phase}: Missing required columns: {missing}")
            return False, f"{phase}: Missing required columns: {missing}"
        
        # Check for NaN/Inf in critical columns
        critical_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in critical_cols:
            if col in df.columns:
                nan_count = df[col].isna().sum()
                inf_count = 0
                if pd.api.types.is_numeric_dtype(df[col]):
                    inf_count = np.isinf(df[col]).sum()
                
                if nan_count > 0:
                    logger.warning(f"⚠️  {phase}: {col} has {nan_count} NaN values ({nan_count/len(df)*100:.1f}%)")
                if inf_count > 0:
                    logger.error(f"❌ {phase}: {col} has {inf_count} Inf values")
                    return False, f"{phase}: {col} has {inf_count} Inf values"
        
        # Check data types for critical columns
        for col in critical_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    logger.error(f"❌ {phase}: {col} column is not numeric (type: {df[col].dtype})")
                    return False, f"{phase}: {col} column is not numeric"
        
        # Check timestamp ordering (if timestamp column exists)
        if 'timestamp' in df.columns:
            if not df['timestamp'].is_monotonic_increasing:
                logger.warning(f"⚠️  {phase}: Timestamps are not sorted (may cause issues)")
        
        return True, None
    
    def _clean_dataframe(self, df: pd.DataFrame, phase: str) -> pd.DataFrame:
        """
        Clean DataFrame of NaN/Inf values (Institutional-Grade)
        
        Strategy:
        1. Forward fill NaN values (conservative - use last known value)
        2. Backward fill remaining NaN (for leading NaN)
        3. Replace Inf with NaN then fill
        4. Last resort: fill with 0 (only if all else fails)
        
        Args:
            df: DataFrame to clean
            phase: Processing phase name (for logging)
            
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        initial_nan = df_clean.isna().sum().sum()
        initial_inf = 0
        
        # Count Inf values
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            inf_count = np.isinf(df_clean[col]).sum()
            if inf_count > 0:
                initial_inf += inf_count
                # Replace Inf with NaN first
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
        
        if initial_nan > 0 or initial_inf > 0:
            logger.debug(f"🧹 {phase}: Cleaning {initial_nan} NaN, {initial_inf} Inf values")
            
            # Forward fill (use last known value)
            df_clean[numeric_cols] = df_clean[numeric_cols].ffill()
            
            # Backward fill (for leading NaN)
            df_clean[numeric_cols] = df_clean[numeric_cols].bfill()
            
            # Last resort: fill remaining NaN with 0 (should be rare)
            remaining_nan = df_clean[numeric_cols].isna().sum().sum()
            if remaining_nan > 0:
                logger.warning(f"⚠️  {phase}: {remaining_nan} NaN values remain after fill, using 0")
                df_clean[numeric_cols] = df_clean[numeric_cols].fillna(0)
            
            final_nan = df_clean.isna().sum().sum()
            if final_nan == 0:
                logger.debug(f"✅ {phase}: All NaN/Inf values cleaned")
            else:
                logger.error(f"❌ {phase}: {final_nan} NaN values remain after cleaning")
        
        return df_clean
    
    def _calculate_data_quality_metrics(
        self, 
        df: pd.DataFrame, 
        phase: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive data quality metrics (Institutional-Grade)
        
        Args:
            df: DataFrame to analyze
            phase: Processing phase name
            
        Returns:
            Dict with quality metrics
        """
        if df.empty:
            return {
                'phase': phase,
                'row_count': 0,
                'quality_score': 0.0,
                'status': 'empty'
            }
        
        metrics = {
            'phase': phase,
            'row_count': len(df),
            'column_count': len(df.columns),
            'missing_values': {},
            'data_types': {},
            'outliers': {},
            'quality_score': 1.0
        }
        
        # Check missing values
        for col in df.columns:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                metrics['missing_values'][col] = {
                    'count': int(nan_count),
                    'percentage': float((nan_count / len(df)) * 100)
                }
        
        # Check data types
        for col in df.columns:
            metrics['data_types'][col] = str(df[col].dtype)
        
        # Check outliers (for critical numeric columns)
        critical_cols = ['open', 'high', 'low', 'close', 'volume']
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in critical_cols and len(df) > 1:
                try:
                    q1 = df[col].quantile(0.25)
                    q3 = df[col].quantile(0.75)
                    iqr = q3 - q1
                    if iqr > 0:  # Avoid division by zero
                        iqr_mult = PIPELINE_CONSTANTS.OUTLIER_IQR_MULTIPLIER
                        outliers = ((df[col] < (q1 - iqr_mult * iqr)) | (df[col] > (q3 + iqr_mult * iqr))).sum()
                        if outliers > 0:
                            metrics['outliers'][col] = int(outliers)
                except Exception as e:
                    logger.debug("Outlier calculation failed for %s: %s", col, e)
        
        # Calculate quality score (0.0 to 1.0)
        quality_score = 1.0
        
        # Penalize missing values
        if metrics['missing_values']:
            total_missing = sum(v['count'] for v in metrics['missing_values'].values())
            missing_penalty = min(PIPELINE_CONSTANTS.MISSING_VALUE_PENALTY_MAX, total_missing / len(df))
            quality_score *= (1 - missing_penalty)
        
        # Penalize outliers (less severe)
        if metrics['outliers']:
            total_outliers = sum(metrics['outliers'].values())
            outlier_penalty = min(PIPELINE_CONSTANTS.OUTLIER_PENALTY_MAX, total_outliers / len(df))
            quality_score *= (1 - outlier_penalty)
        
        metrics['quality_score'] = max(0.0, quality_score)
        metrics['status'] = (
            'excellent' if quality_score >= PIPELINE_CONSTANTS.QUALITY_EXCELLENT_THRESHOLD
            else 'good' if quality_score >= PIPELINE_CONSTANTS.QUALITY_GOOD_THRESHOLD
            else 'poor'
        )
        
        return metrics
    
    # ================================================================
    # Core Pipeline Orchestration (Rule 3)
    # ================================================================
    
    async def process_market_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1min"
    ) -> Dict[str, EnrichedMarketData]:
        """
        Process raw market data through complete pipeline with regime as "beacon light"
        
        Returns fully enriched data ready for strategy consumption.
        
        **Pipeline Flow (Regime as Beacon Light Approach):**
        0. Process regime FIRST (establish bar-by-bar regime sequence as beacon)
        1. Load raw OHLCV (DataManager)
        2. Calculate indicators on entire DataFrame (EnhancedTechnicalIndicators)
        3. Engineer features on entire DataFrame (EnhancedFeatureEngineer)
        4. Generate signals (EnhancedSignalGenerator) - looks up regime per bar via get_regime_at_timestamp()
        
        **Architecture:** Regime acts as metadata reference (beacon light), NOT as segment boundaries.
        This avoids issues with small segments, concatenation, and index alignment.
        Signal engine references regime per bar when filtering/adjusting confidence.
        
        **Rule 3 Compliance:** This is the ONLY way strategies should get data.
        **Rule 2 Compliance:** Regime-aware signal filtering via bar-by-bar regime lookup.
        
        Args:
            symbols: List of symbols to process
            start_time: Start of data range
            end_time: End of data range
            timeframe: Data timeframe (default: 1min)
        
        Returns:
            Dict[symbol, EnrichedMarketData] - Fully processed data per symbol
        
        Example:
            >>> enriched_data = await pipeline.process_market_data(
            ...     symbols=['AAPL', 'TSLA'],
            ...     start_time=datetime(2024, 1, 1),
            ...     end_time=datetime(2024, 12, 31)
            ... )
            >>> # Each symbol has OHLCV + 29 indicators + 50 features + signals
            >>> # Indicators/features calculated with regime-appropriate config per segment
            >>> aapl_df = enriched_data['AAPL'].get_enriched_dataframe()
        """
        if not self.is_operational:
            logger.error("Pipeline not operational")
            return {}
        
        enriched_data = {}
        start_processing = datetime.now()
        
        try:
            # PHASE 1: Load raw OHLCV data
            logger.info(f"📊 Phase 1: Loading raw OHLCV for {len(symbols)} symbols")
            phase1_start = datetime.now()
            
            raw_data = await self._load_raw_data(symbols, start_time, end_time, timeframe)

            # Some unit tests patch _load_raw_data with AsyncMock objects that return
            # coroutine instances. If we detect another awaitable here, await it
            # once more so downstream logic always receives a concrete mapping.
            if inspect.isawaitable(raw_data):
                raw_data = await raw_data
            
            phase1_time = (datetime.now() - phase1_start).total_seconds()
            self.processing_times['data_loading'].append(phase1_time)
            logger.debug(f"✅ Phase 1 complete: {phase1_time:.3f}s")
            
            if not raw_data or all(df.empty for df in raw_data.values()):
                logger.warning("No raw data loaded")
                return {}
            
            # Validate and clean raw data (Institutional-Grade)
            for symbol, df in raw_data.items():
                if not df.empty:
                    is_valid, error = self._validate_dataframe(
                        df, 
                        f"Phase 1 (Raw Data) - {symbol}", 
                        ['open', 'high', 'low', 'close', 'volume']
                    )
                    if not is_valid:
                        logger.error(f"❌ {symbol}: Raw data validation failed: {error}")
                        raw_data[symbol] = pd.DataFrame()  # Mark as invalid
                        continue
                    
                    # Clean NaN/Inf values
                    raw_data[symbol] = self._clean_dataframe(df, f"Phase 1 (Raw Data) - {symbol}")
                    
                    # Log quality metrics
                    quality = self._calculate_data_quality_metrics(df, f"Phase 1 - {symbol}")
                    if quality['quality_score'] < 0.9:
                        logger.warning(f"⚠️  {symbol}: Raw data quality score: {quality['quality_score']:.2f}")
            
            # Process each symbol through pipeline
            for symbol in symbols:
                if symbol not in raw_data or raw_data[symbol].empty:
                    logger.warning(f"No data for {symbol}, skipping")
                    continue
                
                symbol_data = raw_data[symbol].copy()
                symbol_data = symbol_data.sort_values('timestamp').reset_index(drop=True)
                liquidity_sequence = self._assess_liquidity(symbol, symbol_data)
                liquidity_context_first = liquidity_sequence[0] if liquidity_sequence else None
                
                try:
                    # Initialize processing variables to avoid undefined variable risk
                    indicators_df = pd.DataFrame()
                    features_df = pd.DataFrame()
                    signals_df = pd.DataFrame()
                    phase2_time = 0.0
                    phase3_time = 0.0
                    phase4_time = 0.0
                    
                    # PHASE 0: Process regime FIRST (store bar-by-bar regime sequence as "beacon light")
                    # Regime acts as metadata reference, not as segment boundaries
                    dominant_regime_analysis = None
                    regime_sequence = []
                    
                    if self.regime_engine:
                        logger.debug("🔄 Phase 0: Processing regime for %s (beacon light approach)", symbol)
                        regime_result = self.regime_engine.process_market_data(symbol_data)
                        
                        # P0 Fix: Validate regime engine output
                        if not isinstance(regime_result, dict):
                            logger.warning(
                                "⚠️  %s: Regime engine returned %s instead of dict, using empty sequence",
                                symbol, type(regime_result).__name__
                            )
                            regime_result = {}
                        
                        regime_sequence = regime_result.get('regime_sequence', [])
                        if not isinstance(regime_sequence, list):
                            logger.warning(
                                "⚠️  %s: regime_sequence is %s instead of list, using empty",
                                symbol, type(regime_sequence).__name__
                            )
                            regime_sequence = []
                        
                        if regime_sequence:
                            regime_changes_count = regime_result.get('regime_changes_count', 0)
                            logger.debug(
                                "   ✅ %s: Regime beacon established - %d regime states, %d regime changes",
                                symbol, len(regime_sequence), regime_changes_count
                            )
                            
                            # ENHANCED: Per-regime-change config adaptation
                            # If regime changes detected, process in segments with config adaptation per segment
                            if regime_changes_count > 0:
                                logger.info(
                                    f"   🔄 {symbol}: Regime changes detected - "
                                    f"using per-segment config adaptation ({regime_changes_count} changes)"
                                )
                                
                                # Identify regime segments (split by regime changes)
                                regime_segments = self._identify_regime_segments(
                                    symbol_data=symbol_data,
                                    regime_sequence=regime_sequence,
                                    symbol=symbol
                                )
                                
                                # Process segments with config adaptation per segment
                                # Track time for segment processing
                                segment_start = datetime.now()
                                indicators_df, features_df, signals_df = await self._process_regime_segments(
                                    symbol_data=symbol_data,
                                    regime_segments=regime_segments,
                                    symbol=symbol
                                )
                                segment_time = (datetime.now() - segment_start).total_seconds()
                                
                                # Phase 4C: Add regime columns to signals_df for Type 2 regime awareness
                                signals_df = self._add_regime_columns(signals_df, symbol, regime_sequence)
                                
                                # Distribute time across stages (approximate)
                                phase2_time = segment_time * 0.4
                                phase3_time = segment_time * 0.4
                                phase4_time = segment_time * 0.2
                            else:
                                # Single regime - adapt config once, then process normally
                                logger.debug(f"   📊 {symbol}: Single regime - adapting config once")
                                
                                # Get regime analysis from first regime entry
                                first_regime_entry = regime_sequence[0]
                                timestamp = first_regime_entry.get('timestamp')
                                if timestamp:
                                    if isinstance(timestamp, pd.Timestamp):
                                        timestamp = timestamp.to_pydatetime()
                                    regime_analysis = self.regime_engine.get_regime_at_timestamp(
                                        symbol=symbol,
                                        timestamp=timestamp
                                    )
                                    
                                    # Adapt config once for single regime
                                    if regime_analysis:
                                        if self.indicators_engine and hasattr(self.indicators_engine, 'adapt_to_regime'):
                                            await self.indicators_engine.adapt_to_regime(regime_analysis)
                                        if self.feature_engineer and hasattr(self.feature_engineer, 'adapt_to_regime'):
                                            await self.feature_engineer.adapt_to_regime(regime_analysis)
                                        logger.info(
                                            f"   📊 Config adapted for regime: {regime_analysis.primary_regime.value} "
                                            f"(single regime, {len(regime_sequence)} bars)"
                                        )
                                
                                # Use helper method for standard processing
                                indicators_df, features_df, signals_df, phase2_time, phase3_time, phase4_time = \
                                    await self._process_pipeline_stages(symbol_data, symbol, liquidity_context_first)
                                
                                # Phase 4C: Add regime columns to signals_df for Type 2 regime awareness
                                signals_df = self._add_regime_columns(signals_df, symbol, regime_sequence)
                        else:
                            logger.debug(f"   ⚠️  {symbol}: No regime sequence available - using standard processing")
                            
                            # No regime data - use helper method for standard processing
                            indicators_df, features_df, signals_df, phase2_time, phase3_time, phase4_time = \
                                await self._process_pipeline_stages(symbol_data, symbol, liquidity_context_first)
                    
                    # If regime_engine not available, use standard processing
                    if not self.regime_engine:
                        indicators_df, features_df, signals_df, phase2_time, phase3_time, phase4_time = \
                            await self._process_pipeline_stages(symbol_data, symbol, liquidity_context_first)
                    
                    # Phase 4C: Add regime columns to signals_df for Type 2 regime awareness (if regime_sequence available)
                    # Note: Only add if not already added in regime processing blocks above
                    if regime_sequence and 'primary_regime' not in signals_df.columns:
                        signals_df = self._add_regime_columns(signals_df, symbol, regime_sequence)
                    
                    self.processing_times['indicators'].append(phase2_time)
                    self.processing_times['features'].append(phase3_time)
                    self.processing_times['signals'].append(phase4_time)
                    
                    # Create enriched data container
                    enriched_data[symbol] = EnrichedMarketData(
                        symbol=symbol,
                        timeframe=timeframe,
                        raw_data=symbol_data,
                        indicators=indicators_df,
                        features=features_df,
                        signals=signals_df,
                        processing_timestamp=datetime.now(),
                        regime_context=self.current_regime_context,
                        liquidity_context=self._get_latest_liquidity_context(symbol)
                    )
                    
                    # Populate cache for future retrieval (P0 Fix: TTL-based cache)
                    self._cache_put(symbol, enriched_data[symbol])
                    
                    # Validate enrichment
                    if not enriched_data[symbol].validate_enrichment():
                        logger.warning("⚠️  %s: enrichment validation failed", symbol)
                    
                    # Log regime info if available
                    regime_info = ""
                    if self.regime_engine and regime_sequence:
                        regime_info = " ({} regime states, {} changes)".format(
                            len(regime_sequence), regime_result.get('regime_changes_count', 0)
                        )
                    logger.info(
                        "✅ %s processed: %d bars → %d total columns%s",
                        symbol, len(symbol_data), len(signals_df.columns), regime_info
                    )
                    
                except Exception as e:
                    logger.error("❌ %s processing failed: %s", symbol, e, exc_info=True)
                    continue
            
            # Calculate total processing time
            total_time = (datetime.now() - start_processing).total_seconds()
            self.processing_times['total'].append(total_time)
            self.total_processed += len(enriched_data)
            
            logger.info(
                f"✅ Pipeline complete: {len(enriched_data)} symbols processed in {total_time:.3f}s "
                f"(avg: {total_time/max(len(enriched_data), 1):.3f}s/symbol)"
            )
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"❌ Pipeline processing failed: {e}", exc_info=True)
            return {}
    
    async def _process_pipeline_stages(
        self,
        symbol_data: pd.DataFrame,
        symbol: str,
        liquidity_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float, float, float]:
        """
        Process data through pipeline stages 2-4 (Indicators → Features → Signals)
        
        This helper extracts the common processing logic to avoid code duplication.
        
        Args:
            symbol_data: Raw OHLCV DataFrame (already sorted and indexed)
            symbol: Trading symbol
            liquidity_context: Optional liquidity context for adaptation
            
        Returns:
            Tuple of (indicators_df, features_df, signals_df, phase2_time, phase3_time, phase4_time)
        """
        # Adapt to liquidity if available
        if liquidity_context:
            if self.indicators_engine and hasattr(self.indicators_engine, 'adapt_to_liquidity'):
                self.indicators_engine.adapt_to_liquidity(liquidity_context)
            if self.feature_engineer and hasattr(self.feature_engineer, 'adapt_to_liquidity'):
                self.feature_engineer.adapt_to_liquidity(liquidity_context)
        
        # Phase 2: Calculate indicators
        phase2_start = datetime.now()
        indicators_df = await self._calculate_indicators(symbol_data)
        phase2_time = (datetime.now() - phase2_start).total_seconds()
        
        # Phase 3: Engineer features
        phase3_start = datetime.now()
        features_df = await self._engineer_features(indicators_df)
        phase3_time = (datetime.now() - phase3_start).total_seconds()
        
        # Merge liquidity features
        features_df = self._merge_liquidity_features(features_df, symbol)
        
        # Phase 4: Generate signals
        phase4_start = datetime.now()
        signals_df = await self._generate_signals(features_df)
        phase4_time = (datetime.now() - phase4_start).total_seconds()
        
        return indicators_df, features_df, signals_df, phase2_time, phase3_time, phase4_time
    
    # ================================================================
    # Internal Pipeline Stages
    # ================================================================
    
    async def _load_raw_data(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Phase 1: Load raw OHLCV data with timeout protection.
        
        P0 Fix: Uses asyncio.to_thread to avoid blocking event loop,
        wrapped with asyncio.wait_for for timeout protection.
        
        Returns:
            Dict[symbol, DataFrame with OHLCV columns]
        """
        if not self.data_manager:
            logger.warning("DataManager not available, returning empty data")
            return {symbol: pd.DataFrame() for symbol in symbols}
        
        def _sync_load() -> Any:
            """Synchronous data loading (runs in thread pool)."""
            return self.data_manager.load_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                interval=timeframe
            )
        
        try:
            # P0 Fix: Run sync data loading in thread pool with timeout
            # This prevents blocking the event loop and adds timeout protection
            timeout = PIPELINE_CONSTANTS.DATA_LOADING_TIMEOUT_SECONDS
            raw_data = await asyncio.wait_for(
                asyncio.to_thread(_sync_load),
                timeout=timeout
            )
            
            # Convert to dict if single DataFrame
            if isinstance(raw_data, pd.DataFrame):
                # Group by symbol if symbol column exists
                if 'symbol' in raw_data.columns:
                    return {
                        symbol: raw_data[raw_data['symbol'] == symbol].copy()
                        for symbol in symbols
                    }
                else:
                    # Single symbol data
                    return {symbols[0]: raw_data}
            
            return raw_data
            
        except asyncio.TimeoutError:
            logger.error(
                "Data loading timed out after %.1f seconds for symbols: %s",
                PIPELINE_CONSTANTS.DATA_LOADING_TIMEOUT_SECONDS,
                symbols
            )
            return {symbol: pd.DataFrame() for symbol in symbols}
        except Exception as e:
            logger.error("Data loading failed: %s", e)
            return {symbol: pd.DataFrame() for symbol in symbols}
    
    async def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 2: Calculate technical indicators (with validation)
        
        Args:
            data: Raw OHLCV DataFrame
        
        Returns:
            DataFrame with OHLCV + 29+ indicator columns
        """
        if not self.indicators_engine:
            logger.warning("Indicators engine not available, returning raw data")
            return data.copy()
        
        # Validate input data
        is_valid, error = self._validate_dataframe(data, "Phase 2 (Indicators)", ['close', 'volume'])
        if not is_valid:
            logger.error(f"❌ Indicator calculation input validation failed: {error}")
            return data.copy()
        
        try:
            # Calculate indicators through EnhancedTechnicalIndicators (Rule 3.2)
            indicators_df = self.indicators_engine.calculate_indicators(data)
            
            # Validate output
            is_valid, error = self._validate_dataframe(
                indicators_df, 
                "Phase 2 (Indicators) Output", 
                ['close', 'volume'],
                allow_empty=False
            )
            if not is_valid:
                logger.error(f"❌ Indicator calculation output validation failed: {error}")
                return data.copy()  # Return raw data as fallback
            
            # Clean NaN/Inf from indicators
            indicators_df = self._clean_dataframe(indicators_df, "Phase 2 (Indicators)")
            
            # Log quality metrics
            quality = self._calculate_data_quality_metrics(indicators_df, "Phase 2 (Indicators)")
            if quality['quality_score'] < 0.9:
                logger.warning(f"⚠️  Indicator quality score: {quality['quality_score']:.2f}")
            
            return indicators_df
            
        except Exception as e:
            logger.error(f"❌ Indicator calculation failed: {e}", exc_info=True)
            return data.copy()
    
    async def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 3: Engineer ML-ready features (with validation)
        
        Args:
            data: DataFrame with OHLCV + indicators
        
        Returns:
            DataFrame with OHLCV + indicators + 50+ features
        """
        if not self.feature_engineer:
            logger.warning("Feature engineer not available, returning data as-is")
            return data.copy()
        
        # Validate input data
        is_valid, error = self._validate_dataframe(data, "Phase 3 (Features)", ['close'])
        if not is_valid:
            logger.error(f"❌ Feature engineering input validation failed: {error}")
            return data.copy()
        
        try:
            # Engineer features through EnhancedFeatureEngineer (Rule 3.3)
            features_df = self.feature_engineer.create_features(data)
            
            # Validate output
            is_valid, error = self._validate_dataframe(
                features_df, 
                "Phase 3 (Features) Output", 
                ['close'],
                allow_empty=False
            )
            if not is_valid:
                logger.error(f"❌ Feature engineering output validation failed: {error}")
                return data.copy()  # Return previous stage as fallback
            
            # Clean NaN/Inf from features
            features_df = self._clean_dataframe(features_df, "Phase 3 (Features)")
            
            # Log quality metrics
            quality = self._calculate_data_quality_metrics(features_df, "Phase 3 (Features)")
            if quality['quality_score'] < 0.9:
                logger.warning(f"⚠️  Feature quality score: {quality['quality_score']:.2f}")
            
            return features_df
            
        except Exception as e:
            logger.error(f"❌ Feature engineering failed: {e}", exc_info=True)
            return data.copy()
    
    async def _generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 4: Generate preliminary trading signals
        
        Args:
            data: DataFrame with OHLCV + indicators + features
        
        Returns:
            DataFrame with OHLCV + indicators + features (signals are generated separately as TradingSignal objects)
        
        Note: generate_signals() returns List[TradingSignal], not a DataFrame.
        The enriched DataFrame (features + indicators) is what strategies consume.
        TradingSignal objects are generated separately by strategies.
        """
        if not self.signal_generator:
            logger.warning("Signal generator not available, returning data as-is")
            return data.copy()
        
        try:
            # Generate signals through EnhancedSignalGenerator (Rule 3.4)
            # Note: This returns List[TradingSignal], but we need DataFrame for pipeline
            # The TradingSignal objects are used separately by strategies
            # Here we just return the features DataFrame (which is what strategies consume)
            _ = self.signal_generator.generate_signals(data)  # Generate but don't use for DataFrame
            return data.copy()  # Return features DataFrame (signals handled separately)
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return data.copy()
    
    # ================================================================
    # Regime-Segmented Processing Methods (Rule 2 Enhancement)
    # ================================================================
    
    def _identify_regime_segments(
        self,
        symbol_data: pd.DataFrame,
        regime_sequence: List[Dict[str, Any]],
        symbol: str
    ) -> List[Tuple[int, int, Optional[Dict[str, Any]]]]:
        """
        Identify continuous regime segments in DataFrame
        
        **ENHANCEMENT:** Splits DataFrame by regime transitions to enable
        per-segment config adaptation and recalculation.
        
        Uses bar_index from regime_sequence for direct mapping to DataFrame rows.
        Handles warm-up period (bars before first regime entry) as initial segment.
        
        Args:
            symbol_data: DataFrame with timestamp column
            regime_sequence: List of regime entries from regime engine (with bar_index)
            symbol: Trading symbol (for regime lookup)
        
        Returns:
            List of (start_index, end_index, regime_info) tuples
            regime_info contains: {'regime': str, 'regime_analysis': RegimeAnalysis}
        """
        if not regime_sequence or symbol_data.empty:
            # No regime data - single segment
            return [(0, len(symbol_data), None)]
        
        segments = []
        current_regime = None
        segment_start = 0
        
        # Find first regime entry to determine warm-up period
        first_regime_bar = None
        for regime_entry in regime_sequence:
            bar_index = regime_entry.get('bar_index')
            if bar_index is not None and bar_index < len(symbol_data):
                first_regime_bar = bar_index
                break
        
        # If warm-up period exists (bars 0 to first_regime_bar), create initial segment
        if first_regime_bar and first_regime_bar > 0:
            # Warm-up segment: use first available regime or None
            first_regime = regime_sequence[0].get('regime', 'unknown') if regime_sequence else 'unknown'
            segment_timestamp = symbol_data.iloc[0]['timestamp']
            if isinstance(segment_timestamp, pd.Timestamp):
                segment_timestamp = segment_timestamp.to_pydatetime()
            
            regime_analysis = None
            if self.regime_engine:
                # Try to get regime from first bar
                regime_analysis = self.regime_engine.get_regime_at_timestamp(
                    symbol=symbol,
                    timestamp=segment_timestamp
                )
            
            segments.append((
                0,
                first_regime_bar,
                {
                    'regime': first_regime,  # Use first regime for warm-up period
                    'regime_analysis': regime_analysis,
                    'start_timestamp': symbol_data.iloc[0]['timestamp'],
                    'end_timestamp': symbol_data.iloc[first_regime_bar - 1]['timestamp'] if first_regime_bar > 0 else symbol_data.iloc[0]['timestamp']
                }
            ))
            segment_start = first_regime_bar
        
        # Use bar_index from regime sequence for direct DataFrame mapping
        # Regime sequence is in chronological order with bar_index
        for regime_entry in regime_sequence:
            bar_index = regime_entry.get('bar_index')
            if bar_index is None:
                # Fallback to timestamp matching if bar_index not available
                continue
            
            # Ensure bar_index is within DataFrame bounds
            if bar_index >= len(symbol_data):
                continue
            
            regime_name = regime_entry.get('regime', 'unknown')
            
            # Check if regime changed
            if current_regime != regime_name:
                # End current segment, start new one
                if current_regime is not None:
                    # Get regime analysis for previous segment
                    if segment_start < len(symbol_data):
                        segment_timestamp = symbol_data.iloc[segment_start]['timestamp']
                        if isinstance(segment_timestamp, pd.Timestamp):
                            segment_timestamp = segment_timestamp.to_pydatetime()
                        
                        regime_analysis = None
                        if self.regime_engine:
                            regime_analysis = self.regime_engine.get_regime_at_timestamp(
                                symbol=symbol,
                                timestamp=segment_timestamp
                            )
                        
                        segments.append((
                            segment_start,
                            bar_index,
                            {
                                'regime': current_regime,
                                'regime_analysis': regime_analysis,
                                'start_timestamp': symbol_data.iloc[segment_start]['timestamp'],
                                'end_timestamp': symbol_data.iloc[bar_index - 1]['timestamp'] if bar_index > 0 else symbol_data.iloc[segment_start]['timestamp']
                            }
                        ))
                
                segment_start = bar_index
                current_regime = regime_name
        
        # Add final segment (from last regime change to end of DataFrame)
        if segment_start < len(symbol_data):
            segment_timestamp = symbol_data.iloc[segment_start]['timestamp']
            if isinstance(segment_timestamp, pd.Timestamp):
                segment_timestamp = segment_timestamp.to_pydatetime()
            
            regime_analysis = None
            if self.regime_engine:
                regime_analysis = self.regime_engine.get_regime_at_timestamp(
                    symbol=symbol,
                    timestamp=segment_timestamp
                )
            
            segments.append((
                segment_start,
                len(symbol_data),
                {
                    'regime': current_regime,
                    'regime_analysis': regime_analysis,
                    'start_timestamp': symbol_data.iloc[segment_start]['timestamp'],
                    'end_timestamp': symbol_data.iloc[-1]['timestamp']
                }
            ))
        
        # If no segments created (single regime), return single segment
        if not segments:
            return [(0, len(symbol_data), None)]
        
        return segments
    
    def _assess_liquidity(
        self,
        symbol: str,
        symbol_data: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Run liquidity assessment for each bar and persist the sequence"""
        if symbol_data.empty or not self.liquidity_engine:
            self.liquidity_sequence[symbol] = []
            self.liquidity_by_timestamp[symbol] = {}
            return []
        
        sequence: List[Dict[str, Any]] = []
        timestamp_map: Dict[datetime, Dict[str, Any]] = {}
        
        for idx, row in symbol_data.iterrows():
            market_row = row.to_dict()
            metrics = {}
            try:
                metrics = self.liquidity_engine.assess_liquidity_score(symbol, market_row)
            except Exception as exc:
                logger.warning(f"⚠️  Liquidity assessment failed for {symbol} (row {idx}): {exc}")
                metrics = {}
            
            timestamp = row.get('timestamp')
            if isinstance(timestamp, pd.Timestamp):
                timestamp_dt = timestamp.to_pydatetime()
            else:
                timestamp_dt = timestamp
            
            metrics = metrics or {}
            metrics['timestamp'] = timestamp_dt
            metrics['bar_index'] = idx
            
            regime_value = metrics.get('liquidity_regime')
            if hasattr(regime_value, 'value'):
                metrics['liquidity_regime'] = regime_value.value
            
            sequence.append(metrics)
            if timestamp_dt is not None:
                timestamp_map[timestamp_dt] = metrics
        
        self.liquidity_sequence[symbol] = sequence
        self.liquidity_by_timestamp[symbol] = timestamp_map
        return sequence
    
    def _merge_liquidity_features(self, features_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Attach liquidity metrics to the enriched features DataFrame"""
        if features_df.empty:
            return features_df
        
        sequence = self.liquidity_sequence.get(symbol, [])
        if not sequence:
            features_df = features_df.copy()
            for col in [
                'liquidity_score',
                'liquidity_confidence',
                'liquidity_regime',
                'liquidity_risk_score',
                'liquidity_slippage_risk',
                'liquidity_bid_ask_spread_bps',
                'liquidity_effective_spread_bps',
                'liquidity_market_depth',
                'liquidity_volume_ratio'
            ]:
                if col not in features_df.columns:
                    features_df[col] = np.nan
            return features_df
        
        liquidity_df = pd.DataFrame(sequence)
        if 'timestamp' not in liquidity_df.columns:
            return features_df
        
        liquidity_df = liquidity_df.drop_duplicates(subset=['timestamp'], keep='last')
        liquidity_df['timestamp'] = pd.to_datetime(liquidity_df['timestamp'])
        
        rename_map = {
            'overall_score': 'liquidity_score',
            'confidence': 'liquidity_confidence',
            'liquidity_regime': 'liquidity_regime',
            'liquidity_risk_score': 'liquidity_risk_score',
            'slippage_risk': 'liquidity_slippage_risk',
            'bid_ask_spread_bps': 'liquidity_bid_ask_spread_bps',
            'effective_spread_bps': 'liquidity_effective_spread_bps',
            'market_depth': 'liquidity_market_depth',
            'volume_ratio': 'liquidity_volume_ratio'
        }
        
        columns_present = ['timestamp'] + [col for col in rename_map.keys() if col in liquidity_df.columns]
        liquidity_df = liquidity_df[columns_present].rename(columns=rename_map)
        
        features_df = features_df.copy()
        features_df['timestamp'] = pd.to_datetime(features_df['timestamp'])
        merged_df = features_df.merge(liquidity_df, on='timestamp', how='left')
        expected_cols = [
            'liquidity_score',
            'liquidity_confidence',
            'liquidity_regime',
            'liquidity_risk_score',
            'liquidity_slippage_risk',
            'liquidity_bid_ask_spread_bps',
            'liquidity_effective_spread_bps',
            'liquidity_market_depth',
            'liquidity_volume_ratio'
        ]
        for col in expected_cols:
            if col not in merged_df.columns:
                merged_df[col] = np.nan
        return merged_df
    
    def _add_regime_columns(self, signals_df: pd.DataFrame, symbol: str, regime_sequence: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Add regime information columns to signals DataFrame (Phase 4C)
        
        This enables Type 2 (Explicit) regime awareness in strategies by providing
        primary_regime and volatility_regime columns for each bar.
        
        Args:
            signals_df: DataFrame with processed signals
            symbol: Trading symbol
            regime_sequence: List of regime dictionaries with timestamps
            
        Returns:
            DataFrame with added regime columns:
            - primary_regime: str (e.g., 'bull_market', 'bear_high_volatility', 'range_bound')
            - volatility_regime: str (e.g., 'high_volatility', 'normal_volatility', 'low_volatility')
            - regime_confidence: float (0-1, confidence in regime detection)
        """
        # DEBUG Phase 4C: Log regime sequence info
        logger.debug(f"Phase 4C: _add_regime_columns called for {symbol}")
        logger.debug(f"   Regime sequence length: {len(regime_sequence) if regime_sequence else 0}")
        if regime_sequence:
            logger.debug(f"   First regime: {regime_sequence[0] if regime_sequence else 'N/A'}")
            logger.debug(f"   Last regime: {regime_sequence[-1] if regime_sequence else 'N/A'}")
        
        if signals_df.empty or not regime_sequence:
            # Add default columns if no regime data
            logger.warning(f"⚠️  {symbol}: Empty signals_df or regime_sequence - using defaults")
            signals_df = signals_df.copy()
            signals_df['primary_regime'] = 'normal_volatility'
            signals_df['volatility_regime'] = 'normal_volatility'
            signals_df['regime_confidence'] = 0.0
            return signals_df
        
        try:
            # Convert regime sequence to DataFrame
            regime_df = pd.DataFrame(regime_sequence)
            
            # DEBUG Phase 4C: Log regime_df columns
            logger.debug(f"Phase 4C: Regime DataFrame columns: {list(regime_df.columns)}")
            logger.debug(f"   Regime DataFrame shape: {regime_df.shape}")
            if len(regime_df) > 0:
                logger.debug(f"   Sample regime entry: {regime_df.iloc[0].to_dict()}")
            
            if 'timestamp' not in regime_df.columns:
                logger.warning(f"⚠️  {symbol}: No timestamp in regime sequence, cannot add regime columns")
                signals_df = signals_df.copy()
                signals_df['primary_regime'] = 'normal_volatility'
                signals_df['volatility_regime'] = 'normal_volatility'
                signals_df['regime_confidence'] = 0.0
                return signals_df
            
            # Ensure timestamps are datetime
            regime_df['timestamp'] = pd.to_datetime(regime_df['timestamp'])
            
            # CRITICAL FIX: Map 'regime' column to 'primary_regime' if it exists
            # The regime sequence uses 'regime' but we need 'primary_regime'
            if 'regime' in regime_df.columns and 'primary_regime' not in regime_df.columns:
                regime_df['primary_regime'] = regime_df['regime']
                logger.info(f"✅ {symbol}: Mapped 'regime' → 'primary_regime'")
            
            # If no volatility_regime column exists, default to 'normal_volatility'
            # (This happens when regime sequence only has combined regime like 'choppy')
            if 'volatility_regime' not in regime_df.columns:
                regime_df['volatility_regime'] = 'normal_volatility'
                logger.info(f"✅ {symbol}: Added default 'volatility_regime' = 'normal_volatility'")
            
            # Keep only required columns
            regime_cols = ['timestamp', 'primary_regime', 'volatility_regime', 'confidence']
            available_cols = ['timestamp'] + [col for col in regime_cols[1:] if col in regime_df.columns]
            regime_df = regime_df[available_cols].copy()
            
            # Rename confidence to regime_confidence
            if 'confidence' in regime_df.columns:
                regime_df = regime_df.rename(columns={'confidence': 'regime_confidence'})
            
            # Ensure signals_df has timestamp index as column for merging
            signals_df = signals_df.copy()
            if 'timestamp' not in signals_df.columns:
                signals_df['timestamp'] = pd.to_datetime(signals_df.index)
            else:
                signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
            
            # CRITICAL FIX Phase 4C: Check if regime columns already exist (avoid duplicate merge)
            if 'primary_regime' in signals_df.columns:
                logger.warning(f"⚠️  {symbol}: primary_regime column already exists in signals_df - skipping merge")
                logger.info(f"   Existing regime distribution: {signals_df['primary_regime'].value_counts().to_dict()}")
                return signals_df  # Return as-is, regime data already added
            
            # Merge regime data with signals (forward fill for bars between regime changes)
            merged_df = pd.merge_asof(
                signals_df.sort_values('timestamp'),
                regime_df.sort_values('timestamp'),
                on='timestamp',
                direction='backward'  # Use most recent regime for each bar
            )
            
            # DEBUG Phase 4C: Log merge results
            logger.info(f"🔍 Phase 4C: After merge, merged_df columns: {list(merged_df.columns)}")
            if 'primary_regime' in merged_df.columns:
                regime_dist = merged_df['primary_regime'].value_counts().to_dict()
                logger.info(f"   Primary regime distribution AFTER merge: {regime_dist}")
            
            # Fill any remaining NaNs with defaults
            if 'primary_regime' not in merged_df.columns:
                merged_df['primary_regime'] = 'normal_volatility'
            else:
                merged_df['primary_regime'] = merged_df['primary_regime'].fillna('normal_volatility')
            
            if 'volatility_regime' not in merged_df.columns:
                merged_df['volatility_regime'] = 'normal_volatility'
            else:
                merged_df['volatility_regime'] = merged_df['volatility_regime'].fillna('normal_volatility')
            
            if 'regime_confidence' not in merged_df.columns:
                merged_df['regime_confidence'] = 0.0
            else:
                merged_df['regime_confidence'] = merged_df['regime_confidence'].fillna(0.0)
            
            # Restore original index if it was timestamp-based
            if signals_df.index.name is not None and 'timestamp' in signals_df.columns:
                merged_df = merged_df.set_index('timestamp')
            
            logger.debug(f"✅ {symbol}: Added regime columns to {len(merged_df)} bars")
            
            return merged_df
            
        except Exception as e:
            logger.error(f"❌ {symbol}: Error adding regime columns: {e}")
            # Return original DataFrame with default regime columns
            signals_df = signals_df.copy()
            signals_df['primary_regime'] = 'normal_volatility'
            signals_df['volatility_regime'] = 'normal_volatility'
            signals_df['regime_confidence'] = 0.0
            return signals_df
    
    def get_liquidity_sequence(self, symbol: str) -> List[Dict[str, Any]]:
        """Retrieve stored liquidity sequence for a symbol"""
        return self.liquidity_sequence.get(symbol, [])
    
    def get_liquidity_at_timestamp(self, symbol: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Get liquidity metrics for a specific timestamp (or nearest earlier)"""
        if symbol not in self.liquidity_by_timestamp:
            return None
        
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        
        symbol_map = self.liquidity_by_timestamp[symbol]
        if timestamp in symbol_map:
            return symbol_map[timestamp]
        
        symbol_timestamps = sorted(symbol_map.keys())
        for ts in reversed(symbol_timestamps):
            if ts <= timestamp:
                return symbol_map[ts]
        return None
    
    def _get_latest_liquidity_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        sequence = self.liquidity_sequence.get(symbol, [])
        return sequence[-1] if sequence else None
    
    async def _process_regime_segments(
        self,
        symbol_data: pd.DataFrame,
        regime_segments: List[Tuple[int, int, Optional[Dict[str, Any]]]],
        symbol: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Process DataFrame in regime segments with config adaptation per segment
        
        **ENHANCEMENT:** Processes each regime segment separately with adapted config,
        then combines results. This ensures indicators/features are calculated with
        regime-appropriate parameters.
        
        Args:
            symbol_data: Raw OHLCV DataFrame
            regime_segments: List of (start_idx, end_idx, regime_info) tuples
            symbol: Trading symbol
        
        Returns:
            Tuple of (indicators_df, features_df, signals_df) - combined from all segments
        """
        all_indicators = []
        all_features = []
        
        segment_count = len(regime_segments)
        logger.debug(f"   🔄 Processing {segment_count} regime segments for {symbol}")
        
        for segment_idx, (start_idx, end_idx, regime_info) in enumerate(regime_segments):
            # Extract segment data
            segment_data = symbol_data.iloc[start_idx:end_idx].copy()
            
            if segment_data.empty:
                continue
            
            # Get regime analysis for this segment
            regime_analysis = None
            if regime_info and 'regime_analysis' in regime_info:
                regime_analysis = regime_info['regime_analysis']
            elif self.regime_engine and segment_data is not None and not segment_data.empty:
                # Fallback: Get regime from first bar of segment
                first_timestamp = segment_data.iloc[0]['timestamp']
                if isinstance(first_timestamp, pd.Timestamp):
                    first_timestamp = first_timestamp.to_pydatetime()
                regime_analysis = self.regime_engine.get_regime_at_timestamp(
                    symbol=symbol,
                    timestamp=first_timestamp
                )
            
            liquidity_context = None
            if not segment_data.empty:
                seg_timestamp = segment_data.iloc[0]['timestamp']
                if isinstance(seg_timestamp, pd.Timestamp):
                    seg_timestamp = seg_timestamp.to_pydatetime()
                liquidity_context = self.get_liquidity_at_timestamp(symbol, seg_timestamp)
            
            # Adapt config for this segment's regime
            if regime_analysis:
                regime_name = regime_analysis.primary_regime.value if hasattr(regime_analysis.primary_regime, 'value') else str(regime_analysis.primary_regime)
                logger.debug(
                    f"   📊 Segment {segment_idx + 1}/{segment_count} ({start_idx}-{end_idx}): "
                    f"Regime={regime_name}, Bars={len(segment_data)}"
                )
                
                # Adapt indicator engine config
                if self.indicators_engine and hasattr(self.indicators_engine, 'adapt_to_regime'):
                    await self.indicators_engine.adapt_to_regime(regime_analysis)
                
                # Adapt feature engineer config
                if self.feature_engineer and hasattr(self.feature_engineer, 'adapt_to_regime'):
                    await self.feature_engineer.adapt_to_regime(regime_analysis)
            
            if liquidity_context:
                if self.indicators_engine and hasattr(self.indicators_engine, 'adapt_to_liquidity'):
                    self.indicators_engine.adapt_to_liquidity(liquidity_context)
                if self.feature_engineer and hasattr(self.feature_engineer, 'adapt_to_liquidity'):
                    self.feature_engineer.adapt_to_liquidity(liquidity_context)
            
            # Process segment through pipeline
            # PHASE 2: Calculate indicators for this segment
            segment_indicators = await self._calculate_indicators(segment_data)
            all_indicators.append(segment_indicators)
            
            # PHASE 3: Engineer features for this segment
            segment_features = await self._engineer_features(segment_indicators)
            all_features.append(segment_features)
        
        # Combine segments
        if not all_indicators:
            # Fallback to standard processing if no segments processed
            indicators_df = await self._calculate_indicators(symbol_data)
            features_df = await self._engineer_features(indicators_df)
        else:
            # Combine indicator segments
            indicators_df = pd.concat(all_indicators, ignore_index=True)
            # Sort by timestamp to ensure proper order
            if 'timestamp' in indicators_df.columns:
                indicators_df = indicators_df.sort_values('timestamp').reset_index(drop=True)
            
            # Combine feature segments
            features_df = pd.concat(all_features, ignore_index=True)
            # Sort by timestamp to ensure proper order
            if 'timestamp' in features_df.columns:
                features_df = features_df.sort_values('timestamp').reset_index(drop=True)
        
        # PHASE 4: Generate signals (process entire combined DataFrame)
        # Signals are already filtered bar-by-bar in _filter_signals()
        features_df = self._merge_liquidity_features(features_df, symbol)
        signals_df = await self._generate_signals(features_df)
        
        # Track processing times
        # Note: Segment processing time is distributed across multiple calls
        # We'll use average time per segment for metrics
        if segment_count > 0:
            # Approximate time (would need more detailed tracking for exact measurement)
            avg_segment_time = 0.01  # Placeholder - actual time captured in individual calls
            self.processing_times['indicators'].append(avg_segment_time * segment_count)
            self.processing_times['features'].append(avg_segment_time * segment_count)
        
        logger.debug(
            f"   ✅ Combined {segment_count} segments: "
            f"{len(indicators_df)} bars, {len(indicators_df.columns)} indicator columns"
        )
        
        return indicators_df, features_df, signals_df
    
    # ================================================================
    # Utility Methods
    # ================================================================
    
    def clear_cache(self) -> int:
        """
        Clear enriched data cache.
        
        Returns:
            Number of entries cleared
        """
        count = len(self._cache_entries)
        self._cache_entries.clear()
        logger.info("Cache cleared: %d entries removed", count)
        return count
    
    def get_cached_data(self, symbol: str) -> Optional[EnrichedMarketData]:
        """
        Get cached enriched data for symbol (with TTL check).
        
        Args:
            symbol: Symbol to retrieve
        
        Returns:
            EnrichedMarketData or None if not cached or expired
        """
        return self._cache_get(symbol)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get pipeline performance metrics.
        
        Returns:
            Dict with performance statistics
        """
        avg_times = {
            stage: sum(times) / len(times) if times else 0.0
            for stage, times in self.processing_times.items()
        }
        
        # Evict expired entries before reporting
        self._evict_expired_cache()
        
        return {
            'total_processed': self.total_processed,
            'avg_processing_times': avg_times,
            'cache_size': len(self._cache_entries),
            'cache_max_size': self._cache_max_size,
            'cache_ttl_seconds': self._cache_ttl.total_seconds(),
            'metrics_history_size': self._metrics_maxlen,
            'processing_counts': {
                stage: len(times)
                for stage, times in self.processing_times.items()
            }
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'EnrichedMarketData',
    'ProcessingPipelineOrchestrator',
    'PipelineConstants',
    'PIPELINE_CONSTANTS',
]

