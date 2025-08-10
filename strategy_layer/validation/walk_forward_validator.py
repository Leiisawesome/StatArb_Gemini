"""
Walk-Forward Validator

Walk-forward analysis implementation for strategy validation.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .strategy_validator import (
    StrategyValidator,
    ValidationConfig,
    ValidationResult,
    Trade,
    PortfolioState
)
from .backtesting_validator import BacktestingValidator
from strategy_layer.base import StrategyError, StrategyDefinition


@dataclass
class WalkForwardWindow:
    """Walk-forward analysis window"""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    window_id: int


@dataclass
class WalkForwardResult:
    """Result of walk-forward analysis"""
    # Window information
    window_id: int
    train_period: Tuple[datetime, datetime]
    test_period: Tuple[datetime, datetime]
    
    # Training results
    train_result: ValidationResult
    
    # Testing results
    test_result: ValidationResult
    
    # Model performance
    model_performance: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'window_id': self.window_id,
            'train_period': [self.train_period[0].isoformat(), self.train_period[1].isoformat()],
            'test_period': [self.test_period[0].isoformat(), self.test_period[1].isoformat()],
            'train_result': self.train_result.to_dict(),
            'test_result': self.test_result.to_dict(),
            'model_performance': self.model_performance
        }


class WalkForwardValidator(StrategyValidator):
    """Walk-forward validator for strategy validation"""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.windows: List[WalkForwardWindow] = []
        self.results: List[WalkForwardResult] = []
    
    def validate_strategy(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """Validate a trading strategy using walk-forward analysis"""
        try:
            self.logger.info(f"Starting walk-forward validation for strategy: {strategy.config.strategy_id}")
            
            # Generate walk-forward windows
            self._generate_windows()
            
            # Run walk-forward analysis
            self._run_walk_forward_analysis(strategy, market_data)
            
            # Calculate aggregate results
            result = self._calculate_aggregate_result(strategy)
            
            self.logger.info(f"Walk-forward analysis completed. Windows: {len(self.windows)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in walk-forward validation: {e}")
            raise StrategyError(f"Walk-forward validation failed: {e}")
    
    def _generate_windows(self):
        """Generate walk-forward windows"""
        self.windows = []
        
        total_duration = self.config.end_date - self.config.start_date
        window_duration = total_duration / self.config.walk_forward_windows
        
        for i in range(self.config.walk_forward_windows):
            # Calculate window boundaries
            window_start = self.config.start_date + i * window_duration
            window_end = window_start + window_duration
            
            # Split into train/test periods
            train_duration = window_duration * (1 - self.config.validation_split)
            train_start = window_start
            train_end = train_start + train_duration
            test_start = train_end
            test_end = window_end
            
            # Create window
            window = WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=i + 1
            )
            
            self.windows.append(window)
    
    def _run_walk_forward_analysis(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]):
        """Run walk-forward analysis"""
        self.results = []
        
        for window in self.windows:
            try:
                self.logger.info(f"Processing window {window.window_id}")
                
                # Create training data
                train_data = self._filter_market_data(market_data, window.train_start, window.train_end)
                
                # Create testing data
                test_data = self._filter_market_data(market_data, window.test_start, window.test_end)
                
                if train_data and test_data:
                    # Train strategy (if applicable)
                    trained_strategy = self._train_strategy(strategy, train_data)
                    
                    # Validate on training data
                    train_config = ValidationConfig(
                        start_date=window.train_start,
                        end_date=window.train_end,
                        symbols=self.config.symbols,
                        initial_capital=self.config.initial_capital,
                        commission_rate=self.config.commission_rate,
                        slippage_rate=self.config.slippage_rate,
                        max_position_size=self.config.max_position_size,
                        max_drawdown=self.config.max_drawdown,
                        stop_loss=self.config.stop_loss,
                        take_profit=self.config.take_profit,
                        benchmark_symbol=self.config.benchmark_symbol,
                        risk_free_rate=self.config.risk_free_rate
                    )
                    
                    train_validator = BacktestingValidator(train_config)
                    train_result = train_validator.validate_strategy(trained_strategy, train_data)
                    
                    # Validate on testing data
                    test_config = ValidationConfig(
                        start_date=window.test_start,
                        end_date=window.test_end,
                        symbols=self.config.symbols,
                        initial_capital=self.config.initial_capital,
                        commission_rate=self.config.commission_rate,
                        slippage_rate=self.config.slippage_rate,
                        max_position_size=self.config.max_position_size,
                        max_drawdown=self.config.max_drawdown,
                        stop_loss=self.config.stop_loss,
                        take_profit=self.config.take_profit,
                        benchmark_symbol=self.config.benchmark_symbol,
                        risk_free_rate=self.config.risk_free_rate
                    )
                    
                    test_validator = BacktestingValidator(test_config)
                    test_result = test_validator.validate_strategy(trained_strategy, test_data)
                    
                    # Calculate model performance
                    model_performance = self._calculate_model_performance(train_result, test_result)
                    
                    # Create walk-forward result
                    wf_result = WalkForwardResult(
                        window_id=window.window_id,
                        train_period=(window.train_start, window.train_end),
                        test_period=(window.test_start, window.test_end),
                        train_result=train_result,
                        test_result=test_result,
                        model_performance=model_performance
                    )
                    
                    self.results.append(wf_result)
                    
            except Exception as e:
                self.logger.warning(f"Error processing window {window.window_id}: {e}")
                continue
    
    def _filter_market_data(self, market_data: Dict[str, pd.DataFrame], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Filter market data to specific date range"""
        filtered_data = {}
        
        for symbol, data in market_data.items():
            if not data.empty:
                mask = (data.index >= start_date) & (data.index <= end_date)
                filtered = data[mask]
                if not filtered.empty:
                    filtered_data[symbol] = filtered
        
        return filtered_data
    
    def _train_strategy(self, strategy: StrategyDefinition, train_data: Dict[str, pd.DataFrame]) -> StrategyDefinition:
        """Train the strategy (placeholder for future implementation)"""
        # For now, return the original strategy
        # In the future, this could implement parameter optimization or model training
        return strategy
    
    def _calculate_model_performance(self, train_result: ValidationResult, test_result: ValidationResult) -> Dict[str, float]:
        """Calculate model performance metrics"""
        # Calculate performance degradation
        train_sharpe = train_result.sharpe_ratio
        test_sharpe = test_result.sharpe_ratio
        
        train_return = train_result.annualized_return
        test_return = test_result.annualized_return
        
        train_drawdown = train_result.max_drawdown
        test_drawdown = test_result.max_drawdown
        
        # Calculate degradation ratios
        sharpe_degradation = (train_sharpe - test_sharpe) / abs(train_sharpe) if train_sharpe != 0 else 0.0
        return_degradation = (train_return - test_return) / abs(train_return) if train_return != 0 else 0.0
        drawdown_degradation = (test_drawdown - train_drawdown) / abs(train_drawdown) if train_drawdown != 0 else 0.0
        
        # Calculate consistency metrics
        consistency_score = 1.0 - abs(sharpe_degradation) - abs(return_degradation) - abs(drawdown_degradation)
        consistency_score = max(0.0, min(1.0, consistency_score))
        
        return {
            'sharpe_degradation': sharpe_degradation,
            'return_degradation': return_degradation,
            'drawdown_degradation': drawdown_degradation,
            'consistency_score': consistency_score,
            'train_test_correlation': self._calculate_correlation(train_result, test_result)
        }
    
    def _calculate_correlation(self, train_result: ValidationResult, test_result: ValidationResult) -> float:
        """Calculate correlation between train and test results"""
        # Extract key metrics for correlation
        train_metrics = [
            train_result.sharpe_ratio,
            train_result.annualized_return,
            train_result.max_drawdown,
            train_result.win_rate,
            train_result.profit_factor
        ]
        
        test_metrics = [
            test_result.sharpe_ratio,
            test_result.annualized_return,
            test_result.max_drawdown,
            test_result.win_rate,
            test_result.profit_factor
        ]
        
        # Calculate correlation
        correlation = np.corrcoef(train_metrics, test_metrics)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _calculate_aggregate_result(self, strategy: StrategyDefinition) -> ValidationResult:
        """Calculate aggregate results from all windows"""
        if not self.results:
            raise StrategyError("No walk-forward results available")
        
        # Aggregate test results
        test_returns = []
        test_sharpes = []
        test_drawdowns = []
        test_trades = []
        test_win_rates = []
        
        for result in self.results:
            test_returns.append(result.test_result.annualized_return)
            test_sharpes.append(result.test_result.sharpe_ratio)
            test_drawdowns.append(result.test_result.max_drawdown)
            test_trades.append(result.test_result.total_trades)
            test_win_rates.append(result.test_result.win_rate)
        
        # Calculate aggregate metrics
        avg_return = np.mean(test_returns)
        avg_sharpe = np.mean(test_sharpes)
        avg_drawdown = np.mean(test_drawdowns)
        avg_trades = np.mean(test_trades)
        avg_win_rate = np.mean(test_win_rates)
        
        # Calculate consistency metrics
        return_std = np.std(test_returns)
        sharpe_std = np.std(test_sharpes)
        consistency_score = 1.0 - (return_std + sharpe_std) / 2.0
        
        # Create aggregate validation result
        result = ValidationResult(
            strategy_id=strategy.config.strategy_id,
            strategy_name=f"{strategy.config.name} (Walk-Forward)",
            validation_period=(self.config.start_date, self.config.end_date),
            total_return=avg_return,
            annualized_return=avg_return,
            sharpe_ratio=avg_sharpe,
            sortino_ratio=avg_sharpe,  # Simplified
            max_drawdown=avg_drawdown,
            calmar_ratio=avg_return / avg_drawdown if avg_drawdown > 0 else 0.0,
            volatility=return_std,
            var_95=0.0,  # Placeholder
            cvar_95=0.0,  # Placeholder
            beta=0.0,  # Placeholder
            alpha=0.0,  # Placeholder
            total_trades=int(avg_trades),
            winning_trades=int(avg_trades * avg_win_rate),
            losing_trades=int(avg_trades * (1 - avg_win_rate)),
            win_rate=avg_win_rate,
            avg_win=0.0,  # Placeholder
            avg_loss=0.0,  # Placeholder
            profit_factor=0.0,  # Placeholder
            final_value=self.config.initial_capital * (1 + avg_return),
            peak_value=self.config.initial_capital * (1 + avg_return),
            final_positions={},
            config=self.config
        )
        
        return result
    
    def get_walk_forward_summary(self) -> Dict[str, Any]:
        """Get summary of walk-forward analysis"""
        if not self.results:
            return {}
        
        # Calculate aggregate statistics
        train_sharpes = [r.train_result.sharpe_ratio for r in self.results]
        test_sharpes = [r.test_result.sharpe_ratio for r in self.results]
        train_returns = [r.train_result.annualized_return for r in self.results]
        test_returns = [r.test_result.annualized_return for r in self.results]
        
        # Calculate degradation statistics
        sharpe_degradations = [r.model_performance['sharpe_degradation'] for r in self.results]
        return_degradations = [r.model_performance['return_degradation'] for r in self.results]
        consistency_scores = [r.model_performance['consistency_score'] for r in self.results]
        
        return {
            'total_windows': len(self.results),
            'avg_train_sharpe': np.mean(train_sharpes),
            'avg_test_sharpe': np.mean(test_sharpes),
            'avg_train_return': np.mean(train_returns),
            'avg_test_return': np.mean(test_returns),
            'avg_sharpe_degradation': np.mean(sharpe_degradations),
            'avg_return_degradation': np.mean(return_degradations),
            'avg_consistency_score': np.mean(consistency_scores),
            'std_train_sharpe': np.std(train_sharpes),
            'std_test_sharpe': np.std(test_sharpes),
            'std_train_return': np.std(train_returns),
            'std_test_return': np.std(test_returns)
        }
    
    def get_window_results(self) -> List[Dict[str, Any]]:
        """Get results for each window"""
        return [result.to_dict() for result in self.results]
    
    def get_performance_degradation_analysis(self) -> Dict[str, Any]:
        """Analyze performance degradation across windows"""
        if not self.results:
            return {}
        
        degradations = []
        for result in self.results:
            degradation = {
                'window_id': result.window_id,
                'sharpe_degradation': result.model_performance['sharpe_degradation'],
                'return_degradation': result.model_performance['return_degradation'],
                'consistency_score': result.model_performance['consistency_score'],
                'train_sharpe': result.train_result.sharpe_ratio,
                'test_sharpe': result.test_result.sharpe_ratio,
                'train_return': result.train_result.annualized_return,
                'test_return': result.test_result.annualized_return
            }
            degradations.append(degradation)
        
        # Calculate trends
        window_ids = [d['window_id'] for d in degradations]
        sharpe_degradations = [d['sharpe_degradation'] for d in degradations]
        return_degradations = [d['return_degradation'] for d in degradations]
        
        # Calculate trend (positive = increasing degradation)
        if len(window_ids) > 1:
            sharpe_trend = np.polyfit(window_ids, sharpe_degradations, 1)[0]
            return_trend = np.polyfit(window_ids, return_degradations, 1)[0]
        else:
            sharpe_trend = 0.0
            return_trend = 0.0
        
        return {
            'degradations': degradations,
            'sharpe_degradation_trend': sharpe_trend,
            'return_degradation_trend': return_trend,
            'avg_degradation': np.mean(sharpe_degradations + return_degradations),
            'degradation_stability': 1.0 - np.std(sharpe_degradations + return_degradations)
        }
