"""
Signals Engine - Enhanced Manager
Unified signal management with orchestration across all signal components
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import json
import warnings

from .signal_generator import SignalGenerator, SignalGenerationConfig, SignalType
from .factor_analyzer import FactorAnalyzer, FactorAnalysisConfig, FactorType
from .alpha_research import AlphaResearcher, AlphaResearchConfig, AlphaStrategy
from .signal_validator import SignalValidator, SignalValidationReport, ValidationStatus
from .signal_combiner import SignalCombiner, CombinationConfig, CombinationMethod, SignalCombination

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class SignalManagerState(Enum):
    """Signal manager operational states"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class SignalPipeline(Enum):
    """Signal processing pipeline stages"""
    GENERATION = "generation"
    FACTOR_ANALYSIS = "factor_analysis"
    ALPHA_RESEARCH = "alpha_research"
    VALIDATION = "validation"
    COMBINATION = "combination"
    OUTPUT = "output"


@dataclass
class SignalManagerConfig:
    """Configuration for signal manager"""
    # Component configurations
    generation_config: Optional[SignalGenerationConfig] = None
    factor_config: Optional[FactorAnalysisConfig] = None
    alpha_config: Optional[AlphaResearchConfig] = None
    combination_config: Optional[CombinationConfig] = None
    
    # Pipeline settings
    enable_factor_analysis: bool = True
    enable_alpha_research: bool = True
    enable_validation: bool = True
    enable_combination: bool = True
    
    # Processing settings
    parallel_processing: bool = True
    max_concurrent_symbols: int = 10
    signal_timeout_seconds: int = 30
    
    # Quality controls
    min_signal_quality: float = 0.5
    max_signals_per_symbol: int = 5
    signal_expiry_hours: int = 24
    
    # Performance settings
    enable_caching: bool = True
    cache_size: int = 1000
    enable_metrics: bool = True
    
    # Risk controls
    enable_risk_checks: bool = True
    max_portfolio_concentration: float = 0.3
    max_sector_concentration: float = 0.5


@dataclass
class SignalPipelineResult:
    """Result of signal pipeline processing"""
    symbol: str
    pipeline_id: str
    processing_timestamp: datetime
    
    # Pipeline stages
    raw_signals: List[Any] = field(default_factory=list)
    factor_analysis_results: Optional[Any] = None
    alpha_research_results: Optional[Any] = None
    validation_reports: List[SignalValidationReport] = field(default_factory=list)
    combined_signal: Optional[SignalCombination] = None
    
    # Final output
    final_signal: Optional[Any] = None
    signal_quality: float = 0.0
    processing_time_ms: float = 0.0
    
    # Pipeline status
    stages_completed: List[SignalPipeline] = field(default_factory=list)
    pipeline_errors: List[str] = field(default_factory=list)
    
    # Metadata
    processing_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioSignalSummary:
    """Portfolio-level signal summary"""
    summary_timestamp: datetime
    total_symbols: int
    total_signals: int
    
    # Quality distribution
    high_quality_signals: int = 0
    medium_quality_signals: int = 0
    low_quality_signals: int = 0
    
    # Signal distribution
    long_signals: int = 0
    short_signals: int = 0
    neutral_signals: int = 0
    
    # Risk metrics
    total_gross_exposure: float = 0.0
    total_net_exposure: float = 0.0
    concentration_risk: float = 0.0
    
    # Performance estimates
    expected_portfolio_return: float = 0.0
    expected_portfolio_volatility: float = 0.0
    expected_sharpe_ratio: float = 0.0
    
    # Top signals
    top_signals: List[Any] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)


