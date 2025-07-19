"""
Institutional Performance Analytics System
Professional-grade backtesting and performance measurement
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from scipy import stats
import warnings
from dataclasses import dataclass

logger = logging.getLogger('mvs.performance_analyzer')

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    recovery_factor: float
    var_95: float
    cvar_95: float
    
    # Risk-adjusted metrics
    information_ratio: float
    treynor_ratio: float
    jensen_alpha: float
    
    # Trading metrics
    total_trades: int
    avg_trade_return: float
    avg_winner: float
    avg_loser: float
    longest_winning_streak: int
    longest_losing_streak: int
    
    # Benchmark comparison
    tracking_error: float
    beta: float
    correlation_with_benchmark: float
    
    # Additional institutional metrics
    upside_capture: float
    downside_capture: float
    pain_index: float
    sterling_ratio: float

class PerformanceAnalyzer:
    """
    Institutional-grade performance analytics system
    
    Features:
    - Comprehensive risk-adjusted returns analysis
    - Benchmark-relative performance metrics
    - Drawdown and recovery analysis
    - Risk decomposition and attribution
    - Monte Carlo simulation capabilities
    - Professional reporting standards
    """
    
    def __init__(self, benchmark_symbol: str = 'SPY'):
        self.benchmark_symbol = benchmark_symbol
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
        # Performance calculation parameters
        self.trading_days_per_year = 252
        self.months_per_year = 12
        
        # Institutional reporting standards
        self.reporting_metrics = [
            'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
            'max_drawdown', 'calmar_ratio', 'win_rate', 'profit_factor',
            'var_95', 'information_ratio', 'beta', 'tracking_error'
        ]
        
        # Analysis history
        self.performance_history = []
        
        logger.info("Performance Analyzer initialized")
        logger.info(f"Benchmark: {benchmark_symbol}")
        logger.info(f"Risk-free rate: {self.risk_free_rate:.1%}")
    
    def analyze_portfolio_performance(self, portfolio_returns: pd.Series, 
                                    benchmark_returns: pd.Series = None,
                                    positions: pd.DataFrame = None,
                                    transaction_costs: pd.Series = None) -> PerformanceMetrics:
        """
        Comprehensive portfolio performance analysis
        
        Args:
            portfolio_returns: Time series of portfolio returns
            benchmark_returns: Time series of benchmark returns
            positions: DataFrame with position data
            transaction_costs: Series of transaction costs
            
        Returns:
            PerformanceMetrics object with comprehensive analysis
        """
        try:
            logger.info(f"Analyzing portfolio performance ({len(portfolio_returns)} periods)")
            
            # Ensure data is properly formatted
            portfolio_returns = self._prepare_returns_data(portfolio_returns)
            
            if benchmark_returns is not None:
                benchmark_returns = self._prepare_returns_data(benchmark_returns)
                # Align dates
                common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
                portfolio_returns = portfolio_returns.loc[common_dates]
                benchmark_returns = benchmark_returns.loc[common_dates]
            
            # Calculate core performance metrics
            basic_metrics = self._calculate_basic_metrics(portfolio_returns)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(portfolio_returns)
            
            # Calculate trading metrics
            trading_metrics = self._calculate_trading_metrics(portfolio_returns, positions)
            
            # Calculate benchmark-relative metrics
            benchmark_metrics = self._calculate_benchmark_metrics(portfolio_returns, benchmark_returns)
            
            # Calculate advanced institutional metrics
            advanced_metrics = self._calculate_advanced_metrics(portfolio_returns, benchmark_returns)
            
            # Combine all metrics
            all_metrics = {**basic_metrics, **risk_metrics, **trading_metrics, 
                          **benchmark_metrics, **advanced_metrics}
            
            # Create performance metrics object
            performance_metrics = PerformanceMetrics(**all_metrics)
            
            # Store in history
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': performance_metrics,
                'data_points': len(portfolio_returns)
            })
            
            logger.info(f"Performance analysis completed - Sharpe: {performance_metrics.sharpe_ratio:.2f}")
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return self._create_default_metrics()
    
    def _prepare_returns_data(self, returns: pd.Series) -> pd.Series:
        """Prepare and validate returns data"""
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
        
        # Remove any infinite or NaN values
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        
        # Ensure datetime index
        if not isinstance(returns.index, pd.DatetimeIndex):
            try:
                returns.index = pd.to_datetime(returns.index)
            except:
                logger.warning("Could not convert index to datetime")
        
        return returns
    
    def _calculate_basic_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate basic return and volatility metrics"""
        try:
            if len(returns) == 0:
                return self._get_zero_metrics(['total_return', 'annualized_return', 'volatility'])
            
            # Total return
            total_return = (1 + returns).prod() - 1
            
            # Annualized return
            periods_per_year = self._get_periods_per_year(returns)
            annualized_return = (1 + total_return) ** (periods_per_year / len(returns)) - 1
            
            # Volatility (annualized)
            volatility = returns.std() * np.sqrt(periods_per_year)
            
            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility
            }
            
        except Exception as e:
            logger.debug(f"Basic metrics calculation error: {e}")
            return self._get_zero_metrics(['total_return', 'annualized_return', 'volatility'])
    
    def _calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        try:
            if len(returns) < 2:
                return self._get_zero_metrics(['sharpe_ratio', 'sortino_ratio', 'max_drawdown', 
                                             'calmar_ratio', 'var_95', 'cvar_95'])
            
            periods_per_year = self._get_periods_per_year(returns)
            annualized_return = (1 + returns.mean()) ** periods_per_year - 1
            volatility = returns.std() * np.sqrt(periods_per_year)
            
            # Sharpe ratio
            excess_return = annualized_return - self.risk_free_rate
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0
            sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdowns.min()
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)
            
            # Conditional Value at Risk (Expected Shortfall)
            cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar_ratio,
                'var_95': var_95,
                'cvar_95': cvar_95
            }
            
        except Exception as e:
            logger.debug(f"Risk metrics calculation error: {e}")
            return self._get_zero_metrics(['sharpe_ratio', 'sortino_ratio', 'max_drawdown', 
                                         'calmar_ratio', 'var_95', 'cvar_95'])
    
    def _calculate_trading_metrics(self, returns: pd.Series, positions: pd.DataFrame = None) -> Dict[str, float]:
        """Calculate trading-specific performance metrics"""
        try:
            if len(returns) == 0:
                return self._get_zero_metrics(['win_rate', 'profit_factor', 'recovery_factor',
                                             'total_trades', 'avg_trade_return', 'avg_winner', 
                                             'avg_loser', 'longest_winning_streak', 'longest_losing_streak'])
            
            # Basic trading metrics from returns
            winning_periods = returns[returns > 0]
            losing_periods = returns[returns < 0]
            
            win_rate = len(winning_periods) / len(returns) if len(returns) > 0 else 0
            
            total_gains = winning_periods.sum() if len(winning_periods) > 0 else 0
            total_losses = abs(losing_periods.sum()) if len(losing_periods) > 0 else 0
            profit_factor = total_gains / total_losses if total_losses > 0 else float('inf') if total_gains > 0 else 0
            
            # Recovery factor
            total_return = (1 + returns).prod() - 1
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdowns.min())
            recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0
            
            # Trading streaks
            winning_streak, losing_streak = self._calculate_streaks(returns)
            
            return {
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'recovery_factor': recovery_factor,
                'total_trades': len(returns),  # Approximate
                'avg_trade_return': returns.mean(),
                'avg_winner': winning_periods.mean() if len(winning_periods) > 0 else 0,
                'avg_loser': losing_periods.mean() if len(losing_periods) > 0 else 0,
                'longest_winning_streak': winning_streak,
                'longest_losing_streak': losing_streak
            }
            
        except Exception as e:
            logger.debug(f"Trading metrics calculation error: {e}")
            return self._get_zero_metrics(['win_rate', 'profit_factor', 'recovery_factor',
                                         'total_trades', 'avg_trade_return', 'avg_winner', 
                                         'avg_loser', 'longest_winning_streak', 'longest_losing_streak'])
    
    def _calculate_benchmark_metrics(self, portfolio_returns: pd.Series, 
                                   benchmark_returns: pd.Series = None) -> Dict[str, float]:
        """Calculate benchmark-relative performance metrics"""
        try:
            if benchmark_returns is None or len(benchmark_returns) == 0:
                return self._get_zero_metrics(['information_ratio', 'treynor_ratio', 'jensen_alpha',
                                             'tracking_error', 'beta', 'correlation_with_benchmark'])
            
            if len(portfolio_returns) != len(benchmark_returns):
                logger.warning("Portfolio and benchmark return lengths don't match")
                return self._get_zero_metrics(['information_ratio', 'treynor_ratio', 'jensen_alpha',
                                             'tracking_error', 'beta', 'correlation_with_benchmark'])
            
            # Excess returns
            excess_returns = portfolio_returns - benchmark_returns
            
            # Tracking error (volatility of excess returns)
            periods_per_year = self._get_periods_per_year(portfolio_returns)
            tracking_error = excess_returns.std() * np.sqrt(periods_per_year)
            
            # Information ratio
            information_ratio = (excess_returns.mean() * periods_per_year) / tracking_error if tracking_error > 0 else 0
            
            # Beta (portfolio sensitivity to benchmark)
            if benchmark_returns.var() > 0:
                beta = portfolio_returns.cov(benchmark_returns) / benchmark_returns.var()
            else:
                beta = 0
            
            # Jensen's Alpha
            portfolio_annual_return = (1 + portfolio_returns.mean()) ** periods_per_year - 1
            benchmark_annual_return = (1 + benchmark_returns.mean()) ** periods_per_year - 1
            jensen_alpha = portfolio_annual_return - (self.risk_free_rate + beta * (benchmark_annual_return - self.risk_free_rate))
            
            # Treynor ratio
            portfolio_excess_return = portfolio_annual_return - self.risk_free_rate
            treynor_ratio = portfolio_excess_return / beta if beta != 0 else 0
            
            # Correlation with benchmark
            correlation_with_benchmark = portfolio_returns.corr(benchmark_returns)
            
            return {
                'information_ratio': information_ratio,
                'treynor_ratio': treynor_ratio,
                'jensen_alpha': jensen_alpha,
                'tracking_error': tracking_error,
                'beta': beta,
                'correlation_with_benchmark': correlation_with_benchmark
            }
            
        except Exception as e:
            logger.debug(f"Benchmark metrics calculation error: {e}")
            return self._get_zero_metrics(['information_ratio', 'treynor_ratio', 'jensen_alpha',
                                         'tracking_error', 'beta', 'correlation_with_benchmark'])
    
    def _calculate_advanced_metrics(self, portfolio_returns: pd.Series,
                                  benchmark_returns: pd.Series = None) -> Dict[str, float]:
        """Calculate advanced institutional performance metrics"""
        try:
            # Initialize with defaults
            metrics = {
                'upside_capture': 0.0,
                'downside_capture': 0.0,
                'pain_index': 0.0,
                'sterling_ratio': 0.0
            }
            
            if len(portfolio_returns) < 10:
                return metrics
            
            # Pain index (average drawdown)
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            pain_index = abs(drawdowns.mean())
            metrics['pain_index'] = pain_index
            
            # Sterling ratio
            total_return = (1 + portfolio_returns).prod() - 1
            avg_drawdown = abs(drawdowns.mean())
            sterling_ratio = total_return / avg_drawdown if avg_drawdown > 0 else 0
            metrics['sterling_ratio'] = sterling_ratio
            
            # Upside/Downside capture (if benchmark available)
            if benchmark_returns is not None and len(benchmark_returns) == len(portfolio_returns):
                # Upside capture
                up_periods = benchmark_returns > 0
                if up_periods.sum() > 0:
                    upside_portfolio = portfolio_returns[up_periods].mean()
                    upside_benchmark = benchmark_returns[up_periods].mean()
                    upside_capture = upside_portfolio / upside_benchmark if upside_benchmark != 0 else 0
                    metrics['upside_capture'] = upside_capture
                
                # Downside capture
                down_periods = benchmark_returns < 0
                if down_periods.sum() > 0:
                    downside_portfolio = portfolio_returns[down_periods].mean()
                    downside_benchmark = benchmark_returns[down_periods].mean()
                    downside_capture = downside_portfolio / downside_benchmark if downside_benchmark != 0 else 0
                    metrics['downside_capture'] = downside_capture
            
            return metrics
            
        except Exception as e:
            logger.debug(f"Advanced metrics calculation error: {e}")
            return {'upside_capture': 0.0, 'downside_capture': 0.0, 'pain_index': 0.0, 'sterling_ratio': 0.0}
    
    def _calculate_streaks(self, returns: pd.Series) -> Tuple[int, int]:
        """Calculate longest winning and losing streaks"""
        try:
            if len(returns) == 0:
                return 0, 0
            
            # Convert to win/loss sequence
            win_loss = (returns > 0).astype(int)
            
            # Calculate streaks
            streaks = []
            current_streak = 1
            current_type = win_loss.iloc[0]
            
            for i in range(1, len(win_loss)):
                if win_loss.iloc[i] == current_type:
                    current_streak += 1
                else:
                    streaks.append((current_type, current_streak))
                    current_streak = 1
                    current_type = win_loss.iloc[i]
            streaks.append((current_type, current_streak))
            
            # Find longest winning and losing streaks
            winning_streaks = [length for type_, length in streaks if type_ == 1]
            losing_streaks = [length for type_, length in streaks if type_ == 0]
            
            longest_winning_streak = max(winning_streaks) if winning_streaks else 0
            longest_losing_streak = max(losing_streaks) if losing_streaks else 0
            
            return longest_winning_streak, longest_losing_streak
            
        except Exception as e:
            logger.debug(f"Streak calculation error: {e}")
            return 0, 0
    
    def _get_periods_per_year(self, returns: pd.Series) -> float:
        """Determine annualization factor based on data frequency"""
        if len(returns) < 2:
            return 252  # Default to daily
        
        # Calculate average time between observations
        time_diff = (returns.index[-1] - returns.index[0]) / (len(returns) - 1)
        
        if time_diff.days >= 28:  # Monthly or longer
            return 12
        elif time_diff.days >= 6:  # Weekly
            return 52
        else:  # Daily or intraday
            return 252
    
    def _get_zero_metrics(self, metric_names: List[str]) -> Dict[str, float]:
        """Return dictionary with zero values for specified metrics"""
        return {name: 0.0 for name in metric_names}
    
    def _create_default_metrics(self) -> PerformanceMetrics:
        """Create default PerformanceMetrics object for error cases"""
        return PerformanceMetrics(
            total_return=0.0, annualized_return=0.0, volatility=0.0, sharpe_ratio=0.0,
            sortino_ratio=0.0, max_drawdown=0.0, calmar_ratio=0.0, win_rate=0.0,
            profit_factor=0.0, recovery_factor=0.0, var_95=0.0, cvar_95=0.0,
            information_ratio=0.0, treynor_ratio=0.0, jensen_alpha=0.0,
            total_trades=0, avg_trade_return=0.0, avg_winner=0.0, avg_loser=0.0,
            longest_winning_streak=0, longest_losing_streak=0,
            tracking_error=0.0, beta=0.0, correlation_with_benchmark=0.0,
            upside_capture=0.0, downside_capture=0.0, pain_index=0.0, sterling_ratio=0.0
        )
    
    def generate_performance_report(self, portfolio_returns: pd.Series,
                                  benchmark_returns: pd.Series = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            # Calculate performance metrics
            metrics = self.analyze_portfolio_performance(portfolio_returns, benchmark_returns)
            
            # Generate summary statistics
            summary = {
                'analysis_period': {
                    'start_date': portfolio_returns.index.min().strftime('%Y-%m-%d'),
                    'end_date': portfolio_returns.index.max().strftime('%Y-%m-%d'),
                    'total_periods': len(portfolio_returns)
                },
                'performance_summary': {
                    'total_return': f"{metrics.total_return:.2%}",
                    'annualized_return': f"{metrics.annualized_return:.2%}",
                    'volatility': f"{metrics.volatility:.2%}",
                    'sharpe_ratio': f"{metrics.sharpe_ratio:.2f}",
                    'max_drawdown': f"{metrics.max_drawdown:.2%}",
                    'win_rate': f"{metrics.win_rate:.2%}"
                },
                'risk_analysis': {
                    'var_95': f"{metrics.var_95:.2%}",
                    'cvar_95': f"{metrics.cvar_95:.2%}",
                    'sortino_ratio': f"{metrics.sortino_ratio:.2f}",
                    'calmar_ratio': f"{metrics.calmar_ratio:.2f}"
                },
                'benchmark_comparison': {
                    'beta': f"{metrics.beta:.2f}",
                    'correlation': f"{metrics.correlation_with_benchmark:.2f}",
                    'tracking_error': f"{metrics.tracking_error:.2%}",
                    'information_ratio': f"{metrics.information_ratio:.2f}"
                }
            }
            
            return {
                'report_timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'summary': summary,
                'raw_data': {
                    'portfolio_returns': portfolio_returns.to_dict(),
                    'benchmark_returns': benchmark_returns.to_dict() if benchmark_returns is not None else None
                }
            }
            
        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            return {'error': f"Report generation failed: {e}"}
    
    def run_monte_carlo_simulation(self, portfolio_returns: pd.Series, 
                                 num_simulations: int = 1000,
                                 simulation_periods: int = 252) -> Dict[str, Any]:
        """Run Monte Carlo simulation for portfolio projections"""
        try:
            logger.info(f"Running Monte Carlo simulation ({num_simulations} simulations)")
            
            # Calculate historical statistics
            mean_return = portfolio_returns.mean()
            volatility = portfolio_returns.std()
            
            # Run simulations
            simulation_results = []
            
            for i in range(num_simulations):
                # Generate random returns based on historical statistics
                random_returns = np.random.normal(mean_return, volatility, simulation_periods)
                
                # Calculate cumulative performance
                cumulative_performance = (1 + pd.Series(random_returns)).cumprod().iloc[-1] - 1
                simulation_results.append(cumulative_performance)
            
            simulation_results = np.array(simulation_results)
            
            # Calculate simulation statistics
            simulation_stats = {
                'mean_return': simulation_results.mean(),
                'median_return': np.median(simulation_results),
                'std_deviation': simulation_results.std(),
                'percentile_5': np.percentile(simulation_results, 5),
                'percentile_25': np.percentile(simulation_results, 25),
                'percentile_75': np.percentile(simulation_results, 75),
                'percentile_95': np.percentile(simulation_results, 95),
                'probability_positive': (simulation_results > 0).mean(),
                'probability_loss_gt_10pct': (simulation_results < -0.1).mean(),
                'probability_gain_gt_20pct': (simulation_results > 0.2).mean()
            }
            
            return {
                'simulation_parameters': {
                    'num_simulations': num_simulations,
                    'simulation_periods': simulation_periods,
                    'historical_mean_return': mean_return,
                    'historical_volatility': volatility
                },
                'results': simulation_stats,
                'raw_simulations': simulation_results.tolist()
            }
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}")
            return {'error': f"Simulation failed: {e}"}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance analyses"""
        if not self.performance_history:
            return {'status': 'No performance history available'}
        
        latest = self.performance_history[-1]
        
        return {
            'latest_analysis': {
                'timestamp': latest['timestamp'].isoformat(),
                'sharpe_ratio': latest['metrics'].sharpe_ratio,
                'total_return': latest['metrics'].total_return,
                'max_drawdown': latest['metrics'].max_drawdown,
                'win_rate': latest['metrics'].win_rate,
                'data_points': latest['data_points']
            },
            'analysis_count': len(self.performance_history),
            'benchmark_symbol': self.benchmark_symbol,
            'risk_free_rate': self.risk_free_rate
        }
