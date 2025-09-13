#!/usr/bin/env python3
"""
Backtest Configuration Generator
===============================

Generates optimized, baseline, and stress test configurations
based on historical analysis results for systematic backtesting.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import asdict
import json
from pathlib import Path
import itertools
from scipy.optimize import minimize
import uuid

from .data_types import (
    InstrumentRankings, RegimeAnalysisOutput, BacktestConfig,
    BacktestSuite, InstrumentScore
)

# Import from existing strategy system
from ..market_condition_analytics import MarketCondition, StrategyType

# Configure logging
logger = logging.getLogger(__name__)


class BacktestConfigGenerator:
    """
    Advanced generator for backtest configurations based on historical analysis
    """
    
    def __init__(self, max_instruments_per_config: int = 20,
                 min_instruments_per_config: int = 5,
                 enable_portfolio_optimization: bool = True):
        """
        Initialize the config generator
        
        Args:
            max_instruments_per_config: Maximum instruments per backtest
            min_instruments_per_config: Minimum instruments per backtest
            enable_portfolio_optimization: Whether to optimize portfolio weights
        """
        self.max_instruments_per_config = max_instruments_per_config
        self.min_instruments_per_config = min_instruments_per_config
        self.enable_portfolio_optimization = enable_portfolio_optimization
        
        # Configuration generation parameters
        self.top_performers_ratio = 0.3  # Use top 30% of performers
        self.diversification_factor = 0.8  # Balance between performance and diversification
        
        # Risk management parameters
        self.max_position_size = 0.1  # 10% max position size
        self.max_sector_concentration = 0.3  # 30% max sector concentration
        self.volatility_target = 0.15  # 15% target volatility
        
        # Strategy-specific parameters
        self.strategy_parameters = self._initialize_strategy_parameters()
        
        logger.info(f"BacktestConfigGenerator initialized with {max_instruments_per_config} max instruments")
    
    def generate_comprehensive_suite(self, 
                                   regime_analysis: RegimeAnalysisOutput,
                                   rankings: InstrumentRankings,
                                   target_regimes: Optional[List[str]] = None) -> BacktestSuite:
        """
        Generate a comprehensive suite of backtest configurations
        
        Args:
            regime_analysis: Complete regime analysis output
            rankings: Instrument rankings across strategies/regimes
            target_regimes: Optional list of regimes to focus on
            
        Returns:
            Complete backtest suite with optimized, baseline, and stress configs
        """
        logger.info("Generating comprehensive backtest configuration suite")
        
        if target_regimes is None:
            target_regimes = list(regime_analysis.regime_distribution.keys())
        
        # Generate different types of configurations
        optimized_configs = self._generate_optimized_configs(rankings, target_regimes)
        baseline_configs = self._generate_baseline_configs(rankings, target_regimes)
        stress_configs = self._generate_stress_configs(rankings, regime_analysis, target_regimes)
        
        # Prepare suite metadata
        suite_metadata = {
            'generation_timestamp': datetime.now().isoformat(),
            'total_configs_generated': len(optimized_configs) + len(baseline_configs) + len(stress_configs),
            'target_regimes': target_regimes,
            'strategies_included': list(rankings.strategy_rankings.keys()),
            'configuration_parameters': {
                'max_instruments_per_config': self.max_instruments_per_config,
                'min_instruments_per_config': self.min_instruments_per_config,
                'portfolio_optimization_enabled': self.enable_portfolio_optimization,
                'top_performers_ratio': self.top_performers_ratio
            }
        }
        
        # Create backtest suite
        suite = BacktestSuite(
            optimized_configs=optimized_configs,
            baseline_configs=baseline_configs,
            stress_configs=stress_configs,
            suite_metadata=suite_metadata
        )
        
        # Validate suite
        self._validate_backtest_suite(suite)
        
        logger.info(
            f"Generated {suite.total_configs} backtest configurations: "
            f"{len(optimized_configs)} optimized, {len(baseline_configs)} baseline, "
            f"{len(stress_configs)} stress tests"
        )
        
        return suite
    
    def generate_regime_optimized_config(self, 
                                       strategy: str,
                                       regime: str,
                                       rankings: InstrumentRankings,
                                       optimization_objective: str = 'sharpe') -> BacktestConfig:
        """
        Generate a single optimized configuration for a specific strategy/regime
        
        Args:
            strategy: Strategy name
            regime: Target regime
            rankings: Instrument rankings
            optimization_objective: Optimization objective ('sharpe', 'return', 'risk_adjusted')
            
        Returns:
            Optimized backtest configuration
        """
        logger.info(f"Generating optimized config for {strategy}/{regime}")
        
        # Get top instruments for this strategy/regime
        top_instruments = rankings.get_top_instruments(strategy, regime, self.max_instruments_per_config * 2)
        
        if len(top_instruments) < self.min_instruments_per_config:
            raise ValueError(
                f"Insufficient instruments for {strategy}/{regime}: "
                f"{len(top_instruments)} < {self.min_instruments_per_config}"
            )
        
        # Select optimal instrument subset
        selected_instruments = self._select_optimal_instruments(
            top_instruments, optimization_objective
        )
        
        # Generate strategy parameters
        strategy_params = self._generate_strategy_parameters(strategy, regime, selected_instruments)
        
        # Generate risk parameters
        risk_params = self._generate_risk_parameters(selected_instruments, regime)
        
        # Create configuration
        config_id = str(uuid.uuid4())[:8]
        config = BacktestConfig(
            config_id=config_id,
            name=f"{strategy}_{regime}_optimized_{config_id}",
            strategy=strategy,
            instruments=[inst.symbol for inst in selected_instruments],
            regime_context=regime,
            parameters=strategy_params,
            risk_params=risk_params,
            metadata={
                'optimization_objective': optimization_objective,
                'generation_method': 'regime_optimized',
                'top_instrument_scores': [
                    {'symbol': inst.symbol, 'score': inst.composite_score}
                    for inst in selected_instruments[:5]
                ],
                'expected_performance': self._estimate_config_performance(selected_instruments)
            }
        )
        
        return config
    
    def optimize_portfolio_weights(self, instruments: List[InstrumentScore],
                                 optimization_method: str = 'mean_variance') -> Dict[str, float]:
        """
        Optimize portfolio weights for given instruments
        
        Args:
            instruments: List of instrument scores
            optimization_method: Optimization method to use
            
        Returns:
            Dictionary mapping symbols to optimal weights
        """
        if not self.enable_portfolio_optimization or len(instruments) < 2:
            # Equal weights if optimization disabled or insufficient instruments
            equal_weight = 1.0 / len(instruments)
            return {inst.symbol: equal_weight for inst in instruments}
        
        logger.debug(f"Optimizing portfolio weights for {len(instruments)} instruments")
        
        try:
            if optimization_method == 'mean_variance':
                return self._optimize_mean_variance(instruments)
            elif optimization_method == 'risk_parity':
                return self._optimize_risk_parity(instruments)
            elif optimization_method == 'max_sharpe':
                return self._optimize_max_sharpe(instruments)
            else:
                logger.warning(f"Unknown optimization method: {optimization_method}")
                return self._equal_weights(instruments)
                
        except Exception as e:
            logger.warning(f"Portfolio optimization failed: {e}")
            return self._equal_weights(instruments)
    
    def _generate_optimized_configs(self, rankings: InstrumentRankings,
                                  target_regimes: List[str]) -> List[BacktestConfig]:
        """Generate optimized configurations"""
        optimized_configs = []
        
        for strategy_name in rankings.strategy_rankings.keys():
            for regime in target_regimes:
                if regime in rankings.strategy_rankings[strategy_name]:
                    try:
                        # Generate multiple variants with different objectives
                        for objective in ['sharpe', 'return', 'risk_adjusted']:
                            config = self.generate_regime_optimized_config(
                                strategy_name, regime, rankings, objective
                            )
                            optimized_configs.append(config)
                            
                    except Exception as e:
                        logger.warning(f"Failed to generate optimized config for {strategy_name}/{regime}: {e}")
        
        return optimized_configs
    
    def _generate_baseline_configs(self, rankings: InstrumentRankings,
                                 target_regimes: List[str]) -> List[BacktestConfig]:
        """Generate baseline configurations for comparison"""
        baseline_configs = []
        
        for strategy_name in rankings.strategy_rankings.keys():
            for regime in target_regimes:
                if regime in rankings.strategy_rankings[strategy_name]:
                    try:
                        # Simple top-N selection without optimization
                        top_instruments = rankings.get_top_instruments(
                            strategy_name, regime, self.min_instruments_per_config + 5
                        )
                        
                        if len(top_instruments) >= self.min_instruments_per_config:
                            # Take top instruments without optimization
                            selected = top_instruments[:self.min_instruments_per_config]
                            
                            config_id = str(uuid.uuid4())[:8]
                            config = BacktestConfig(
                                config_id=config_id,
                                name=f"{strategy_name}_{regime}_baseline_{config_id}",
                                strategy=strategy_name,
                                instruments=[inst.symbol for inst in selected],
                                regime_context=regime,
                                parameters=self.strategy_parameters[strategy_name]['default'].copy(),
                                risk_params=self._generate_default_risk_parameters(),
                                config_type='baseline',
                                metadata={
                                    'generation_method': 'top_n_selection',
                                    'selection_criteria': 'composite_score',
                                    'num_instruments': len(selected)
                                }
                            )
                            
                            baseline_configs.append(config)
                            
                    except Exception as e:
                        logger.warning(f"Failed to generate baseline config for {strategy_name}/{regime}: {e}")
        
        return baseline_configs
    
    def _generate_stress_configs(self, rankings: InstrumentRankings,
                               regime_analysis: RegimeAnalysisOutput,
                               target_regimes: List[str]) -> List[BacktestConfig]:
        """Generate stress test configurations"""
        stress_configs = []
        
        for strategy_name in rankings.strategy_rankings.keys():
            for regime in target_regimes:
                if regime in rankings.strategy_rankings[strategy_name]:
                    try:
                        instruments = rankings.strategy_rankings[strategy_name][regime]
                        
                        if len(instruments) >= self.min_instruments_per_config:
                            # Different stress test scenarios
                            stress_scenarios = [
                                ('high_risk', self._select_high_risk_instruments),
                                ('low_sharpe', self._select_low_sharpe_instruments),
                                ('high_correlation', self._select_high_correlation_instruments),
                                ('bottom_performers', self._select_bottom_performers)
                            ]
                            
                            for scenario_name, selection_func in stress_scenarios:
                                try:
                                    selected = selection_func(instruments, self.min_instruments_per_config)
                                    
                                    if len(selected) >= self.min_instruments_per_config:
                                        config_id = str(uuid.uuid4())[:8]
                                        config = BacktestConfig(
                                            config_id=config_id,
                                            name=f"{strategy_name}_{regime}_{scenario_name}_{config_id}",
                                            strategy=strategy_name,
                                            instruments=[inst.symbol for inst in selected],
                                            regime_context=regime,
                                            parameters=self._generate_stress_parameters(strategy_name, scenario_name),
                                            risk_params=self._generate_stress_risk_parameters(scenario_name),
                                            config_type='stress',
                                            metadata={
                                                'stress_scenario': scenario_name,
                                                'generation_method': 'stress_testing',
                                                'expected_challenge': self._describe_stress_scenario(scenario_name)
                                            }
                                        )
                                        
                                        stress_configs.append(config)
                                        
                                except Exception as e:
                                    logger.warning(f"Failed to generate {scenario_name} stress config: {e}")
                                    
                    except Exception as e:
                        logger.warning(f"Failed to generate stress configs for {strategy_name}/{regime}: {e}")
        
        return stress_configs
    
    def _select_optimal_instruments(self, instruments: List[InstrumentScore],
                                  objective: str) -> List[InstrumentScore]:
        """Select optimal subset of instruments"""
        if len(instruments) <= self.max_instruments_per_config:
            return instruments
        
        # Sort by different criteria based on objective
        if objective == 'sharpe':
            sorted_instruments = sorted(instruments, key=lambda x: x.sharpe_ratio, reverse=True)
        elif objective == 'return':
            sorted_instruments = sorted(instruments, key=lambda x: x.expected_return, reverse=True)
        elif objective == 'risk_adjusted':
            # Balance return and risk
            sorted_instruments = sorted(
                instruments, 
                key=lambda x: x.expected_return / (1 + x.max_drawdown),
                reverse=True
            )
        else:
            # Default to composite score
            sorted_instruments = sorted(instruments, key=lambda x: x.composite_score, reverse=True)
        
        # Apply diversification filter
        selected = self._apply_diversification_filter(
            sorted_instruments[:int(self.max_instruments_per_config * 1.5)]
        )
        
        return selected[:self.max_instruments_per_config]
    
    def _apply_diversification_filter(self, instruments: List[InstrumentScore]) -> List[InstrumentScore]:
        """Apply diversification constraints to instrument selection"""
        # Simple diversification: avoid highly correlated instruments
        # In production, this would use actual correlation data
        
        selected = []
        sector_count = {}
        
        for instrument in instruments:
            # Simple sector classification based on symbol patterns
            sector = self._classify_instrument_sector(instrument.symbol)
            
            # Check sector concentration
            current_sector_weight = sector_count.get(sector, 0) / max(len(selected), 1)
            
            if current_sector_weight < self.max_sector_concentration or len(selected) < self.min_instruments_per_config:
                selected.append(instrument)
                sector_count[sector] = sector_count.get(sector, 0) + 1
                
                if len(selected) >= self.max_instruments_per_config:
                    break
        
        return selected
    
    def _generate_strategy_parameters(self, strategy: str, regime: str,
                                    instruments: List[InstrumentScore]) -> Dict[str, Any]:
        """Generate strategy-specific parameters"""
        base_params = self.strategy_parameters[strategy]['default'].copy()
        
        # Regime-specific adjustments
        if regime == 'high_volatility':
            # More conservative parameters for high volatility
            if 'lookback_period' in base_params:
                base_params['lookback_period'] = min(base_params['lookback_period'], 20)
            if 'rebalance_frequency' in base_params:
                base_params['rebalance_frequency'] = 'daily'
            base_params['volatility_adjustment'] = True
            
        elif regime == 'low_volatility':
            # More aggressive parameters for low volatility
            if 'lookback_period' in base_params:
                base_params['lookback_period'] = max(base_params['lookback_period'], 60)
            if 'rebalance_frequency' in base_params:
                base_params['rebalance_frequency'] = 'weekly'
            
        elif regime in ['bull_market', 'bear_market']:
            # Trend-following adjustments
            if 'momentum_window' in base_params:
                base_params['momentum_window'] = 20
            base_params['trend_following'] = True
        
        # Add instrument-specific parameters
        avg_volatility = np.mean([inst.volatility for inst in instruments])
        avg_sharpe = np.mean([inst.sharpe_ratio for inst in instruments])
        
        base_params.update({
            'portfolio_volatility_target': min(0.25, avg_volatility * 1.2),
            'expected_sharpe_target': max(0.5, avg_sharpe * 0.8),
            'instrument_count': len(instruments),
            'regime_context': regime
        })
        
        return base_params
    
    def _generate_risk_parameters(self, instruments: List[InstrumentScore], regime: str) -> Dict[str, Any]:
        """Generate risk management parameters"""
        # Calculate portfolio-level risk metrics
        avg_volatility = np.mean([inst.volatility for inst in instruments])
        max_individual_drawdown = max([inst.max_drawdown for inst in instruments])
        
        risk_params = {
            'max_position_size': min(self.max_position_size, 0.8 / len(instruments)),
            'portfolio_volatility_limit': min(0.3, avg_volatility * 1.5),
            'max_portfolio_drawdown': min(0.2, max_individual_drawdown * 0.8),
            'stop_loss_threshold': 0.05,  # 5% stop loss
            'rebalance_threshold': 0.02,  # 2% rebalance threshold
            'cash_buffer': 0.05,  # 5% cash buffer
            'correlation_limit': 0.8,  # Maximum correlation between positions
        }
        
        # Regime-specific risk adjustments
        if regime == 'high_volatility':
            risk_params['max_position_size'] *= 0.7  # Reduce position sizes
            risk_params['stop_loss_threshold'] = 0.03  # Tighter stops
            risk_params['cash_buffer'] = 0.1  # Higher cash buffer
            
        elif regime == 'low_volatility':
            risk_params['max_position_size'] *= 1.2  # Increase position sizes
            risk_params['stop_loss_threshold'] = 0.08  # Wider stops
            
        return risk_params
    
    def _generate_default_risk_parameters(self) -> Dict[str, Any]:
        """Generate default risk parameters"""
        return {
            'max_position_size': 0.05,
            'portfolio_volatility_limit': 0.20,
            'max_portfolio_drawdown': 0.15,
            'stop_loss_threshold': 0.05,
            'rebalance_threshold': 0.02,
            'cash_buffer': 0.05
        }
    
    def _generate_stress_parameters(self, strategy: str, scenario: str) -> Dict[str, Any]:
        """Generate parameters for stress testing scenarios"""
        base_params = self.strategy_parameters[strategy]['default'].copy()
        
        if scenario == 'high_risk':
            # Amplify risk-taking
            base_params['leverage_multiplier'] = 1.5
            base_params['aggressive_rebalancing'] = True
            
        elif scenario == 'low_sharpe':
            # Test with sub-optimal timing
            base_params['signal_delay'] = 2  # 2-day delay
            base_params['transaction_costs'] = 0.005  # Higher costs
            
        elif scenario == 'high_correlation':
            # Test during correlation breakdown
            base_params['correlation_override'] = True
            base_params['diversification_disabled'] = True
            
        return base_params
    
    def _generate_stress_risk_parameters(self, scenario: str) -> Dict[str, Any]:
        """Generate risk parameters for stress scenarios"""
        base_risk = self._generate_default_risk_parameters()
        
        if scenario == 'high_risk':
            base_risk['max_position_size'] *= 2.0
            base_risk['stop_loss_threshold'] *= 2.0
            
        elif scenario == 'low_sharpe':
            base_risk['transaction_costs'] = 0.01
            base_risk['slippage'] = 0.005
            
        return base_risk
    
    def _select_high_risk_instruments(self, instruments: List[InstrumentScore], n: int) -> List[InstrumentScore]:
        """Select high-risk instruments for stress testing"""
        return sorted(instruments, key=lambda x: x.volatility, reverse=True)[:n]
    
    def _select_low_sharpe_instruments(self, instruments: List[InstrumentScore], n: int) -> List[InstrumentScore]:
        """Select low Sharpe ratio instruments"""
        return sorted(instruments, key=lambda x: x.sharpe_ratio)[:n]
    
    def _select_high_correlation_instruments(self, instruments: List[InstrumentScore], n: int) -> List[InstrumentScore]:
        """Select potentially high correlation instruments"""
        # Simple heuristic: select instruments with similar correlation to market
        median_corr = np.median([inst.correlation_to_market for inst in instruments])
        return sorted(
            instruments,
            key=lambda x: abs(x.correlation_to_market - median_corr)
        )[:n]
    
    def _select_bottom_performers(self, instruments: List[InstrumentScore], n: int) -> List[InstrumentScore]:
        """Select bottom performing instruments"""
        return sorted(instruments, key=lambda x: x.composite_score)[:n]
    
    def _describe_stress_scenario(self, scenario: str) -> str:
        """Describe what each stress scenario tests"""
        descriptions = {
            'high_risk': 'Tests strategy performance with high-volatility instruments and increased leverage',
            'low_sharpe': 'Tests strategy with poor risk-adjusted returns and higher transaction costs',
            'high_correlation': 'Tests strategy when diversification benefits break down',
            'bottom_performers': 'Tests strategy with historically poor-performing instruments'
        }
        return descriptions.get(scenario, 'Generic stress test scenario')
    
    def _optimize_mean_variance(self, instruments: List[InstrumentScore]) -> Dict[str, float]:
        """Optimize portfolio using mean-variance optimization"""
        n = len(instruments)
        
        # Extract expected returns and construct covariance matrix
        returns = np.array([inst.expected_return for inst in instruments])
        
        # Simple covariance matrix estimation
        volatilities = np.array([inst.volatility for inst in instruments])
        correlations = np.array([inst.correlation_to_market for inst in instruments])
        
        # Construct covariance matrix (simplified)
        cov_matrix = np.outer(volatilities, volatilities) * np.mean(correlations)
        np.fill_diagonal(cov_matrix, volatilities ** 2)
        
        # Optimization constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
        ]
        
        bounds = [(0, self.max_position_size) for _ in range(n)]  # Position size limits
        
        # Initial guess (equal weights)
        x0 = np.array([1/n] * n)
        
        # Objective function (minimize negative Sharpe ratio)
        def objective(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            return -sharpe  # Minimize negative Sharpe
        
        try:
            result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
            
            if result.success:
                optimal_weights = result.x
                return {inst.symbol: weight for inst, weight in zip(instruments, optimal_weights)}
            else:
                logger.warning("Mean-variance optimization failed, using equal weights")
                return self._equal_weights(instruments)
                
        except Exception as e:
            logger.warning(f"Mean-variance optimization error: {e}")
            return self._equal_weights(instruments)
    
    def _optimize_risk_parity(self, instruments: List[InstrumentScore]) -> Dict[str, float]:
        """Optimize portfolio using risk parity"""
        # Simplified risk parity: inverse volatility weighting
        volatilities = np.array([inst.volatility for inst in instruments])
        inv_vol_weights = 1 / volatilities
        normalized_weights = inv_vol_weights / np.sum(inv_vol_weights)
        
        return {inst.symbol: weight for inst, weight in zip(instruments, normalized_weights)}
    
    def _optimize_max_sharpe(self, instruments: List[InstrumentScore]) -> Dict[str, float]:
        """Optimize for maximum Sharpe ratio"""
        # Weight by Sharpe ratio
        sharpe_ratios = np.array([max(0, inst.sharpe_ratio) for inst in instruments])
        
        if np.sum(sharpe_ratios) > 0:
            weights = sharpe_ratios / np.sum(sharpe_ratios)
        else:
            weights = np.array([1/len(instruments)] * len(instruments))
        
        return {inst.symbol: weight for inst, weight in zip(instruments, weights)}
    
    def _equal_weights(self, instruments: List[InstrumentScore]) -> Dict[str, float]:
        """Generate equal weights"""
        weight = 1.0 / len(instruments)
        return {inst.symbol: weight for inst in instruments}
    
    def _estimate_config_performance(self, instruments: List[InstrumentScore]) -> Dict[str, float]:
        """Estimate expected performance of configuration"""
        return {
            'expected_return': np.mean([inst.expected_return for inst in instruments]),
            'expected_sharpe': np.mean([inst.sharpe_ratio for inst in instruments]),
            'expected_max_drawdown': max([inst.max_drawdown for inst in instruments]),
            'expected_win_rate': np.mean([inst.win_rate for inst in instruments]),
            'portfolio_volatility': np.sqrt(np.mean([inst.volatility**2 for inst in instruments]))
        }
    
    def _classify_instrument_sector(self, symbol: str) -> str:
        """Simple sector classification based on symbol"""
        # This is a simplified classification
        # In production, would use proper sector data
        
        if symbol.startswith(('AAPL', 'MSFT', 'GOOGL', 'AMZN')):
            return 'technology'
        elif symbol.startswith(('JPM', 'BAC', 'WFC', 'C')):
            return 'financial'
        elif symbol.startswith(('XOM', 'CVX', 'COP')):
            return 'energy'
        elif symbol.startswith(('JNJ', 'PFE', 'UNH')):
            return 'healthcare'
        else:
            return 'other'
    
    def _validate_backtest_suite(self, suite: BacktestSuite) -> None:
        """Validate the generated backtest suite"""
        total_configs = suite.total_configs
        
        if total_configs == 0:
            raise ValueError("No backtest configurations generated")
        
        # Check for duplicate config IDs
        all_config_ids = []
        for config_list in [suite.optimized_configs, suite.baseline_configs, suite.stress_configs]:
            all_config_ids.extend([config.config_id for config in config_list])
        
        if len(all_config_ids) != len(set(all_config_ids)):
            logger.warning("Duplicate configuration IDs detected")
        
        # Validate individual configurations
        invalid_configs = 0
        for config_list in [suite.optimized_configs, suite.baseline_configs, suite.stress_configs]:
            for config in config_list:
                try:
                    # Basic validation
                    if len(config.instruments) < self.min_instruments_per_config:
                        invalid_configs += 1
                        logger.warning(f"Config {config.config_id} has too few instruments")
                    
                    if not config.strategy or not config.regime_context:
                        invalid_configs += 1
                        logger.warning(f"Config {config.config_id} missing strategy or regime")
                        
                except Exception as e:
                    invalid_configs += 1
                    logger.warning(f"Config validation error: {e}")
        
        if invalid_configs > 0:
            logger.warning(f"{invalid_configs} invalid configurations detected out of {total_configs}")
        
        logger.info(f"Backtest suite validation complete: {total_configs} configurations")
    
    def _initialize_strategy_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default strategy parameters"""
        return {
            'mean_reversion': {
                'default': {
                    'lookback_period': 20,
                    'entry_threshold': 2.0,  # Standard deviations
                    'exit_threshold': 0.5,
                    'rebalance_frequency': 'daily',
                    'position_sizing': 'equal_weight'
                }
            },
            'momentum': {
                'default': {
                    'momentum_window': 20,
                    'signal_window': 5,
                    'trend_threshold': 0.05,
                    'rebalance_frequency': 'weekly',
                    'position_sizing': 'volatility_weighted'
                }
            },
            'pairs_trading': {
                'default': {
                    'cointegration_window': 252,
                    'entry_zscore': 2.0,
                    'exit_zscore': 0.5,
                    'hedge_ratio_lookback': 60,
                    'rebalance_frequency': 'daily'
                }
            }
        }