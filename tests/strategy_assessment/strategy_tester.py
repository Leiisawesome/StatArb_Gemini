#!/usr/bin/env python3
"""
Comprehensive Strategy Testing Framework
========================================

Professional framework for testing and validating all 10 enhanced strategies.
Integrates with core_engine components and backtesting infrastructure.

Key Features:
- Automated testing of all 10 strategies
- Data loading from ClickHouse
- Performance comparison and ranking
- Regime-based analysis
- Signal quality assessment
- Comprehensive reporting

Author: StatArb_Gemini Strategy Optimization
Version: 1.0.0 (Phase 1 Implementation)
Date: October 2025
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import asyncio
import json
from dataclasses import dataclass, asdict

# Ensure pd is available globally
pd.options.mode.chained_assignment = None  # Suppress warnings

# Import backtesting framework
from .backtesting_framework import (
    ProfessionalBacktester, BacktestConfig, PerformanceMetrics, 
    MarketRegime, Trade
)

# Import strategy config factory (Phase 3)
from .strategy_config_factory import StrategyConfigFactory

# Import core engine components
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '../../'))

try:
    from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
    from core_engine.regime.engine import EnhancedRegimeEngine
    from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
    from core_engine.processing.features.engineer import EnhancedFeatureEngineer
    from core_engine.type_definitions.strategy import StrategyType
    from core_engine.trading.strategies.strategy_engine import StrategyConfig
except ImportError as e:
    logging.error(f"Failed to import core engine components: {e}")
    logging.error("Make sure core_engine package is in PYTHONPATH")

logger = logging.getLogger(__name__)


@dataclass
class StrategyTestConfig:
    """Configuration for strategy testing"""
    
    # Strategy identification
    strategy_type: str
    strategy_name: str
    strategy_config: Dict[str, Any]
    
    # Testing parameters
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    
    # Data configuration
    data_interval: str = "5min"  # Phase 4.3: Testing 5-minute data for better risk-adjusted returns
    
    # Performance thresholds
    min_sharpe_ratio: float = 1.0
    max_drawdown_threshold: float = 0.20
    min_win_rate: float = 0.50


@dataclass
class StrategyTestResult:
    """Results from strategy testing"""
    
    strategy_type: str
    strategy_name: str
    performance_metrics: Dict[str, Any]
    backtest_report: Dict[str, Any]
    signal_quality: Dict[str, Any]
    regime_performance: Dict[str, Any]
    
    # Performance grade
    overall_grade: str = "C"
    alpha_potential: str = "MEDIUM"
    optimization_priority: int = 5
    
    # Recommendations
    strengths: List[str] = None
    weaknesses: List[str] = None
    optimization_recommendations: List[str] = None
    
    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []
        if self.optimization_recommendations is None:
            self.optimization_recommendations = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strategy_type': self.strategy_type,
            'strategy_name': self.strategy_name,
            'performance_metrics': self.performance_metrics,
            'backtest_report': self.backtest_report,
            'signal_quality': self.signal_quality,
            'regime_performance': self.regime_performance,
            'overall_grade': self.overall_grade,
            'alpha_potential': self.alpha_potential,
            'optimization_priority': self.optimization_priority,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'optimization_recommendations': self.optimization_recommendations
        }


class ComprehensiveStrategyTester:
    """
    Comprehensive Strategy Testing Framework
    
    Professional testing infrastructure for all 10 enhanced strategies.
    Provides standardized testing, performance comparison, and optimization recommendations.
    """
    
    def __init__(self, output_dir: str = "tests/strategy_assessment/results"):
        """Initialize strategy tester"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test results storage
        self.test_results: Dict[str, StrategyTestResult] = {}
        self.performance_rankings: List[Tuple[str, float]] = []
        
        # Core engine components
        self.data_manager: Optional[ClickHouseDataManager] = None
        self.regime_engine: Optional[EnhancedRegimeEngine] = None
        self.indicators_engine: Optional[EnhancedTechnicalIndicators] = None
        self.feature_engineer: Optional[EnhancedFeatureEngineer] = None
        
        # Data quality metrics storage
        self.quality_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🧪 Comprehensive Strategy Tester initialized")
        logger.info(f"   Output directory: {self.output_dir}")
    
    async def initialize_components(self, data_config: ClickHouseDataConfig) -> bool:
        """Initialize core engine components"""
        
        try:
            logger.info("🔧 Initializing core engine components...")
            
            # Initialize data manager
            self.data_manager = ClickHouseDataManager(data_config)
            await self.data_manager.initialize()
            logger.info("   ✅ Data Manager initialized")
            
            # Initialize regime engine
            self.regime_engine = EnhancedRegimeEngine({})
            await self.regime_engine.initialize()
            logger.info("   ✅ Regime Engine initialized")
            
            # Initialize indicators engine
            self.indicators_engine = EnhancedTechnicalIndicators({})
            await self.indicators_engine.initialize()
            logger.info("   ✅ Indicators Engine initialized")
            
            # Initialize feature engineer
            self.feature_engineer = EnhancedFeatureEngineer({})
            await self.feature_engineer.initialize()
            logger.info("   ✅ Feature Engineer initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            return False
    
    async def load_market_data(self, symbols: List[str], start_date: str, 
                               end_date: str, interval: str = "1min") -> Dict[str, pd.DataFrame]:
        """Load market data for testing"""
        
        try:
            logger.info(f"📊 Loading market data...")
            logger.info(f"   Symbols: {symbols}")
            logger.info(f"   Period: {start_date} to {end_date}")
            logger.info(f"   Interval: {interval}")
            
            market_data = {}
            
            # Convert string dates to datetime objects
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            for symbol in symbols:
                data = self.data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=start_dt,
                    end_date=end_dt,
                    timeframe=interval
                )
                
                if data is not None and not data.empty:
                    market_data[symbol] = data
                    logger.info(f"   ✅ Loaded {len(data)} bars for {symbol}")
                else:
                    logger.warning(f"   ⚠️  No data for {symbol}")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Market data loading failed: {e}")
            return {}
    
    def _quick_data_quality_check(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Quick data quality validation (Phase 2.4)"""
        try:
            quality_metrics = {
                'symbol': symbol,
                'data_points': len(df),
                'missing_pct': 0.0,
                'outliers_pct': 0.0,
                'duplicates': 0,
                'quality_score': 100.0,
                'issues': []
            }
            
            # Check missing values
            if 'close' in df.columns:
                missing = df['close'].isnull().sum()
                missing_pct = (missing / len(df)) * 100 if len(df) > 0 else 0
                quality_metrics['missing_pct'] = missing_pct
                
                if missing_pct > 5:
                    quality_metrics['issues'].append(f"High missing data: {missing_pct:.1f}%")
                    quality_metrics['quality_score'] -= 20
            
            # Check for outliers (simple z-score method)
            if 'close' in df.columns and len(df) > 10:
                returns = df['close'].pct_change()
                if returns.std() > 0:
                    z_scores = np.abs((returns - returns.mean()) / returns.std())
                    outliers = (z_scores > 5).sum()
                    outliers_pct = (outliers / len(df)) * 100
                    quality_metrics['outliers_pct'] = outliers_pct
                    
                    if outliers_pct > 2:
                        quality_metrics['issues'].append(f"High outliers: {outliers_pct:.1f}%")
                        quality_metrics['quality_score'] -= 10
            
            # Check for duplicates
            if 'timestamp' in df.columns:
                duplicates = df['timestamp'].duplicated().sum()
                quality_metrics['duplicates'] = duplicates
                
                if duplicates > 0:
                    quality_metrics['issues'].append(f"Duplicate timestamps: {duplicates}")
                    quality_metrics['quality_score'] -= 15
            
            # Ensure score is between 0 and 100
            quality_metrics['quality_score'] = max(0, min(100, quality_metrics['quality_score']))
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Data quality check failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'data_points': len(df),
                'quality_score': 0.0,
                'issues': [f"Validation error: {str(e)}"]
            }
    
    async def prepare_strategy_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Prepare data with indicators and features"""
        
        try:
            logger.info("🔄 Preparing strategy data with indicators and features...")
            
            # Quick data quality validation
            logger.info("📊 Validating data quality...")
            for symbol, data in market_data.items():
                quality_metrics = self._quick_data_quality_check(data, symbol)
                self.quality_metrics[symbol] = quality_metrics
                
                if quality_metrics['quality_score'] >= 85:
                    logger.info(f"   ✅ {symbol}: Data quality validated (Score: {quality_metrics['quality_score']:.1f}/100)")
                else:
                    logger.warning(f"   ⚠️  {symbol}: Data quality score: {quality_metrics['quality_score']:.1f}/100")
            
            processed_data = {}
            
            for symbol, data in market_data.items():
                try:
                    # Ensure data has required columns
                    if 'close' not in data.columns:
                        logger.warning(f"   ⚠️  {symbol}: Missing 'close' column, skipping indicators")
                        processed_data[symbol] = data
                        continue
                    
                    # Add symbol column if missing (required by some indicators)
                    data_copy = data.copy()
                    if 'symbol' not in data_copy.columns:
                        data_copy['symbol'] = symbol
                    
                    # Calculate indicators (synchronous method)
                    data_with_indicators = self.indicators_engine.calculate_indicators(data_copy)
                    
                    # Engineer features (synchronous method)
                    data_with_features = self.feature_engineer.create_features(data_with_indicators)
                    
                    processed_data[symbol] = data_with_features
                    logger.info(f"   ✅ Processed {symbol}: {len(data_with_features.columns)} features")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️  {symbol}: Feature engineering failed ({e}), using raw data")
                    processed_data[symbol] = data
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Data preparation failed: {e}")
            return market_data  # Return original data as fallback
    
    async def detect_regimes(self, market_data: Dict[str, pd.DataFrame]) -> List[Tuple[datetime, MarketRegime]]:
        """Detect market regimes throughout testing period"""
        
        try:
            logger.info("📈 Detecting market regimes...")
            
            regime_history = []
            
            # Use primary symbol for regime detection
            primary_symbol = list(market_data.keys())[0]
            primary_data = market_data[primary_symbol]
            
            # Simplified regime detection based on volatility and returns
            # Calculate rolling metrics for regime classification
            returns = primary_data['close'].pct_change()
            volatility = returns.rolling(window=20).std() * np.sqrt(252)  # Annualized
            rolling_return = returns.rolling(window=20).mean() * 252  # Annualized
            
            # Sample regime detection every 100 bars to reduce overhead
            sample_indices = range(20, len(primary_data), 100)
            
            for i in sample_indices:
                timestamp = primary_data.index[i]
                vol = volatility.iloc[i] if not pd.isna(volatility.iloc[i]) else 0.15
                ret = rolling_return.iloc[i] if not pd.isna(rolling_return.iloc[i]) else 0.0
                
                # Classify regime based on volatility and returns
                if vol > 0.30:
                    regime = MarketRegime.HIGH_VOLATILITY
                elif vol < 0.12:
                    regime = MarketRegime.LOW_VOLATILITY
                elif ret > 0.15:
                    regime = MarketRegime.BULL
                elif ret < -0.15:
                    regime = MarketRegime.BEAR
                else:
                    regime = MarketRegime.SIDEWAYS
                
                regime_history.append((timestamp, regime))
            
            logger.info(f"   ✅ Detected {len(regime_history)} regime periods")
            return regime_history
            
        except Exception as e:
            logger.error(f"❌ Regime detection failed: {e}")
            # Return default regime for entire period as fallback
            if market_data:
                primary_symbol = list(market_data.keys())[0]
                primary_data = market_data[primary_symbol]
                return [(primary_data.index[0], MarketRegime.UNKNOWN)]
            return []
    
    async def test_strategy(self, config: StrategyTestConfig) -> StrategyTestResult:
        """
        Test a single strategy comprehensively
        
        Args:
            config: Strategy test configuration
            
        Returns:
            StrategyTestResult with comprehensive analysis
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"TESTING STRATEGY: {config.strategy_name} ({config.strategy_type})")
        logger.info(f"{'='*80}\n")
        
        try:
            # Step 1: Load and prepare market data
            market_data = await self.load_market_data(
                config.symbols, config.start_date, config.end_date, config.data_interval
            )
            
            if not market_data:
                logger.error(f"❌ No market data available for {config.strategy_name}")
                return None
            
            # Step 2: Prepare data with indicators and features
            processed_data = await self.prepare_strategy_data(market_data)
            
            # Step 3: Detect market regimes
            regime_history = await self.detect_regimes(market_data)
            
            # Step 4: Load strategy implementation
            strategy = await self._load_strategy_implementation(config)
            
            if strategy is None:
                logger.error(f"❌ Failed to load strategy: {config.strategy_name}")
                return None
            
            # Step 5: Initialize backtester
            backtest_config = BacktestConfig(
                start_date=config.start_date,
                end_date=config.end_date,
                initial_capital=config.initial_capital,
                data_interval=config.data_interval,
                enable_regime_analysis=True
            )
            
            backtester = ProfessionalBacktester(backtest_config)
            
            # Step 6: Run backtest
            logger.info(f"🚀 Running backtest for {config.strategy_name}...")
            
            await self._run_strategy_backtest(
                strategy, backtester, processed_data, regime_history
            )
            
            # Step 7: Calculate performance metrics
            performance_metrics = backtester.calculate_performance_metrics()
            
            # Step 8: Generate backtest report
            backtest_report = backtester.generate_report(
                config.strategy_name,
                save_path=str(self.output_dir / config.strategy_type)
            )
            
            # Step 9: Analyze signal quality
            signal_quality = self._analyze_signal_quality(backtester.closed_positions)
            
            # Step 10: Analyze regime performance
            regime_performance = self._analyze_regime_performance(
                backtester.closed_positions, regime_history
            )
            
            # Step 11: Grade strategy and provide recommendations
            grade, alpha_potential, priority = self._grade_strategy_performance(performance_metrics)
            strengths, weaknesses, recommendations = self._generate_recommendations(
                performance_metrics, signal_quality, regime_performance
            )
            
            # Step 12: Create test result
            test_result = StrategyTestResult(
                strategy_type=config.strategy_type,
                strategy_name=config.strategy_name,
                performance_metrics=performance_metrics.to_dict(),
                backtest_report=backtest_report,
                signal_quality=signal_quality,
                regime_performance=regime_performance,
                overall_grade=grade,
                alpha_potential=alpha_potential,
                optimization_priority=priority,
                strengths=strengths,
                weaknesses=weaknesses,
                optimization_recommendations=recommendations
            )
            
            # Step 13: Print summary
            backtester.print_summary(config.strategy_name)
            self._print_strategy_analysis(test_result)
            
            # Step 14: Store results
            self.test_results[config.strategy_type] = test_result
            
            # Step 15: Save detailed results
            self._save_test_result(test_result)
            
            logger.info(f"✅ Strategy testing completed: {config.strategy_name}")
            logger.info(f"   Grade: {grade} | Alpha Potential: {alpha_potential} | Priority: {priority}")
            
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Strategy testing failed for {config.strategy_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _load_strategy_implementation(self, config: StrategyTestConfig):
        """Load strategy implementation"""
        
        try:
            # Map strategy types to implementations
            strategy_modules = {
                'statistical_arbitrage': 'core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage',
                'momentum': 'core_engine.trading.strategies.implementations.momentum.enhanced_momentum',
                'mean_reversion': 'core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion',
                'pairs_trading': 'core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading',
                'breakout': 'core_engine.trading.strategies.implementations.breakout.enhanced_breakout',
                'trend_following': 'core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following',
                'volatility': 'core_engine.trading.strategies.implementations.volatility.enhanced_volatility',
                'arbitrage': 'core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage',
                'factor': 'core_engine.trading.strategies.implementations.factor.enhanced_factor',
                'multi_asset': 'core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset'
            }
            
            module_path = strategy_modules.get(config.strategy_type)
            if not module_path:
                logger.error(f"Unknown strategy type: {config.strategy_type}")
                return None
            
            # Dynamically import strategy class
            from importlib import import_module
            module = import_module(module_path)
            
            # Get strategy class (assumes class name is Enhanced<Type>Strategy)
            class_name = ''.join([word.capitalize() for word in config.strategy_type.split('_')]) + 'Strategy'
            class_name = 'Enhanced' + class_name
            
            strategy_class = getattr(module, class_name, None)
            if not strategy_class:
                logger.error(f"Strategy class not found: {class_name}")
                return None
            
            # Create strategy configuration object
            # For now, use minimal default config (will be enhanced in Phase 3-7)
            
            # Extract only StrategyConfig-compatible parameters
            # Determine strategy type from config or strategy name
            strategy_type = getattr(config, 'strategy_type', None)
            if strategy_type is None:
                # Try to infer from strategy name
                strategy_type_map = {
                    'statistical_arbitrage': StrategyType.STATISTICAL_ARBITRAGE,
                    'momentum': StrategyType.MOMENTUM,
                    'mean_reversion': StrategyType.MEAN_REVERSION,
                    'pairs_trading': StrategyType.PAIRS_TRADING,
                    'trend_following': StrategyType.TREND_FOLLOWING,
                    'breakout': StrategyType.BREAKOUT,
                    'volatility': StrategyType.VOLATILITY,
                    'arbitrage': StrategyType.ARBITRAGE,
                    'factor': StrategyType.FACTOR,
                    'multi_asset': StrategyType.MULTI_ASSET
                }
                strategy_type = strategy_type_map.get(config.strategy_name.lower(), StrategyType.CUSTOM)
            
            # Ensure strategy_type is StrategyType enum, not string
            if isinstance(strategy_type, str):
                strategy_type = StrategyType[strategy_type.upper()]
            
            # ===================================================================
            # PHASE 3 ENHANCEMENT: Use Strategy-Specific Configs
            # ===================================================================
            # Create strategy-specific configuration using config factory
            # This enables strategies to use their advanced features
            
            logger.info(f"   🔧 Creating {config.strategy_type}-specific configuration...")
            
            # Prepare config overrides (avoid duplicate keys)
            config_overrides = {**config.strategy_config}
            config_overrides.pop('symbols', None)  # Remove symbols from overrides since we pass it explicitly
            config_overrides.pop('strategy_id', None)  # Remove if present
            config_overrides.pop('strategy_name', None)  # Remove if present
            
            # PROFESSIONAL MODE: Enable pre-loaded pairs for Statistical Arbitrage
            # Note: config.strategy_type might be string or enum, so check both
            is_stat_arb = (config.strategy_type == StrategyType.STATISTICAL_ARBITRAGE or 
                          config.strategy_type == 'statistical_arbitrage' or
                          str(config.strategy_type) == 'statistical_arbitrage')
            
            if is_stat_arb:
                config_overrides['use_preloaded_pairs'] = True
                logger.info("   📊 Enabling PRE-LOADED PAIRS mode for Statistical Arbitrage (PROFESSIONAL)")
            
            strategy_config = StrategyConfigFactory.create_config(
                strategy_type=config.strategy_type,
                symbols=config.symbols,
                strategy_id=config.strategy_name,
                strategy_name=config.strategy_name,
                # Override defaults with user-provided config (excluding duplicates)
                **config_overrides
            )
            
            logger.info(f"   ✅ Created {type(strategy_config).__name__}")
            
            # Instantiate strategy with strategy-specific config
            strategy = strategy_class(strategy_config)
            await strategy.initialize()
            
            logger.info(f"   ✅ Loaded strategy: {class_name}")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _run_strategy_backtest(self, strategy, backtester: ProfessionalBacktester,
                                    market_data: Dict[str, pd.DataFrame],
                                    regime_history: List[Tuple[datetime, MarketRegime]]) -> None:
        """Run strategy backtest"""
        
        try:
            # Get all timestamps (use first symbol as reference)
            primary_symbol = list(market_data.keys())[0]
            timestamps = market_data[primary_symbol].index
            
            regime_idx = 0
            
            for timestamp in timestamps:
                # Update current regime
                if regime_idx < len(regime_history) and timestamp >= regime_history[regime_idx][0]:
                    backtester.update_regime(regime_history[regime_idx][1], timestamp)
                    regime_idx = min(regime_idx + 1, len(regime_history) - 1)
                
                # Prepare current market data slice
                current_data = {}
                for symbol, data in market_data.items():
                    if timestamp in data.index:
                        current_data[symbol] = data.loc[:timestamp]
                
                # Generate signals from strategy
                signals = await strategy.generate_signals(current_data)
                
                # Execute signals
                current_prices = {symbol: data.loc[timestamp, 'close'] 
                                 for symbol, data in market_data.items() 
                                 if timestamp in data.index}
                
                for signal in signals:
                    signal_dict = {
                        'symbol': signal.symbol,
                        'side': signal.signal_type.value,
                        'quantity': signal.target_quantity,
                        'confidence': signal.confidence,
                        'strategy_id': strategy.strategy_id
                    }
                    
                    price = current_prices.get(signal.symbol)
                    if price:
                        backtester.execute_trade(signal_dict, price, timestamp)
                
                # Update equity
                backtester.update_equity(timestamp, current_prices)
            
        except Exception as e:
            logger.error(f"Backtest execution failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _analyze_signal_quality(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze signal quality metrics"""
        
        if not trades:
            return {
                'total_signals': 0,
                'signal_accuracy': 0.0,
                'avg_signal_confidence': 0.0,
                'false_positive_rate': 0.0,
                'signal_consistency': 0.0
            }
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        # Calculate signal accuracy
        signal_accuracy = len(winning_trades) / len(trades) if trades else 0
        
        # Average signal confidence
        avg_confidence = np.mean([t.signal_confidence for t in trades])
        
        # False positive rate (high confidence but lost)
        high_confidence_losses = [t for t in losing_trades if t.signal_confidence > 0.7]
        false_positive_rate = len(high_confidence_losses) / len(trades) if trades else 0
        
        # Signal consistency (correlation between confidence and outcome)
        confidences = [t.signal_confidence for t in trades]
        outcomes = [1 if t.pnl > 0 else 0 for t in trades]
        signal_consistency = np.corrcoef(confidences, outcomes)[0, 1] if len(trades) > 1 else 0
        
        return {
            'total_signals': len(trades),
            'signal_accuracy': signal_accuracy,
            'avg_signal_confidence': avg_confidence,
            'false_positive_rate': false_positive_rate,
            'signal_consistency': signal_consistency,
            'high_confidence_wins': len([t for t in winning_trades if t.signal_confidence > 0.7]),
            'low_confidence_losses': len([t for t in losing_trades if t.signal_confidence < 0.5])
        }
    
    def _analyze_regime_performance(self, trades: List[Trade], 
                                   regime_history: List[Tuple[datetime, MarketRegime]]) -> Dict[str, Any]:
        """Analyze performance by market regime"""
        
        regime_stats = {}
        
        for regime in MarketRegime:
            regime_trades = [t for t in trades if t.regime == regime.value]
            
            if regime_trades:
                regime_pnl = sum([t.pnl for t in regime_trades])
                regime_win_rate = len([t for t in regime_trades if t.pnl > 0]) / len(regime_trades)
                avg_return = np.mean([t.pnl_pct for t in regime_trades])
                
                regime_stats[regime.value] = {
                    'trade_count': len(regime_trades),
                    'total_pnl': regime_pnl,
                    'win_rate': regime_win_rate,
                    'avg_return_pct': avg_return * 100,
                    'best_trade': max([t.pnl for t in regime_trades]),
                    'worst_trade': min([t.pnl for t in regime_trades])
                }
            else:
                regime_stats[regime.value] = {
                    'trade_count': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0,
                    'avg_return_pct': 0.0,
                    'best_trade': 0.0,
                    'worst_trade': 0.0
                }
        
        return regime_stats
    
    def _grade_strategy_performance(self, metrics: PerformanceMetrics) -> Tuple[str, str, int]:
        """Grade strategy performance and determine alpha potential"""
        
        # Calculate composite score
        sharpe_score = min(metrics.sharpe_ratio / 2.0, 1.0) * 30  # Max 30 points
        return_score = min(metrics.annualized_return / 0.25, 1.0) * 25  # Max 25 points
        drawdown_score = max(0, (0.20 - metrics.max_drawdown) / 0.20) * 20  # Max 20 points
        win_rate_score = min(metrics.win_rate / 0.65, 1.0) * 15  # Max 15 points
        profit_factor_score = min(metrics.profit_factor / 2.5, 1.0) * 10  # Max 10 points
        
        total_score = sharpe_score + return_score + drawdown_score + win_rate_score + profit_factor_score
        
        # Determine grade
        if total_score >= 85:
            grade = "A"
            alpha_potential = "VERY HIGH"
            priority = 1
        elif total_score >= 75:
            grade = "B"
            alpha_potential = "HIGH"
            priority = 2
        elif total_score >= 65:
            grade = "C"
            alpha_potential = "MEDIUM-HIGH"
            priority = 3
        elif total_score >= 50:
            grade = "D"
            alpha_potential = "MEDIUM"
            priority = 4
        else:
            grade = "F"
            alpha_potential = "LOW"
            priority = 5
        
        return grade, alpha_potential, priority
    
    def _generate_recommendations(self, metrics: PerformanceMetrics,
                                 signal_quality: Dict[str, Any],
                                 regime_performance: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
        """Generate strengths, weaknesses, and optimization recommendations"""
        
        strengths = []
        weaknesses = []
        recommendations = []
        
        # Analyze Sharpe Ratio
        if metrics.sharpe_ratio > 1.5:
            strengths.append(f"Excellent risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})")
        elif metrics.sharpe_ratio < 0.8:
            weaknesses.append(f"Low risk-adjusted returns (Sharpe: {metrics.sharpe_ratio:.2f})")
            recommendations.append("Focus on improving signal quality and reducing false positives")
        
        # Analyze Win Rate
        if metrics.win_rate > 0.60:
            strengths.append(f"High win rate ({metrics.win_rate*100:.1f}%)")
        elif metrics.win_rate < 0.50:
            weaknesses.append(f"Low win rate ({metrics.win_rate*100:.1f}%)")
            recommendations.append("Implement more stringent entry filters to improve signal accuracy")
        
        # Analyze Drawdown
        if metrics.max_drawdown < 0.12:
            strengths.append(f"Low maximum drawdown ({metrics.max_drawdown*100:.1f}%)")
        elif metrics.max_drawdown > 0.20:
            weaknesses.append(f"High maximum drawdown ({metrics.max_drawdown*100:.1f}%)")
            recommendations.append("Implement dynamic position sizing and tighter stop losses")
        
        # Analyze Profit Factor
        if metrics.profit_factor > 2.0:
            strengths.append(f"Strong profit factor ({metrics.profit_factor:.2f})")
        elif metrics.profit_factor < 1.5:
            weaknesses.append(f"Weak profit factor ({metrics.profit_factor:.2f})")
            recommendations.append("Optimize exit timing to maximize winners and minimize losers")
        
        # Analyze Signal Quality
        if signal_quality['signal_accuracy'] > 0.60:
            strengths.append(f"High signal accuracy ({signal_quality['signal_accuracy']*100:.1f}%)")
        else:
            weaknesses.append(f"Low signal accuracy ({signal_quality['signal_accuracy']*100:.1f}%)")
            recommendations.append("Enhance signal generation logic with additional filters")
        
        # Analyze Regime Performance
        regime_analysis = self._analyze_regime_consistency(regime_performance)
        if regime_analysis['consistent']:
            strengths.append("Consistent performance across market regimes")
        else:
            weaknesses.append(f"Inconsistent regime performance (weak in {', '.join(regime_analysis['weak_regimes'])})")
            recommendations.append(f"Optimize strategy parameters for {', '.join(regime_analysis['weak_regimes'])} markets")
        
        return strengths, weaknesses, recommendations
    
    def _analyze_regime_consistency(self, regime_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze regime performance consistency"""
        
        regime_returns = []
        weak_regimes = []
        
        for regime, stats in regime_performance.items():
            if stats['trade_count'] > 0:
                regime_returns.append(stats['avg_return_pct'])
                if stats['avg_return_pct'] < 0:
                    weak_regimes.append(regime)
        
        if regime_returns:
            consistency = np.std(regime_returns) < 5.0  # Standard deviation < 5%
        else:
            consistency = False
        
        return {
            'consistent': consistency,
            'weak_regimes': weak_regimes,
            'return_volatility': np.std(regime_returns) if regime_returns else 0
        }
    
    def _print_strategy_analysis(self, result: StrategyTestResult) -> None:
        """Print strategy analysis summary"""
        
        print(f"\n{'='*80}")
        print(f"STRATEGY ANALYSIS: {result.strategy_name}")
        print(f"{'='*80}")
        print(f"\n📊 Overall Assessment:")
        print(f"   Grade:              {result.overall_grade}")
        print(f"   Alpha Potential:    {result.alpha_potential}")
        print(f"   Priority:           {result.optimization_priority}")
        print(f"\n💪 Strengths:")
        for strength in result.strengths:
            print(f"   ✅ {strength}")
        print(f"\n⚠️  Weaknesses:")
        for weakness in result.weaknesses:
            print(f"   ❌ {weakness}")
        print(f"\n🔧 Optimization Recommendations:")
        for i, rec in enumerate(result.optimization_recommendations, 1):
            print(f"   {i}. {rec}")
        print(f"\n{'='*80}\n")
    
    def _save_test_result(self, result: StrategyTestResult) -> None:
        """Save test result to file"""
        
        result_file = self.output_dir / f"{result.strategy_type}_test_result.json"
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"💾 Test result saved: {result_file}")
    
    async def test_all_strategies(self, base_config: Dict[str, Any]) -> Dict[str, StrategyTestResult]:
        """Test all 10 strategies"""
        
        logger.info(f"\n{'='*80}")
        logger.info(f"COMPREHENSIVE STRATEGY ASSESSMENT - PHASE 1")
        logger.info(f"{'='*80}\n")
        
        # Define all 10 strategies
        strategies_to_test = [
            {
                'strategy_type': 'statistical_arbitrage',
                'strategy_name': 'Enhanced Statistical Arbitrage',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'momentum',
                'strategy_name': 'Enhanced Momentum',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'mean_reversion',
                'strategy_name': 'Enhanced Mean Reversion',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'pairs_trading',
                'strategy_name': 'Enhanced Pairs Trading',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'breakout',
                'strategy_name': 'Enhanced Breakout',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'trend_following',
                'strategy_name': 'Enhanced Trend Following',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'volatility',
                'strategy_name': 'Enhanced Volatility',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'arbitrage',
                'strategy_name': 'Enhanced Arbitrage',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'factor',
                'strategy_name': 'Enhanced Factor',
                'strategy_config': base_config
            },
            {
                'strategy_type': 'multi_asset',
                'strategy_name': 'Enhanced Multi-Asset',
                'strategy_config': base_config
            }
        ]
        
        results = {}
        
        for strategy_info in strategies_to_test:
            test_config = StrategyTestConfig(
                **strategy_info,
                symbols=base_config.get('symbols', ['NVDA', 'TSLA', 'AAPL']),
                start_date=base_config.get('start_date', '2022-01-01'),
                end_date=base_config.get('end_date', '2024-12-31'),
                initial_capital=base_config.get('initial_capital', 100000.0)
            )
            
            result = await self.test_strategy(test_config)
            if result:
                results[strategy_info['strategy_type']] = result
        
        # Generate comprehensive report
        self._generate_comprehensive_report(results)
        
        return results
    
    def _generate_comprehensive_report(self, results: Dict[str, StrategyTestResult]) -> None:
        """Generate comprehensive assessment report"""
        
        # Sort by priority
        sorted_results = sorted(results.items(), key=lambda x: x[1].optimization_priority)
        
        print(f"\n{'='*80}")
        print(f"PHASE 1 COMPREHENSIVE ASSESSMENT REPORT")
        print(f"{'='*80}\n")
        
        print("📊 Strategy Performance Ranking:")
        print(f"{'Rank':<6} {'Strategy':<30} {'Grade':<8} {'Alpha':<15} {'Sharpe':<10}")
        print(f"{'-'*80}")
        
        for rank, (strategy_type, result) in enumerate(sorted_results, 1):
            sharpe = result.performance_metrics.get('sharpe_ratio', 0)
            print(f"{rank:<6} {result.strategy_name:<30} {result.overall_grade:<8} "
                  f"{result.alpha_potential:<15} {sharpe:>8.2f}")
        
        print(f"\n{'='*80}\n")
        
        # Save comprehensive report
        report = {
            'assessment_date': datetime.now().isoformat(),
            'total_strategies_tested': len(results),
            'strategy_rankings': [
                {
                    'rank': i + 1,
                    'strategy_type': strategy_type,
                    'strategy_name': result.strategy_name,
                    'grade': result.overall_grade,
                    'alpha_potential': result.alpha_potential,
                    'priority': result.optimization_priority,
                    'sharpe_ratio': result.performance_metrics.get('sharpe_ratio', 0),
                    'annual_return': result.performance_metrics.get('annualized_return', 0),
                    'max_drawdown': result.performance_metrics.get('max_drawdown', 0)
                }
                for i, (strategy_type, result) in enumerate(sorted_results)
            ]
        }
        
        report_file = self.output_dir / "phase1_comprehensive_assessment.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Comprehensive report saved: {report_file}")


# Export key classes
__all__ = [
    'ComprehensiveStrategyTester',
    'StrategyTestConfig',
    'StrategyTestResult'
]