class SignalCache:
    """Signal caching system"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = {}
        self._access_times = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached signal"""
        with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Cache signal"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = value
            self._access_times[key] = time.time()
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entry"""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def clear(self) -> None:
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


class SignalMetrics:
    """Signal processing metrics"""
    
    def __init__(self):
        self._metrics = defaultdict(list)
        self._counters = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_processing_time(self, stage: str, time_ms: float) -> None:
        """Record processing time for a stage"""
        with self._lock:
            self._metrics[f"{stage}_processing_time"].append(time_ms)
    
    def increment_counter(self, counter_name: str) -> None:
        """Increment a counter"""
        with self._lock:
            self._counters[counter_name] += 1
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a general metric"""
        with self._lock:
            self._metrics[metric_name].append(value)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        with self._lock:
            summary = {
                'counters': dict(self._counters),
                'averages': {},
                'recent_values': {}
            }
            
            for metric_name, values in self._metrics.items():
                if values:
                    summary['averages'][metric_name] = np.mean(values)
                    summary['recent_values'][metric_name] = values[-10:]  # Last 10 values
            
            return summary


class EnhancedSignalManager:
    """
    Enhanced Signal Manager - Unified orchestration of signal processing
    
    Coordinates signal generation, factor analysis, alpha research,
    validation, and combination across the entire signal pipeline.
    """
    
    def __init__(self, config: Optional[SignalManagerConfig] = None):
        """Initialize enhanced signal manager"""
        self.config = config or SignalManagerConfig()
        
        # Component initialization
        self.signal_generator = SignalGenerator(self.config.generation_config)
        self.factor_analyzer = FactorAnalyzer(self.config.factor_config) if self.config.enable_factor_analysis else None
        self.alpha_researcher = AlphaResearcher(self.config.alpha_config) if self.config.enable_alpha_research else None
        self.signal_validator = SignalValidator() if self.config.enable_validation else None
        self.signal_combiner = SignalCombiner(self.config.combination_config) if self.config.enable_combination else None
        
        # Signal management
        self._active_signals = defaultdict(list)  # symbol -> [signals]
        self._signal_history = defaultdict(deque)  # symbol -> deque of historical signals
        self._pipeline_results = deque(maxlen=10000)
        
        # Caching and metrics
        self.cache = SignalCache(self.config.cache_size) if self.config.enable_caching else None
        self.metrics = SignalMetrics() if self.config.enable_metrics else None
        
        # State management
        self.state = SignalManagerState.INITIALIZING
        self._processing_tasks = {}
        self._lock = threading.Lock()
        
        # Performance tracking
        self._performance_data = defaultdict(list)
        self._processing_times = defaultdict(list)
        
        # Risk monitoring
        self._risk_alerts = deque(maxlen=1000)
        self._portfolio_metrics = {}
        
        self.state = SignalManagerState.READY
        logger.info("Enhanced Signal Manager initialized successfully")
    
    async def process_signal_pipeline(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SignalPipelineResult:
        """Process complete signal pipeline for a symbol"""
        
        start_time = time.time()
        pipeline_id = f"{symbol}_{int(time.time())}"
        context = context or {}
        
        result = SignalPipelineResult(
            symbol=symbol,
            pipeline_id=pipeline_id,
            processing_timestamp=datetime.now(),
            processing_context=context.copy()
        )
        
        try:
            self.state = SignalManagerState.PROCESSING
            
            # Stage 1: Signal Generation
            try:
                stage_start = time.time()
                raw_signals = await self._generate_signals(symbol, market_data, context)
                result.raw_signals = raw_signals
                result.stages_completed.append(SignalPipeline.GENERATION)
                
                if self.metrics:
                    stage_time = (time.time() - stage_start) * 1000
                    self.metrics.record_processing_time("generation", stage_time)
                    self.metrics.increment_counter("signals_generated")
                
                logger.debug(f"Generated {len(raw_signals)} raw signals for {symbol}")
                
            except Exception as e:
                result.pipeline_errors.append(f"Signal generation failed: {str(e)}")
                logger.error(f"Signal generation failed for {symbol}: {e}")
            
            # Stage 2: Factor Analysis (if enabled and signals available)
            if self.factor_analyzer and result.raw_signals:
                try:
                    stage_start = time.time()
                    factor_results = await self._analyze_factors(symbol, market_data, result.raw_signals, context)
                    result.factor_analysis_results = factor_results
                    result.stages_completed.append(SignalPipeline.FACTOR_ANALYSIS)
                    
                    if self.metrics:
                        stage_time = (time.time() - stage_start) * 1000
                        self.metrics.record_processing_time("factor_analysis", stage_time)
                    
                    logger.debug(f"Completed factor analysis for {symbol}")
                    
                except Exception as e:
                    result.pipeline_errors.append(f"Factor analysis failed: {str(e)}")
                    logger.error(f"Factor analysis failed for {symbol}: {e}")
            
            # Stage 3: Alpha Research (if enabled and signals available)
            if self.alpha_researcher and result.raw_signals:
                try:
                    stage_start = time.time()
                    alpha_results = await self._research_alpha(symbol, market_data, result.raw_signals, context)
                    result.alpha_research_results = alpha_results
                    result.stages_completed.append(SignalPipeline.ALPHA_RESEARCH)
                    
                    if self.metrics:
                        stage_time = (time.time() - stage_start) * 1000
                        self.metrics.record_processing_time("alpha_research", stage_time)
                    
                    logger.debug(f"Completed alpha research for {symbol}")
                    
                except Exception as e:
                    result.pipeline_errors.append(f"Alpha research failed: {str(e)}")
                    logger.error(f"Alpha research failed for {symbol}: {e}")
            
            # Stage 4: Signal Validation (if enabled and signals available)
            if self.signal_validator and result.raw_signals:
                try:
                    stage_start = time.time()
                    validation_reports = []
                    
                    for signal in result.raw_signals:
                        validation_context = context.copy()
                        validation_context.update({
                            'factor_analysis': result.factor_analysis_results,
                            'alpha_research': result.alpha_research_results
                        })
                        
                        report = await self.signal_validator.validate_signal(signal, validation_context)
                        validation_reports.append(report)
                    
                    result.validation_reports = validation_reports
                    result.stages_completed.append(SignalPipeline.VALIDATION)
                    
                    if self.metrics:
                        stage_time = (time.time() - stage_start) * 1000
                        self.metrics.record_processing_time("validation", stage_time)
                        self.metrics.increment_counter("signals_validated")
                    
                    logger.debug(f"Validated {len(validation_reports)} signals for {symbol}")
                    
                except Exception as e:
                    result.pipeline_errors.append(f"Signal validation failed: {str(e)}")
                    logger.error(f"Signal validation failed for {symbol}: {e}")
            
            # Filter valid signals for combination
            valid_signals = self._filter_valid_signals(result.raw_signals, result.validation_reports)
            
            # Stage 5: Signal Combination (if enabled and multiple valid signals)
            if self.signal_combiner and len(valid_signals) >= 2:
                try:
                    stage_start = time.time()
                    combination_context = context.copy()
                    combination_context.update({
                        'factor_analysis': result.factor_analysis_results,
                        'alpha_research': result.alpha_research_results,
                        'validation_reports': result.validation_reports
                    })
                    
                    combined_signal = await self.signal_combiner.combine_signals(
                        valid_signals, symbol, combination_context
                    )
                    result.combined_signal = combined_signal
                    result.stages_completed.append(SignalPipeline.COMBINATION)
                    
                    if self.metrics:
                        stage_time = (time.time() - stage_start) * 1000
                        self.metrics.record_processing_time("combination", stage_time)
                        self.metrics.increment_counter("signals_combined")
                    
                    logger.debug(f"Combined signals for {symbol}")
                    
                except Exception as e:
                    result.pipeline_errors.append(f"Signal combination failed: {str(e)}")
                    logger.error(f"Signal combination failed for {symbol}: {e}")
            
            # Stage 6: Final Signal Selection
            final_signal = self._select_final_signal(result)
            result.final_signal = final_signal
            result.stages_completed.append(SignalPipeline.OUTPUT)
            
            if final_signal:
                result.signal_quality = self._calculate_signal_quality(final_signal, result)
                
                # Store active signal
                with self._lock:
                    self._active_signals[symbol].append(final_signal)
                    # Keep only recent signals
                    self._active_signals[symbol] = self._active_signals[symbol][-self.config.max_signals_per_symbol:]
                    
                    # Add to history
                    self._signal_history[symbol].append(final_signal)
                    if len(self._signal_history[symbol]) > 1000:
                        self._signal_history[symbol].popleft()
                
                if self.metrics:
                    self.metrics.increment_counter("final_signals_produced")
                    self.metrics.record_metric("signal_quality", result.signal_quality)
            
            # Record total processing time
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Store pipeline result
            self._pipeline_results.append(result)
            
            # Cache result if enabled
            if self.cache:
                cache_key = f"{symbol}_{int(time.time() // 300)}"  # 5-minute buckets
                self.cache.put(cache_key, result)
            
            if self.metrics:
                self.metrics.record_processing_time("total_pipeline", result.processing_time_ms)
            
            logger.info(f"Pipeline completed for {symbol}: {len(result.stages_completed)} stages, "
                       f"quality: {result.signal_quality:.2f}, time: {result.processing_time_ms:.1f}ms")
            
            self.state = SignalManagerState.READY
            return result
            
        except Exception as e:
            self.state = SignalManagerState.ERROR
            result.pipeline_errors.append(f"Pipeline error: {str(e)}")
            logger.error(f"Pipeline processing failed for {symbol}: {e}")
            return result
    
    async def _generate_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Any]:
        """Generate raw signals"""
        
        try:
            # Generate signals using all available strategies
            signals = []
            
            # Generate momentum signals
            momentum_result = await self.signal_generator.generate_momentum_signal(symbol, market_data)
            if momentum_result and momentum_result.signals:
                signals.extend(momentum_result.signals)
            
            # Generate mean reversion signals
            mean_reversion_result = await self.signal_generator.generate_mean_reversion_signal(symbol, market_data)
            if mean_reversion_result and mean_reversion_result.signals:
                signals.extend(mean_reversion_result.signals)
            
            # Generate statistical arbitrage signals
            stat_arb_result = await self.signal_generator.generate_statistical_arbitrage_signal(symbol, market_data)
            if stat_arb_result and stat_arb_result.signals:
                signals.extend(stat_arb_result.signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []
    
    async def _analyze_factors(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        signals: List[Any],
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """Perform factor analysis"""
        
        try:
            # Get price data for factor analysis
            price_data = market_data.get('prices', pd.DataFrame())
            
            if price_data.empty:
                return None
            
            # Calculate factor exposures
            factor_result = await self.factor_analyzer.calculate_factor_exposures(symbol, price_data)
            
            # Perform factor decomposition
            if factor_result and factor_result.factor_loadings:
                decomposition = await self.factor_analyzer.decompose_returns(
                    symbol, 
                    price_data.get('returns', pd.Series())
                )
                
                # Combine results
                combined_result = {
                    'factor_exposures': factor_result,
                    'factor_decomposition': decomposition,
                    'analysis_timestamp': datetime.now()
                }
                
                return combined_result
            
            return factor_result
            
        except Exception as e:
            logger.error(f"Error in factor analysis for {symbol}: {e}")
            return None
    
    async def _research_alpha(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        signals: List[Any],
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """Perform alpha research"""
        
        try:
            # Get return data for alpha research
            returns = market_data.get('returns', pd.Series())
            
            if returns.empty:
                return None
            
            # Test alpha strategies
            alpha_results = {}
            
            # Momentum alpha
            momentum_alpha = await self.alpha_researcher.test_momentum_alpha(symbol, returns)
            if momentum_alpha:
                alpha_results['momentum'] = momentum_alpha
            
            # Mean reversion alpha
            mean_reversion_alpha = await self.alpha_researcher.test_mean_reversion_alpha(symbol, returns)
            if mean_reversion_alpha:
                alpha_results['mean_reversion'] = mean_reversion_alpha
            
            # Factor-based alpha
            if context.get('factor_analysis'):
                factor_alpha = await self.alpha_researcher.test_factor_alpha(
                    symbol, 
                    returns, 
                    context['factor_analysis']
                )
                if factor_alpha:
                    alpha_results['factor'] = factor_alpha
            
            # Combined alpha research result
            combined_result = {
                'alpha_strategies': alpha_results,
                'research_timestamp': datetime.now(),
                'symbol': symbol
            }
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Error in alpha research for {symbol}: {e}")
            return None
    
    def _filter_valid_signals(
        self,
        signals: List[Any],
        validation_reports: List[SignalValidationReport]
    ) -> List[Any]:
        """Filter signals based on validation results"""
        
        if not validation_reports:
            return signals
        
        valid_signals = []
        
        for signal, report in zip(signals, validation_reports):
            if (report.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING] and
                report.overall_score >= self.config.min_signal_quality):
                valid_signals.append(signal)
        
        return valid_signals
    
    def _select_final_signal(self, result: SignalPipelineResult) -> Optional[Any]:
        """Select final signal from pipeline results"""
        
        # Priority order: combined signal -> best validated signal -> best raw signal
        
        # 1. Combined signal (if available)
        if result.combined_signal:
            return result.combined_signal
        
        # 2. Best validated signal
        if result.validation_reports:
            best_report = max(result.validation_reports, key=lambda r: r.overall_score)
            if best_report.overall_score >= self.config.min_signal_quality:
                # Find corresponding signal
                for i, report in enumerate(result.validation_reports):
                    if report == best_report and i < len(result.raw_signals):
                        return result.raw_signals[i]
        
        # 3. Best raw signal (by confidence)
        if result.raw_signals:
            best_signal = max(result.raw_signals, key=lambda s: getattr(s, 'confidence', 0.0))
            if getattr(best_signal, 'confidence', 0.0) >= self.config.min_signal_quality:
                return best_signal
        
        return None
    
    def _calculate_signal_quality(self, signal: Any, result: SignalPipelineResult) -> float:
        """Calculate overall signal quality score"""
        
        # Base quality from signal confidence
        base_quality = getattr(signal, 'confidence', 0.5)
        
        # Boost from validation
        validation_boost = 0.0
        if result.validation_reports:
            avg_validation_score = np.mean([r.overall_score for r in result.validation_reports])
            validation_boost = avg_validation_score * 0.2
        
        # Boost from factor analysis
        factor_boost = 0.0
        if result.factor_analysis_results:
            factor_boost = 0.1  # Fixed boost for having factor analysis
        
        # Boost from alpha research
        alpha_boost = 0.0
        if result.alpha_research_results:
            alpha_boost = 0.1  # Fixed boost for having alpha research
        
        # Boost from combination
        combination_boost = 0.0
        if result.combined_signal:
            combination_boost = 0.1  # Fixed boost for signal combination
        
        total_quality = min(base_quality + validation_boost + factor_boost + alpha_boost + combination_boost, 1.0)
        
        return total_quality
    
    async def process_portfolio_signals(
        self,
        symbols: List[str],
        market_data_map: Dict[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SignalPipelineResult]:
        """Process signals for entire portfolio"""
        
        context = context or {}
        results = {}
        
        # Limit concurrent processing
        semaphore = asyncio.Semaphore(self.config.max_concurrent_symbols)
        
        async def process_symbol(symbol: str) -> Tuple[str, SignalPipelineResult]:
            async with semaphore:
                try:
                    market_data = market_data_map.get(symbol, {})
                    result = await asyncio.wait_for(
                        self.process_signal_pipeline(symbol, market_data, context),
                        timeout=self.config.signal_timeout_seconds
                    )
                    return symbol, result
                except asyncio.TimeoutError:
                    logger.warning(f"Signal processing timeout for {symbol}")
                    return symbol, SignalPipelineResult(
                        symbol=symbol,
                        pipeline_id=f"{symbol}_timeout",
                        processing_timestamp=datetime.now(),
                        pipeline_errors=["Processing timeout"]
                    )
                except Exception as e:
                    logger.error(f"Error processing signals for {symbol}: {e}")
                    return symbol, SignalPipelineResult(
                        symbol=symbol,
                        pipeline_id=f"{symbol}_error",
                        processing_timestamp=datetime.now(),
                        pipeline_errors=[str(e)]
                    )
        
        # Process all symbols concurrently
        if self.config.parallel_processing:
            tasks = [process_symbol(symbol) for symbol in symbols]
            symbol_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in symbol_results:
                if isinstance(result, tuple):
                    symbol, pipeline_result = result
                    results[symbol] = pipeline_result
                else:
                    logger.error(f"Unexpected result type: {type(result)}")
        else:
            # Sequential processing
            for symbol in symbols:
                symbol, result = await process_symbol(symbol)
                results[symbol] = result
        
        # Update portfolio metrics
        self._update_portfolio_metrics(results)
        
        logger.info(f"Processed signals for {len(results)} symbols")
        
        return results
    
    def _update_portfolio_metrics(self, results: Dict[str, SignalPipelineResult]) -> None:
        """Update portfolio-level metrics"""
        
        total_exposure = 0.0
        net_exposure = 0.0
        symbol_exposures = {}
        
        for symbol, result in results.items():
            if result.final_signal:
                position_size = getattr(result.final_signal, 'suggested_position_size', 0.0)
                total_exposure += abs(position_size)
                net_exposure += position_size
                symbol_exposures[symbol] = abs(position_size)
        
        # Calculate concentration risk
        concentration_risk = 0.0
        if symbol_exposures and total_exposure > 0:
            max_exposure = max(symbol_exposures.values())
            concentration_risk = max_exposure / total_exposure
        
        with self._lock:
            self._portfolio_metrics = {
                'total_gross_exposure': total_exposure,
                'total_net_exposure': net_exposure,
                'concentration_risk': concentration_risk,
                'active_symbols': len([r for r in results.values() if r.final_signal]),
                'last_update': datetime.now()
            }
        
        # Check for risk alerts
        if concentration_risk > self.config.max_portfolio_concentration:
            self._risk_alerts.append({
                'timestamp': datetime.now(),
                'type': 'concentration_risk',
                'message': f"Portfolio concentration risk: {concentration_risk:.1%} > {self.config.max_portfolio_concentration:.1%}",
                'severity': 'high'
            })
    
    def get_portfolio_summary(self) -> PortfolioSignalSummary:
        """Get portfolio signal summary"""
        
        with self._lock:
            active_signals = []
            for symbol_signals in self._active_signals.values():
                active_signals.extend(symbol_signals)
        
        summary = PortfolioSignalSummary(
            summary_timestamp=datetime.now(),
            total_symbols=len(self._active_signals),
            total_signals=len(active_signals)
        )
        
        if active_signals:
            # Quality distribution
            for signal in active_signals:
                quality = getattr(signal, 'confidence', 0.5)
                
                if quality >= 0.8:
                    summary.high_quality_signals += 1
                elif quality >= 0.6:
                    summary.medium_quality_signals += 1
                else:
                    summary.low_quality_signals += 1
            
            # Signal distribution
            for signal in active_signals:
                strength = getattr(signal, 'strength', 0.0)
                
                if strength > 0.1:
                    summary.long_signals += 1
                elif strength < -0.1:
                    summary.short_signals += 1
                else:
                    summary.neutral_signals += 1
            
            # Risk metrics
            summary.total_gross_exposure = self._portfolio_metrics.get('total_gross_exposure', 0.0)
            summary.total_net_exposure = self._portfolio_metrics.get('total_net_exposure', 0.0)
            summary.concentration_risk = self._portfolio_metrics.get('concentration_risk', 0.0)
            
            # Performance estimates
            expected_returns = [getattr(s, 'expected_return', 0.0) for s in active_signals]
            expected_volatilities = [getattr(s, 'expected_volatility', 0.2) for s in active_signals]
            
            summary.expected_portfolio_return = np.mean(expected_returns)
            summary.expected_portfolio_volatility = np.mean(expected_volatilities)
            
            if summary.expected_portfolio_volatility > 0:
                summary.expected_sharpe_ratio = summary.expected_portfolio_return / summary.expected_portfolio_volatility
            
            # Top signals
            sorted_signals = sorted(active_signals, key=lambda s: getattr(s, 'confidence', 0.0), reverse=True)
            summary.top_signals = sorted_signals[:10]
        
        # Risk alerts
        recent_alerts = [alert for alert in self._risk_alerts if 
                        (datetime.now() - alert['timestamp']).total_seconds() < 3600]  # Last hour
        summary.risk_alerts = [alert['message'] for alert in recent_alerts]
        
        return summary
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        
        pipeline_count = len(self._pipeline_results)
        successful_pipelines = len([r for r in self._pipeline_results if r.final_signal])
        
        avg_processing_time = 0.0
        if self._pipeline_results:
            avg_processing_time = np.mean([r.processing_time_ms for r in self._pipeline_results])
        
        stage_completion_rates = {}
        for stage in SignalPipeline:
            completed = len([r for r in self._pipeline_results if stage in r.stages_completed])
            stage_completion_rates[stage.value] = completed / max(pipeline_count, 1)
        
        stats = {
            'total_pipelines_processed': pipeline_count,
            'successful_pipelines': successful_pipelines,
            'success_rate': successful_pipelines / max(pipeline_count, 1),
            'average_processing_time_ms': avg_processing_time,
            'stage_completion_rates': stage_completion_rates,
            'active_symbols': len(self._active_signals),
            'total_active_signals': sum(len(signals) for signals in self._active_signals.values()),
            'recent_risk_alerts': len([a for a in self._risk_alerts 
                                     if (datetime.now() - a['timestamp']).total_seconds() < 3600])
        }
        
        # Add component-specific stats
        if self.metrics:
            stats['detailed_metrics'] = self.metrics.get_summary()
        
        if self.signal_validator:
            stats['validation_stats'] = self.signal_validator.get_validation_statistics()
        
        if self.signal_combiner:
            stats['combination_stats'] = self.signal_combiner.get_combination_statistics()
        
        return stats
    
    def get_active_signals(self, symbol: Optional[str] = None) -> Dict[str, List[Any]]:
        """Get active signals"""
        
        with self._lock:
            if symbol:
                return {symbol: self._active_signals.get(symbol, [])}
            else:
                return dict(self._active_signals)
    
    def get_recent_pipeline_results(self, limit: int = 100) -> List[SignalPipelineResult]:
        """Get recent pipeline results"""
        
        return list(self._pipeline_results)[-limit:]
    
    def cleanup_expired_signals(self) -> int:
        """Clean up expired signals"""
        
        expiry_time = datetime.now() - timedelta(hours=self.config.signal_expiry_hours)
        cleaned_count = 0
        
        with self._lock:
            for symbol in list(self._active_signals.keys()):
                original_count = len(self._active_signals[symbol])
                
                # Filter out expired signals
                self._active_signals[symbol] = [
                    signal for signal in self._active_signals[symbol]
                    if getattr(signal, 'timestamp', datetime.now()) > expiry_time
                ]
                
                cleaned_count += original_count - len(self._active_signals[symbol])
                
                # Remove empty symbol entries
                if not self._active_signals[symbol]:
                    del self._active_signals[symbol]
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired signals")
        
        return cleaned_count
    
    async def shutdown(self) -> None:
        """Shutdown signal manager"""
        
        logger.info("Shutting down Enhanced Signal Manager")
        
        self.state = SignalManagerState.SHUTDOWN
        
        # Cancel any running tasks
        for task_id, task in self._processing_tasks.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled processing task: {task_id}")
        
        # Clear caches
        if self.cache:
            self.cache.clear()
        
        logger.info("Enhanced Signal Manager shutdown complete")
    
    def __str__(self) -> str:
        """String representation"""
        return f"EnhancedSignalManager(state={self.state.value}, active_symbols={len(self._active_signals)})"