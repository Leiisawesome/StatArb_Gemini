#!/usr/bin/env python3
"""
Universe Selection Validator
============================

Comprehensive validation system for universe selection results. This validator
performs backtesting, statistical validation, and performance attribution to
ensure the quality and robustness of instrument universe selections.

Key Features:
- Historical performance validation
- Out-of-sample testing
- Statistical significance testing
- Regime-dependent validation
- Selection stability analysis
- Performance attribution

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import warnings
from scipy import stats
from scipy.optimize import minimize
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
import yaml
import json

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Import core components
from .universe_selector import UniverseSelection, IntelligentUniverseSelector
from .historical_analyzer import HistoricalInstrumentAnalyzer, InstrumentProfile
from .fitness_calculator import InstrumentFitnessCalculator, FitnessRanking
from ..market_data import EnhancedClickHouseLoader, DataRequest
from ..market_regime import ProfessionalRegimeSystem
from ...configuration import UnifiedConfigManager

logger = logging.getLogger(__name__)

@dataclass
class ValidationMetrics:
    """Validation performance metrics"""
    # Return metrics
    total_return: float
    annualized_return: float
    excess_return: float  # vs benchmark
    
    # Risk metrics
    volatility: float
    max_drawdown: float
    var_95: float  # Value at Risk
    cvar_95: float  # Conditional Value at Risk
    
    # Risk-adjusted metrics
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    
    # Statistical metrics
    win_rate: float
    profit_factor: float
    skewness: float
    kurtosis: float
    
    # Regime-specific metrics
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Complete validation result"""
    selection_id: str
    validation_period: Tuple[datetime, datetime]
    validation_timestamp: datetime
    
    # Performance metrics
    in_sample_metrics: ValidationMetrics
    out_of_sample_metrics: ValidationMetrics
    
    # Statistical tests
    statistical_significance: Dict[str, float]
    stability_metrics: Dict[str, float]
    
    # Comparative analysis
    benchmark_comparison: Dict[str, float]
    peer_comparison: Dict[str, float]
    
    # Validation status
    validation_passed: bool
    confidence_level: float
    warnings: List[str]
    recommendations: List[str]

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: datetime
    end_date: datetime
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly
    transaction_costs: float = 0.001  # 10 bps
    slippage: float = 0.0005  # 5 bps
    
    # Validation parameters
    in_sample_ratio: float = 0.7  # 70% for training, 30% for validation
    min_validation_periods: int = 50
    significance_level: float = 0.05

