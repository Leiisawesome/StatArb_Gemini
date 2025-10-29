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
Version: 1.0.0
Status: Production
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
import asyncio

from core_engine.system.interfaces import ISystemComponent, IRegimeAware, RegimeContext
from core_engine.exceptions import ConfigurationRequiredError

# Import will be available after components exist
from core_engine.data.manager import ClickHouseDataManager
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator

# Import configurations
from core_engine.config import DataConfig, IndicatorConfig, FeatureConfig, SignalConfig

logger = logging.getLogger(__name__)

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
        checks = {
            'has_raw_data': not self.raw_data.empty,
            'has_indicators': not self.indicators.empty,
            'has_features': not self.features.empty,
            'has_signals': not self.signals.empty,
            'raw_columns_present': all(col in self.signals.columns for col in ['open', 'high', 'low', 'close', 'volume']),
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
            'enrichment_valid': self.validate_enrichment()
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
        signal_config: Optional[Any] = None
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
        if True:  # Config is always available now
            self.data_config = data_config or DataConfig()
            self.indicator_config = indicator_config or IndicatorConfig()
            self.feature_config = feature_config or FeatureConfig()
            self.signal_config = signal_config or SignalConfig()
        else:
            self.data_config = data_config or {}
            self.indicator_config = indicator_config or {}
            self.feature_config = feature_config or {}
            self.signal_config = signal_config or {}
        
        # Pipeline components (initialized in initialize())
        self.data_manager: Optional[Any] = None
        self.indicators_engine: Optional[Any] = None
        self.feature_engineer: Optional[Any] = None
        self.signal_generator: Optional[Any] = None
        
        # Regime awareness (IRegimeAware)
        self.regime_engine: Optional[Any] = None
        self.current_regime_context: Optional[RegimeContext] = None
        
        # Processing cache
        self.enriched_data_cache: Dict[str, EnrichedMarketData] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_clear = datetime.now()
        
        # Performance metrics
        self.processing_times: Dict[str, List[float]] = {
            'data_loading': [],
            'indicators': [],
            'features': [],
            'signals': [],
            'total': []
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
        
        self.is_operational = True
        logger.info("✅ Pipeline orchestrator operational")
        return True
    
    async def stop(self) -> bool:
        """
        Stop pipeline operations
        
        Returns:
            True if stop successful
        """
        self.is_operational = False
        
        # Clear cache
        self.enriched_data_cache.clear()
        
        logger.info("Pipeline orchestrator stopped")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all pipeline components
        
        Returns:
            Dict with health status of each component
        """
        health = {
            'orchestrator_healthy': self.is_operational,
            'initialized': self.is_initialized,
            'cache_size': len(self.enriched_data_cache),
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
            'cache_size': len(self.enriched_data_cache),
            'total_processed': self.total_processed,
            'avg_processing_times_ms': {k: v * 1000 for k, v in avg_times.items()},
            'components_available': True,
            'config_available': True
        }
    
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
        cache_size = len(self.enriched_data_cache)
        self.enriched_data_cache.clear()
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
            self.enriched_data_cache.clear()
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
        Process raw market data through complete pipeline
        
        Returns fully enriched data ready for strategy consumption.
        
        **Pipeline Flow:**
        1. Load raw OHLCV (DataManager)
        2. Calculate indicators (EnhancedTechnicalIndicators)
        3. Engineer features (EnhancedFeatureEngineer)
        4. Generate signals (EnhancedSignalGenerator)
        
        **Rule 3 Compliance:** This is the ONLY way strategies should get data.
        
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
            
            phase1_time = (datetime.now() - phase1_start).total_seconds()
            self.processing_times['data_loading'].append(phase1_time)
            logger.debug(f"✅ Phase 1 complete: {phase1_time:.3f}s")
            
            if not raw_data or all(df.empty for df in raw_data.values()):
                logger.warning("No raw data loaded")
                return {}
            
            # Process each symbol through pipeline
            for symbol in symbols:
                if symbol not in raw_data or raw_data[symbol].empty:
                    logger.warning(f"No data for {symbol}, skipping")
                    continue
                
                symbol_data = raw_data[symbol].copy()
                
                try:
                    # PHASE 2: Calculate technical indicators
                    logger.debug(f"🔧 Phase 2: Calculating indicators for {symbol}")
                    phase2_start = datetime.now()
                    
                    indicators_df = await self._calculate_indicators(symbol_data)
                    
                    phase2_time = (datetime.now() - phase2_start).total_seconds()
                    self.processing_times['indicators'].append(phase2_time)
                    
                    # PHASE 3: Engineer features
                    logger.debug(f"🔬 Phase 3: Engineering features for {symbol}")
                    phase3_start = datetime.now()
                    
                    features_df = await self._engineer_features(indicators_df)
                    
                    phase3_time = (datetime.now() - phase3_start).total_seconds()
                    self.processing_times['features'].append(phase3_time)
                    
                    # PHASE 4: Generate preliminary signals
                    logger.debug(f"📡 Phase 4: Generating signals for {symbol}")
                    phase4_start = datetime.now()
                    
                    signals_df = await self._generate_signals(features_df)
                    
                    phase4_time = (datetime.now() - phase4_start).total_seconds()
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
                        regime_context=self.current_regime_context
                    )
                    
                    # Validate enrichment
                    if not enriched_data[symbol].validate_enrichment():
                        logger.warning(f"⚠️  {symbol}: enrichment validation failed")
                    
                    logger.info(
                        f"✅ {symbol} processed: {len(symbol_data)} bars → "
                        f"{len(signals_df.columns)} total columns "
                        f"(P2:{phase2_time:.2f}s P3:{phase3_time:.2f}s P4:{phase4_time:.2f}s)"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} processing failed: {e}")
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
        Phase 1: Load raw OHLCV data
        
        Returns:
            Dict[symbol, DataFrame with OHLCV columns]
        """
        if not self.data_manager:
            logger.warning("DataManager not available, returning empty data")
            return {symbol: pd.DataFrame() for symbol in symbols}
        
        try:
            # Load data through DataManager (Single Data Authority - Rule 3.1)
            raw_data = await self.data_manager.load_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                interval=timeframe
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
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            return {symbol: pd.DataFrame() for symbol in symbols}
    
    async def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 2: Calculate technical indicators
        
        Args:
            data: Raw OHLCV DataFrame
        
        Returns:
            DataFrame with OHLCV + 29+ indicator columns
        """
        if not self.indicators_engine:
            logger.warning("Indicators engine not available, returning raw data")
            return data.copy()
        
        try:
            # Calculate indicators through EnhancedTechnicalIndicators (Rule 3.2)
            indicators_df = self.indicators_engine.calculate_indicators(data)
            return indicators_df
            
        except Exception as e:
            logger.error(f"Indicator calculation failed: {e}")
            return data.copy()
    
    async def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 3: Engineer ML-ready features
        
        Args:
            data: DataFrame with OHLCV + indicators
        
        Returns:
            DataFrame with OHLCV + indicators + 50+ features
        """
        if not self.feature_engineer:
            logger.warning("Feature engineer not available, returning data as-is")
            return data.copy()
        
        try:
            # Engineer features through EnhancedFeatureEngineer (Rule 3.3)
            features_df = self.feature_engineer.create_features(data)
            return features_df
            
        except Exception as e:
            logger.error(f"Feature engineering failed: {e}")
            return data.copy()
    
    async def _generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 4: Generate preliminary trading signals
        
        Args:
            data: DataFrame with OHLCV + indicators + features
        
        Returns:
            DataFrame with OHLCV + indicators + features + signal columns
        """
        if not self.signal_generator:
            logger.warning("Signal generator not available, returning data as-is")
            return data.copy()
        
        try:
            # Generate signals through EnhancedSignalGenerator (Rule 3.4)
            signals_df = self.signal_generator.generate_signals(data)
            return signals_df
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return data.copy()
    
    # ================================================================
    # Utility Methods
    # ================================================================
    
    def clear_cache(self) -> int:
        """
        Clear enriched data cache
        
        Returns:
            Number of entries cleared
        """
        count = len(self.enriched_data_cache)
        self.enriched_data_cache.clear()
        self.last_cache_clear = datetime.now()
        logger.info(f"Cache cleared: {count} entries removed")
        return count
    
    def get_cached_data(self, symbol: str) -> Optional[EnrichedMarketData]:
        """
        Get cached enriched data for symbol
        
        Args:
            symbol: Symbol to retrieve
        
        Returns:
            EnrichedMarketData or None if not cached
        """
        return self.enriched_data_cache.get(symbol)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get pipeline performance metrics
        
        Returns:
            Dict with performance statistics
        """
        avg_times = {
            stage: sum(times) / len(times) if times else 0.0
            for stage, times in self.processing_times.items()
        }
        
        return {
            'total_processed': self.total_processed,
            'avg_processing_times': avg_times,
            'cache_size': len(self.enriched_data_cache),
            'last_cache_clear': self.last_cache_clear.isoformat(),
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
    'ProcessingPipelineOrchestrator'
]