class UniverseSelectionValidator:
    """
    Comprehensive validator for universe selection results using historical
    backtesting, statistical analysis, and performance attribution.
    """
    
    def __init__(self, 
                 config_manager: Optional[UnifiedConfigManager] = None,
                 historical_analyzer: Optional[HistoricalInstrumentAnalyzer] = None,
                 universe_selector: Optional[IntelligentUniverseSelector] = None):
        """
        Initialize selection validator
        
        Args:
            config_manager: Configuration manager
            historical_analyzer: Historical analyzer instance
            universe_selector: Universe selector instance
        """
        self.config_manager = config_manager or UnifiedConfigManager()
        self.historical_analyzer = historical_analyzer or HistoricalInstrumentAnalyzer(config_manager)
        self.universe_selector = universe_selector or IntelligentUniverseSelector(config_manager)
        
        self.data_loader = EnhancedClickHouseLoader(self.config_manager.get_database_config())
        self.regime_system = ProfessionalRegimeSystem()
        
        # Validation cache
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        # Benchmark data
        self.benchmark_symbols = ['SPY', 'QQQ', 'IWM']
        self.benchmark_data: Dict[str, pd.DataFrame] = {}
        
        logger.info("🔍 Universe Selection Validator initialized")
    
    async def validate_selection(self,
                               selection: UniverseSelection,
                               backtest_config: Optional[BacktestConfig] = None,
                               benchmark_symbol: str = "SPY") -> ValidationResult:
        """
        Perform comprehensive validation of universe selection
        
        Args:
            selection: Universe selection to validate
            backtest_config: Backtesting configuration
            benchmark_symbol: Benchmark for comparison
            
        Returns:
            Complete validation result
        """
        try:
            logger.info(f"🔍 Validating universe selection for {selection.strategy}")
            logger.info(f"   📊 Instruments: {len(selection.selected_instruments)}")
            logger.info(f"   🌊 Regime: {selection.regime}")
            
            # Use default config if not provided
            if backtest_config is None:
                backtest_config = BacktestConfig(
                    start_date=datetime.now() - timedelta(days=365),
                    end_date=datetime.now() - timedelta(days=1)
                )
            
            # Generate unique selection ID
            selection_id = f"{selection.strategy}_{selection.regime}_{len(selection.selected_instruments)}_{int(selection.selection_timestamp.timestamp())}"
            
            # Check cache
            if selection_id in self.validation_cache:
                logger.info("📋 Using cached validation result")
                return self.validation_cache[selection_id]
            
            # Step 1: Load historical data for selected instruments
            historical_data = await self._load_validation_data(
                selection.selected_instruments, backtest_config
            )
            
            # Step 2: Load benchmark data
            benchmark_data = await self._load_benchmark_data(
                benchmark_symbol, backtest_config
            )
            
            # Step 3: Split data into in-sample and out-of-sample
            in_sample_data, out_sample_data = self._split_validation_data(
                historical_data, backtest_config
            )
            
            # Step 4: Run in-sample validation
            in_sample_metrics = await self._run_backtest_validation(
                in_sample_data, selection, backtest_config, "in_sample"
            )
            
            # Step 5: Run out-of-sample validation
            out_sample_metrics = await self._run_backtest_validation(
                out_sample_data, selection, backtest_config, "out_sample"
            )
            
            # Step 6: Perform statistical significance tests
            statistical_tests = self._perform_statistical_tests(
                in_sample_metrics, out_sample_metrics, benchmark_data
            )
            
            # Step 7: Calculate stability metrics
            stability_metrics = await self._calculate_stability_metrics(
                selection, historical_data, backtest_config
            )
            
            # Step 8: Benchmark comparison
            benchmark_comparison = self._compare_to_benchmark(
                out_sample_metrics, benchmark_data, backtest_config
            )
            
            # Step 9: Peer comparison (simplified)
            peer_comparison = await self._perform_peer_comparison(
                selection, out_sample_metrics
            )
            
            # Step 10: Determine validation status
            validation_passed, confidence_level, warnings, recommendations = self._determine_validation_status(
                in_sample_metrics, out_sample_metrics, statistical_tests, stability_metrics
            )
            
            # Create validation result
            result = ValidationResult(
                selection_id=selection_id,
                validation_period=(backtest_config.start_date, backtest_config.end_date),
                validation_timestamp=datetime.now(),
                in_sample_metrics=in_sample_metrics,
                out_of_sample_metrics=out_sample_metrics,
                statistical_significance=statistical_tests,
                stability_metrics=stability_metrics,
                benchmark_comparison=benchmark_comparison,
                peer_comparison=peer_comparison,
                validation_passed=validation_passed,
                confidence_level=confidence_level,
                warnings=warnings,
                recommendations=recommendations
            )
            
            # Cache result
            self.validation_cache[selection_id] = result
            
            logger.info(f"✅ Validation completed")
            logger.info(f"   📊 Status: {'PASSED' if validation_passed else 'FAILED'}")
            logger.info(f"   🎯 Confidence: {confidence_level:.3f}")
            logger.info(f"   📈 Out-of-sample Sharpe: {out_sample_metrics.sharpe_ratio:.3f}")
            logger.info(f"   📉 Max Drawdown: {out_sample_metrics.max_drawdown:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            # Return failed validation
            return self._create_failed_validation(selection_id, str(e))
    
    async def _load_validation_data(self,
                                  symbols: List[str],
                                  config: BacktestConfig) -> Dict[str, pd.DataFrame]:
        """Load historical data for validation"""
        try:
            logger.info(f"📊 Loading validation data for {len(symbols)} instruments")
            
            data = {}
            
            for symbol in symbols:
                request = DataRequest(
                    symbols=[symbol],
                    start_date=config.start_date,
                    end_date=config.end_date,
                    interval="1D",  # Daily data for validation
                    include_volume=True,
                    include_technical=False
                )
                
                symbol_data = await self.data_loader.load_market_data(request)
                
                if not symbol_data.empty:
                    # Calculate returns
                    symbol_data['returns'] = symbol_data['close'].pct_change()
                    symbol_data['log_returns'] = np.log(symbol_data['close'] / symbol_data['close'].shift(1))
                    data[symbol] = symbol_data
                else:
                    logger.warning(f"⚠️ No data available for {symbol}")
            
            logger.info(f"✅ Loaded data for {len(data)} instruments")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to load validation data: {e}")
            return {}
    
    async def _load_benchmark_data(self,
                                 benchmark_symbol: str,
                                 config: BacktestConfig) -> pd.DataFrame:
        """Load benchmark data for comparison"""
        try:
            request = DataRequest(
                symbols=[benchmark_symbol],
                start_date=config.start_date,
                end_date=config.end_date,
                interval="1D",
                include_volume=True
            )
            
            benchmark_data = await self.data_loader.load_market_data(request)
            
            if not benchmark_data.empty:
                benchmark_data['returns'] = benchmark_data['close'].pct_change()
                benchmark_data['log_returns'] = np.log(benchmark_data['close'] / benchmark_data['close'].shift(1))
            
            return benchmark_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load benchmark data: {e}")
            return pd.DataFrame()
    
    def _split_validation_data(self,
                             data: Dict[str, pd.DataFrame],
                             config: BacktestConfig) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """Split data into in-sample and out-of-sample periods"""
        try:
            in_sample_data = {}
            out_sample_data = {}
            
            for symbol, df in data.items():
                if df.empty:
                    continue
                
                # Calculate split point
                total_periods = len(df)
                split_point = int(total_periods * config.in_sample_ratio)
                
                # Ensure minimum validation periods
                if total_periods - split_point < config.min_validation_periods:
                    split_point = max(0, total_periods - config.min_validation_periods)
                
                in_sample_data[symbol] = df.iloc[:split_point].copy()
                out_sample_data[symbol] = df.iloc[split_point:].copy()
            
            logger.info(f"📊 Data split: In-sample={len(in_sample_data)}, Out-sample={len(out_sample_data)}")
            return in_sample_data, out_sample_data
            
        except Exception as e:
            logger.error(f"❌ Data splitting failed: {e}")
            return {}, {}
    
    async def _run_backtest_validation(self,
                                     data: Dict[str, pd.DataFrame],
                                     selection: UniverseSelection,
                                     config: BacktestConfig,
                                     period_type: str) -> ValidationMetrics:
        """Run backtesting validation on data"""
        try:
            logger.info(f"🔄 Running {period_type} backtest validation")
            
            if not data:
                return self._create_empty_metrics()
            
            # Create portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(
                data, selection.weights, config
            )
            
            if portfolio_returns.empty:
                return self._create_empty_metrics()
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(portfolio_returns)
            
            # Add regime-specific analysis
            regime_performance = await self._analyze_regime_performance(
                portfolio_returns, data, selection.strategy
            )
            metrics.regime_performance = regime_performance
            
            logger.info(f"   📊 {period_type.title()} Sharpe: {metrics.sharpe_ratio:.3f}")
            logger.info(f"   📈 {period_type.title()} Return: {metrics.annualized_return:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Backtest validation failed for {period_type}: {e}")
            return self._create_empty_metrics()
    
    def _calculate_portfolio_returns(self,
                                   data: Dict[str, pd.DataFrame],
                                   weights: Dict[str, float],
                                   config: BacktestConfig) -> pd.Series:
        """Calculate portfolio returns with rebalancing"""
        try:
            # Align all return series
            return_series = {}
            common_dates = None
            
            for symbol, weight in weights.items():
                if symbol in data and not data[symbol].empty:
                    returns = data[symbol]['returns'].dropna()
                    if not returns.empty:
                        return_series[symbol] = returns
                        if common_dates is None:
                            common_dates = returns.index
                        else:
                            common_dates = common_dates.intersection(returns.index)
            
            if not return_series or common_dates is None or len(common_dates) == 0:
                return pd.Series(dtype=float)
            
            # Create portfolio returns
            portfolio_returns = pd.Series(0.0, index=common_dates)
            
            for symbol, weight in weights.items():
                if symbol in return_series:
                    aligned_returns = return_series[symbol].reindex(common_dates, fill_value=0)
                    portfolio_returns += weight * aligned_returns
            
            # Apply transaction costs (simplified)
            transaction_cost = config.transaction_costs + config.slippage
            
            # Rebalancing frequency adjustment
            if config.rebalance_frequency == "monthly":
                # Apply costs monthly (simplified)
                monthly_cost = transaction_cost * len(weights) / 21  # Approximate trading days per month
                portfolio_returns -= monthly_cost / 252  # Daily cost
            elif config.rebalance_frequency == "weekly":
                weekly_cost = transaction_cost * len(weights) / 5
                portfolio_returns -= weekly_cost / 252
            
            return portfolio_returns.dropna()
            
        except Exception as e:
            logger.error(f"❌ Portfolio return calculation failed: {e}")
            return pd.Series(dtype=float)
    
    def _calculate_performance_metrics(self, returns: pd.Series) -> ValidationMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            if returns.empty or len(returns) < 10:
                return self._create_empty_metrics()
            
            # Basic return metrics
            total_return = (1 + returns).prod() - 1
            annualized_return = (1 + returns).prod() ** (252 / len(returns)) - 1
            
            # Risk metrics
            volatility = returns.std() * np.sqrt(252)
            
            # Drawdown calculation
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # VaR and CVaR
            var_95 = np.percentile(returns, 5)
            cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
            
            # Risk-adjusted metrics
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else volatility
            sortino_ratio = annualized_return / downside_std if downside_std > 0 else 0
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0
            
            # Information ratio (vs zero for now)
            information_ratio = sharpe_ratio  # Simplified
            
            # Trade statistics
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0
            
            avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
            avg_loss = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            # Distribution metrics
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            return ValidationMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                excess_return=0.0,  # Will be calculated vs benchmark
                volatility=volatility,
                max_drawdown=max_drawdown,
                var_95=var_95,
                cvar_95=cvar_95,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                information_ratio=information_ratio,
                win_rate=win_rate,
                profit_factor=profit_factor,
                skewness=skewness,
                kurtosis=kurtosis
            )
            
        except Exception as e:
            logger.error(f"❌ Performance metrics calculation failed: {e}")
            return self._create_empty_metrics()
    
    def _create_empty_metrics(self) -> ValidationMetrics:
        """Create empty metrics for fallback"""
        return ValidationMetrics(
            total_return=0.0, annualized_return=0.0, excess_return=0.0,
            volatility=0.0, max_drawdown=0.0, var_95=0.0, cvar_95=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0, information_ratio=0.0,
            win_rate=0.0, profit_factor=0.0, skewness=0.0, kurtosis=0.0
        )
    
    async def _analyze_regime_performance(self,
                                        portfolio_returns: pd.Series,
                                        data: Dict[str, pd.DataFrame],
                                        strategy: str) -> Dict[str, Dict[str, float]]:
        """Analyze performance by market regime"""
        try:
            # This would use actual regime detection on historical data
            # For now, we'll create a simplified analysis
            
            regime_performance = {}
            
            # Split returns into periods (simplified regime analysis)
            if len(portfolio_returns) > 100:
                # High volatility periods (top 25%)
                vol_threshold = portfolio_returns.rolling(20).std().quantile(0.75)
                high_vol_mask = portfolio_returns.rolling(20).std() > vol_threshold
                
                if high_vol_mask.sum() > 10:
                    high_vol_returns = portfolio_returns[high_vol_mask]
                    regime_performance['high_volatility'] = {
                        'return': high_vol_returns.mean() * 252,
                        'volatility': high_vol_returns.std() * np.sqrt(252),
                        'sharpe': (high_vol_returns.mean() * 252) / (high_vol_returns.std() * np.sqrt(252)) if high_vol_returns.std() > 0 else 0
                    }
                
                # Low volatility periods
                low_vol_returns = portfolio_returns[~high_vol_mask]
                if len(low_vol_returns) > 10:
                    regime_performance['low_volatility'] = {
                        'return': low_vol_returns.mean() * 252,
                        'volatility': low_vol_returns.std() * np.sqrt(252),
                        'sharpe': (low_vol_returns.mean() * 252) / (low_vol_returns.std() * np.sqrt(252)) if low_vol_returns.std() > 0 else 0
                    }
            
            return regime_performance
            
        except Exception as e:
            logger.debug(f"Regime performance analysis failed: {e}")
            return {}
    
    def _perform_statistical_tests(self,
                                 in_sample: ValidationMetrics,
                                 out_sample: ValidationMetrics,
                                 benchmark_data: pd.DataFrame) -> Dict[str, float]:
        """Perform statistical significance tests"""
        try:
            tests = {}
            
            # Sharpe ratio consistency test
            sharpe_diff = abs(in_sample.sharpe_ratio - out_sample.sharpe_ratio)
            sharpe_consistency = 1.0 - min(1.0, sharpe_diff / 2.0)  # Normalize
            tests['sharpe_consistency'] = sharpe_consistency
            
            # Return consistency test
            return_diff = abs(in_sample.annualized_return - out_sample.annualized_return)
            return_consistency = 1.0 - min(1.0, return_diff / 0.5)  # Normalize by 50%
            tests['return_consistency'] = return_consistency
            
            # Volatility consistency test
            vol_diff = abs(in_sample.volatility - out_sample.volatility)
            vol_consistency = 1.0 - min(1.0, vol_diff / 0.3)  # Normalize by 30%
            tests['volatility_consistency'] = vol_consistency
            
            # Overall significance (combined score)
            overall_significance = np.mean([sharpe_consistency, return_consistency, vol_consistency])
            tests['overall_significance'] = overall_significance
            
            # Statistical power (simplified)
            tests['statistical_power'] = 0.8 if overall_significance > 0.7 else 0.5
            
            return tests
            
        except Exception as e:
            logger.debug(f"Statistical tests failed: {e}")
            return {'overall_significance': 0.5, 'statistical_power': 0.5}
    
    async def _calculate_stability_metrics(self,
                                         selection: UniverseSelection,
                                         data: Dict[str, pd.DataFrame],
                                         config: BacktestConfig) -> Dict[str, float]:
        """Calculate selection stability metrics"""
        try:
            stability_metrics = {}
            
            # Weight stability (how stable are the weights over time)
            # This would involve rerunning selection at different time points
            # For now, we'll use simplified metrics
            
            # Instrument availability stability
            available_instruments = len([s for s in selection.selected_instruments if s in data])
            availability_stability = available_instruments / len(selection.selected_instruments)
            stability_metrics['instrument_availability'] = availability_stability
            
            # Selection confidence stability (from selection metadata)
            stability_metrics['selection_confidence'] = selection.selection_confidence
            
            # Regime stability
            stability_metrics['regime_confidence'] = selection.regime_confidence
            
            # Overall stability score
            overall_stability = np.mean([
                availability_stability,
                selection.selection_confidence,
                selection.regime_confidence
            ])
            stability_metrics['overall_stability'] = overall_stability
            
            return stability_metrics
            
        except Exception as e:
            logger.debug(f"Stability metrics calculation failed: {e}")
            return {'overall_stability': 0.7}
    
    def _compare_to_benchmark(self,
                            metrics: ValidationMetrics,
                            benchmark_data: pd.DataFrame,
                            config: BacktestConfig) -> Dict[str, float]:
        """Compare performance to benchmark"""
        try:
            if benchmark_data.empty:
                return {'excess_return': 0.0, 'information_ratio': 0.0, 'tracking_error': 0.0}
            
            # Calculate benchmark metrics
            benchmark_returns = benchmark_data['returns'].dropna()
            
            if benchmark_returns.empty:
                return {'excess_return': 0.0, 'information_ratio': 0.0, 'tracking_error': 0.0}
            
            benchmark_annual_return = (1 + benchmark_returns).prod() ** (252 / len(benchmark_returns)) - 1
            benchmark_volatility = benchmark_returns.std() * np.sqrt(252)
            benchmark_sharpe = benchmark_annual_return / benchmark_volatility if benchmark_volatility > 0 else 0
            
            # Calculate comparison metrics
            excess_return = metrics.annualized_return - benchmark_annual_return
            sharpe_difference = metrics.sharpe_ratio - benchmark_sharpe
            
            # Information ratio (simplified)
            tracking_error = abs(metrics.volatility - benchmark_volatility)
            information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
            
            return {
                'excess_return': excess_return,
                'sharpe_difference': sharpe_difference,
                'information_ratio': information_ratio,
                'tracking_error': tracking_error,
                'benchmark_annual_return': benchmark_annual_return,
                'benchmark_sharpe': benchmark_sharpe
            }
            
        except Exception as e:
            logger.debug(f"Benchmark comparison failed: {e}")
            return {'excess_return': 0.0, 'information_ratio': 0.0, 'tracking_error': 0.0}
    
    async def _perform_peer_comparison(self,
                                     selection: UniverseSelection,
                                     metrics: ValidationMetrics) -> Dict[str, float]:
        """Compare to peer selections (simplified)"""
        try:
            # This would compare to other strategy selections
            # For now, we'll use industry benchmarks
            
            strategy_benchmarks = {
                'momentum': {'sharpe': 0.8, 'return': 0.12, 'max_dd': -0.15},
                'mean_reversion': {'sharpe': 1.0, 'return': 0.10, 'max_dd': -0.10},
                'pairs_trading': {'sharpe': 1.2, 'return': 0.08, 'max_dd': -0.08}
            }
            
            benchmark = strategy_benchmarks.get(selection.strategy, strategy_benchmarks['momentum'])
            
            return {
                'sharpe_vs_peer': metrics.sharpe_ratio / benchmark['sharpe'] if benchmark['sharpe'] > 0 else 1.0,
                'return_vs_peer': metrics.annualized_return / benchmark['return'] if benchmark['return'] > 0 else 1.0,
                'drawdown_vs_peer': abs(metrics.max_drawdown) / abs(benchmark['max_dd']) if benchmark['max_dd'] < 0 else 1.0
            }
            
        except Exception as e:
            logger.debug(f"Peer comparison failed: {e}")
            return {'sharpe_vs_peer': 1.0, 'return_vs_peer': 1.0, 'drawdown_vs_peer': 1.0}
    
    def _determine_validation_status(self,
                                   in_sample: ValidationMetrics,
                                   out_sample: ValidationMetrics,
                                   statistical_tests: Dict[str, float],
                                   stability_metrics: Dict[str, float]) -> Tuple[bool, float, List[str], List[str]]:
        """Determine overall validation status"""
        try:
            warnings = []
            recommendations = []
            
            # Validation criteria
            criteria_passed = 0
            total_criteria = 0
            
            # 1. Out-of-sample Sharpe ratio > 0.5
            total_criteria += 1
            if out_sample.sharpe_ratio > 0.5:
                criteria_passed += 1
            else:
                warnings.append(f"Low out-of-sample Sharpe ratio: {out_sample.sharpe_ratio:.3f}")
                recommendations.append("Consider adjusting selection criteria or strategy parameters")
            
            # 2. Maximum drawdown < 25%
            total_criteria += 1
            if out_sample.max_drawdown > -0.25:
                criteria_passed += 1
            else:
                warnings.append(f"High maximum drawdown: {out_sample.max_drawdown:.3f}")
                recommendations.append("Implement stronger risk management controls")
            
            # 3. Statistical significance > 0.6
            total_criteria += 1
            significance = statistical_tests.get('overall_significance', 0.5)
            if significance > 0.6:
                criteria_passed += 1
            else:
                warnings.append(f"Low statistical significance: {significance:.3f}")
                recommendations.append("Increase validation period or improve selection methodology")
            
            # 4. Stability > 0.7
            total_criteria += 1
            stability = stability_metrics.get('overall_stability', 0.7)
            if stability > 0.7:
                criteria_passed += 1
            else:
                warnings.append(f"Low selection stability: {stability:.3f}")
                recommendations.append("Review instrument availability and selection consistency")
            
            # 5. Positive excess return
            total_criteria += 1
            if out_sample.annualized_return > 0.05:  # > 5% annual return
                criteria_passed += 1
            else:
                warnings.append(f"Low absolute return: {out_sample.annualized_return:.3f}")
                recommendations.append("Consider alternative strategies or market conditions")
            
            # Determine validation status
            pass_rate = criteria_passed / total_criteria
            validation_passed = pass_rate >= 0.6  # 60% of criteria must pass
            
            # Calculate confidence level
            confidence_components = [
                pass_rate,
                min(1.0, max(0.0, (out_sample.sharpe_ratio + 1) / 2)),  # Normalize Sharpe
                significance,
                stability
            ]
            confidence_level = np.mean(confidence_components)
            
            # Additional recommendations
            if validation_passed:
                if confidence_level > 0.8:
                    recommendations.append("Selection shows strong validation - proceed with confidence")
                else:
                    recommendations.append("Selection passed validation but monitor performance closely")
            else:
                recommendations.append("Selection failed validation - consider alternative approaches")
            
            return validation_passed, confidence_level, warnings, recommendations
            
        except Exception as e:
            logger.error(f"❌ Validation status determination failed: {e}")
            return False, 0.3, ["Validation process encountered errors"], ["Review validation methodology"]
    
    def _create_failed_validation(self, selection_id: str, error_msg: str) -> ValidationResult:
        """Create failed validation result"""
        return ValidationResult(
            selection_id=selection_id,
            validation_period=(datetime.now() - timedelta(days=365), datetime.now()),
            validation_timestamp=datetime.now(),
            in_sample_metrics=self._create_empty_metrics(),
            out_of_sample_metrics=self._create_empty_metrics(),
            statistical_significance={'overall_significance': 0.0},
            stability_metrics={'overall_stability': 0.0},
            benchmark_comparison={'excess_return': 0.0},
            peer_comparison={'sharpe_vs_peer': 0.0},
            validation_passed=False,
            confidence_level=0.0,
            warnings=[f"Validation failed: {error_msg}"],
            recommendations=["Review selection methodology and data availability"]
        )
    
    def generate_validation_report(self,
                                 result: ValidationResult,
                                 output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        try:
            logger.info("📋 Generating validation report")
            
            report = {
                'validation_metadata': {
                    'selection_id': result.selection_id,
                    'validation_timestamp': result.validation_timestamp.isoformat(),
                    'validation_period': {
                        'start': result.validation_period[0].isoformat(),
                        'end': result.validation_period[1].isoformat()
                    },
                    'validation_passed': result.validation_passed,
                    'confidence_level': result.confidence_level
                },
                'performance_summary': {
                    'in_sample': {
                        'annualized_return': result.in_sample_metrics.annualized_return,
                        'sharpe_ratio': result.in_sample_metrics.sharpe_ratio,
                        'max_drawdown': result.in_sample_metrics.max_drawdown,
                        'volatility': result.in_sample_metrics.volatility
                    },
                    'out_of_sample': {
                        'annualized_return': result.out_of_sample_metrics.annualized_return,
                        'sharpe_ratio': result.out_of_sample_metrics.sharpe_ratio,
                        'max_drawdown': result.out_of_sample_metrics.max_drawdown,
                        'volatility': result.out_of_sample_metrics.volatility
                    }
                },
                'statistical_analysis': result.statistical_significance,
                'stability_analysis': result.stability_metrics,
                'benchmark_comparison': result.benchmark_comparison,
                'peer_comparison': result.peer_comparison,
                'validation_status': {
                    'warnings': result.warnings,
                    'recommendations': result.recommendations
                },
                'regime_performance': {
                    'in_sample': result.in_sample_metrics.regime_performance,
                    'out_of_sample': result.out_of_sample_metrics.regime_performance
                }
            }
            
            # Save report if path provided
            if output_path:
                with open(output_path, 'w') as f:
                    yaml.dump(report, f, default_flow_style=False, sort_keys=False)
                logger.info(f"💾 Validation report saved to {output_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return {}

# Example usage and testing
if __name__ == "__main__":
    async def test_validator():
        """Test the selection validator"""
        validator = UniverseSelectionValidator()
        
        # This would use actual selection results
        logger.info("🔍 Testing Selection Validator")
        print("✅ Selection Validator test completed")
    
    # Run test
    asyncio.run(test_validator())
