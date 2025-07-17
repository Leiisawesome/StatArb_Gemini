"""
Performance analysis and reporting for momentum backtest
Comprehensive analytics with institutional-grade metrics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Comprehensive performance analysis for momentum trading strategy
    
    Features:
    - Risk-adjusted performance metrics
    - Drawdown analysis
    - Trade-level analytics
    - Benchmark comparisons
    - Factor attribution
    - Risk decomposition
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.performance_config = config.get('performance', {})
        self.risk_free_rate = self.performance_config.get('risk_free_rate', 0.02)
        self.benchmark_symbol = self.performance_config.get('benchmark_symbol', 'SPY')
        
        # Set plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def analyze_performance(self, backtest_results: Dict[str, Any], 
                          benchmark_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Perform comprehensive performance analysis
        
        Args:
            backtest_results: Results from backtest engine
            benchmark_data: Benchmark price data for comparison
            
        Returns:
            Dictionary with detailed performance metrics and analysis
        """
        logger.info("Starting comprehensive performance analysis...")
        
        # Extract data from backtest results
        portfolio_history = backtest_results['portfolio_history']
        trade_history = backtest_results['trade_history']
        daily_returns = backtest_results['daily_returns']
        
        # Calculate core performance metrics
        performance_metrics = self._calculate_performance_metrics(daily_returns, portfolio_history)
        
        # Risk analysis
        risk_metrics = self._calculate_risk_metrics(daily_returns, portfolio_history)
        
        # Trade analysis
        trade_metrics = self._analyze_trades(trade_history)
        
        # Benchmark comparison
        benchmark_analysis = {}
        if benchmark_data is not None:
            benchmark_analysis = self._analyze_vs_benchmark(portfolio_history, benchmark_data)
        
        # Drawdown analysis
        drawdown_analysis = self._analyze_drawdowns(portfolio_history)
        
        # Rolling performance analysis
        rolling_analysis = self._calculate_rolling_metrics(daily_returns)
        
        # Monthly/quarterly analysis
        period_analysis = self._analyze_periodic_performance(portfolio_history)
        
        # Factor exposure analysis
        factor_analysis = self._analyze_factor_exposure(portfolio_history, trade_history)
        
        # Compile comprehensive results
        analysis_results = {
            'performance_metrics': performance_metrics,
            'risk_metrics': risk_metrics,
            'trade_metrics': trade_metrics,
            'benchmark_analysis': benchmark_analysis,
            'drawdown_analysis': drawdown_analysis,
            'rolling_analysis': rolling_analysis,
            'period_analysis': period_analysis,
            'factor_analysis': factor_analysis,
            
            # Raw data for further analysis
            'portfolio_history': portfolio_history,
            'trade_history': trade_history,
            'daily_returns': daily_returns
        }
        
        logger.info("Performance analysis completed")
        return analysis_results
    
    def _calculate_performance_metrics(self, daily_returns: np.ndarray, 
                                     portfolio_history: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        
        if len(daily_returns) == 0:
            return {}
        
        # Basic return metrics
        total_return = portfolio_history['total_return'].iloc[-1]
        annualized_return = ((1 + total_return) ** (252 / len(daily_returns))) - 1
        
        # Volatility metrics
        daily_vol = np.std(daily_returns)
        annualized_vol = daily_vol * np.sqrt(252)
        
        # Risk-adjusted metrics
        excess_returns = daily_returns - (self.risk_free_rate / 252)
        sharpe_ratio = np.mean(excess_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        
        # Sortino ratio (downside risk)
        downside_returns = daily_returns[daily_returns < 0]
        downside_vol = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino_ratio = np.mean(excess_returns) / downside_vol * np.sqrt(252) if downside_vol > 0 else 0
        
        # Calmar ratio
        max_dd = abs(self._calculate_max_drawdown_from_returns(daily_returns))
        calmar_ratio = annualized_return / max_dd if max_dd > 0 else 0
        
        # Win rate
        winning_days = len(daily_returns[daily_returns > 0])
        win_rate = winning_days / len(daily_returns)
        
        # Average win/loss
        wins = daily_returns[daily_returns > 0]
        losses = daily_returns[daily_returns < 0]
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Skewness and kurtosis
        skewness = stats.skew(daily_returns)
        kurtosis = stats.kurtosis(daily_returns)
        
        # Value at Risk
        var_5pct = np.percentile(daily_returns, 5)
        var_1pct = np.percentile(daily_returns, 1)
        
        # Conditional Value at Risk (Expected Shortfall)
        cvar_5pct = np.mean(daily_returns[daily_returns <= var_5pct])
        cvar_1pct = np.mean(daily_returns[daily_returns <= var_1pct])
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_vol,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_daily_return': np.mean(daily_returns),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'var_5pct': var_5pct,
            'var_1pct': var_1pct,
            'cvar_5pct': cvar_5pct,
            'cvar_1pct': cvar_1pct,
            'best_day': np.max(daily_returns),
            'worst_day': np.min(daily_returns),
            'trading_days': len(daily_returns)
        }
        
        return metrics
    
    def _calculate_risk_metrics(self, daily_returns: np.ndarray, 
                               portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        
        # Leverage analysis
        avg_leverage = portfolio_history['leverage'].mean()
        max_leverage = portfolio_history['leverage'].max()
        leverage_volatility = portfolio_history['leverage'].std()
        
        # Exposure analysis
        avg_long_exposure = portfolio_history['long_exposure'].mean()
        avg_short_exposure = portfolio_history['short_exposure'].mean()
        avg_net_exposure = portfolio_history['net_exposure'].mean()
        avg_gross_exposure = portfolio_history['long_exposure'].mean() + portfolio_history['short_exposure'].mean()
        
        # Beta calculation (simplified - using returns correlation)
        portfolio_volatility = np.std(daily_returns) * np.sqrt(252)
        
        # Risk concentration (would need position-level data for full analysis)
        
        risk_metrics = {
            'leverage_metrics': {
                'average_leverage': avg_leverage,
                'maximum_leverage': max_leverage,
                'leverage_volatility': leverage_volatility
            },
            'exposure_metrics': {
                'average_long_exposure': avg_long_exposure,
                'average_short_exposure': avg_short_exposure,
                'average_net_exposure': avg_net_exposure,
                'average_gross_exposure': avg_gross_exposure
            },
            'volatility_metrics': {
                'daily_volatility': np.std(daily_returns),
                'annualized_volatility': portfolio_volatility,
                'volatility_of_volatility': self._calculate_vol_of_vol(daily_returns)
            }
        }
        
        return risk_metrics
    
    def _analyze_trades(self, trade_history: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trade-level performance"""
        
        if trade_history.empty:
            return {}
        
        # Trade summary
        total_trades = len(trade_history)
        buy_trades = len(trade_history[trade_history['side'] == 'BUY'])
        sell_trades = len(trade_history[trade_history['side'] == 'SELL'])
        
        # Trade costs
        total_commission = trade_history['commission'].sum()
        total_slippage = trade_history['slippage'].sum()
        total_market_impact = trade_history['market_impact'].sum()
        total_transaction_costs = trade_history['total_cost'].sum()
        
        # Average trade sizes
        avg_trade_value = (trade_history['quantity'] * trade_history['price']).mean()
        avg_commission = trade_history['commission'].mean()
        avg_slippage = trade_history['slippage'].mean()
        
        # Trade frequency analysis
        if 'date' in trade_history.columns:
            trade_dates = pd.to_datetime(trade_history['date'])
            trading_period = (trade_dates.max() - trade_dates.min()).days
            trades_per_day = total_trades / trading_period if trading_period > 0 else 0
            
            # Daily trade volume
            daily_trade_volume = trade_history.groupby(trade_dates.dt.date)['quantity'].sum()
            avg_daily_volume = daily_trade_volume.mean()
        else:
            trades_per_day = 0
            avg_daily_volume = 0
        
        # Symbol analysis
        symbol_trade_counts = trade_history['symbol'].value_counts()
        most_traded_symbols = symbol_trade_counts.head(10).to_dict()
        
        trade_metrics = {
            'trade_summary': {
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'trades_per_day': trades_per_day
            },
            'cost_analysis': {
                'total_commission': total_commission,
                'total_slippage': total_slippage,
                'total_market_impact': total_market_impact,
                'total_transaction_costs': total_transaction_costs,
                'avg_commission': avg_commission,
                'avg_slippage': avg_slippage,
                'commission_as_pct_of_volume': total_commission / (avg_trade_value * total_trades) if total_trades > 0 else 0
            },
            'trade_characteristics': {
                'avg_trade_value': avg_trade_value,
                'avg_daily_volume': avg_daily_volume,
                'most_traded_symbols': most_traded_symbols
            }
        }
        
        return trade_metrics
    
    def _analyze_vs_benchmark(self, portfolio_history: pd.DataFrame, 
                             benchmark_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance vs benchmark"""
        
        # Align dates
        common_dates = portfolio_history.index.intersection(benchmark_data.index)
        
        if len(common_dates) == 0:
            return {}
        
        portfolio_returns = portfolio_history.loc[common_dates, 'daily_return']
        benchmark_prices = benchmark_data.loc[common_dates].iloc[:, 0]  # First column
        benchmark_returns = benchmark_prices.pct_change().dropna()
        
        # Align returns
        aligned_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_returns = portfolio_returns.loc[aligned_dates]
        benchmark_returns = benchmark_returns.loc[aligned_dates]
        
        if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
            return {}
        
        # Calculate relative metrics
        excess_returns = portfolio_returns - benchmark_returns
        
        # Alpha and Beta
        beta, alpha = np.polyfit(benchmark_returns, portfolio_returns, 1)
        
        # Information ratio
        tracking_error = np.std(excess_returns) * np.sqrt(252)
        information_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
        
        # Correlation
        correlation = np.corrcoef(portfolio_returns, benchmark_returns)[0, 1]
        
        # Up/down capture ratios
        up_market_days = benchmark_returns > 0
        down_market_days = benchmark_returns < 0
        
        up_capture = np.mean(portfolio_returns[up_market_days]) / np.mean(benchmark_returns[up_market_days]) if np.sum(up_market_days) > 0 else 0
        down_capture = np.mean(portfolio_returns[down_market_days]) / np.mean(benchmark_returns[down_market_days]) if np.sum(down_market_days) > 0 else 0
        
        # Performance comparison
        portfolio_cumulative = (1 + portfolio_returns).cumprod().iloc[-1] - 1
        benchmark_cumulative = (1 + benchmark_returns).cumprod().iloc[-1] - 1
        
        benchmark_analysis = {
            'alpha_annualized': alpha * 252,
            'beta': beta,
            'information_ratio': information_ratio,
            'tracking_error': tracking_error,
            'correlation': correlation,
            'up_capture_ratio': up_capture,
            'down_capture_ratio': down_capture,
            'portfolio_total_return': portfolio_cumulative,
            'benchmark_total_return': benchmark_cumulative,
            'excess_return': portfolio_cumulative - benchmark_cumulative,
            'excess_return_annualized': (portfolio_cumulative - benchmark_cumulative) * (252 / len(portfolio_returns))
        }
        
        return benchmark_analysis
    
    def _analyze_drawdowns(self, portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive drawdown analysis"""
        
        portfolio_values = portfolio_history['portfolio_value']
        
        # Calculate drawdown series
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        
        # Find drawdown periods
        is_drawdown = drawdown < 0
        drawdown_periods = []
        
        start_date = None
        for date, in_dd in is_drawdown.items():
            if in_dd and start_date is None:
                start_date = date
            elif not in_dd and start_date is not None:
                # End of drawdown period
                period_data = drawdown[start_date:date]
                min_dd = period_data.min()
                duration = len(period_data)
                
                drawdown_periods.append({
                    'start_date': start_date,
                    'end_date': date,
                    'duration_days': duration,
                    'max_drawdown': min_dd,
                    'recovery_date': date
                })
                start_date = None
        
        # Sort by magnitude
        drawdown_periods.sort(key=lambda x: x['max_drawdown'])
        
        # Summary statistics
        max_drawdown = drawdown.min()
        avg_drawdown = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        
        # Underwater curve (time in drawdown)
        time_underwater = len(drawdown[drawdown < 0]) / len(drawdown)
        
        # Average recovery time
        if drawdown_periods:
            avg_recovery_time = np.mean([p['duration_days'] for p in drawdown_periods])
            max_recovery_time = max([p['duration_days'] for p in drawdown_periods])
        else:
            avg_recovery_time = 0
            max_recovery_time = 0
        
        drawdown_analysis = {
            'max_drawdown': max_drawdown,
            'average_drawdown': avg_drawdown,
            'time_underwater_pct': time_underwater,
            'number_of_drawdowns': len(drawdown_periods),
            'average_recovery_time_days': avg_recovery_time,
            'max_recovery_time_days': max_recovery_time,
            'top_5_drawdowns': drawdown_periods[:5],
            'drawdown_series': drawdown
        }
        
        return drawdown_analysis
    
    def _calculate_rolling_metrics(self, daily_returns: np.ndarray, 
                                  window_days: int = 60) -> Dict[str, Any]:
        """Calculate rolling performance metrics"""
        
        if len(daily_returns) < window_days:
            return {}
        
        returns_series = pd.Series(daily_returns)
        
        # Rolling Sharpe ratio
        rolling_sharpe = returns_series.rolling(window_days).apply(
            lambda x: np.mean(x) / np.std(x) * np.sqrt(252) if np.std(x) > 0 else 0
        )
        
        # Rolling volatility
        rolling_vol = returns_series.rolling(window_days).std() * np.sqrt(252)
        
        # Rolling max drawdown
        def rolling_max_dd(x):
            cumulative = (1 + x).cumprod()
            peak = cumulative.expanding().max()
            dd = (cumulative - peak) / peak
            return dd.min()
        
        rolling_max_dd = returns_series.rolling(window_days).apply(rolling_max_dd)
        
        rolling_analysis = {
            'rolling_sharpe_ratio': {
                'mean': rolling_sharpe.mean(),
                'std': rolling_sharpe.std(),
                'min': rolling_sharpe.min(),
                'max': rolling_sharpe.max(),
                'series': rolling_sharpe
            },
            'rolling_volatility': {
                'mean': rolling_vol.mean(),
                'std': rolling_vol.std(),
                'min': rolling_vol.min(),
                'max': rolling_vol.max(),
                'series': rolling_vol
            },
            'rolling_max_drawdown': {
                'mean': rolling_max_dd.mean(),
                'std': rolling_max_dd.std(),
                'min': rolling_max_dd.min(),
                'max': rolling_max_dd.max(),
                'series': rolling_max_dd
            }
        }
        
        return rolling_analysis
    
    def _analyze_periodic_performance(self, portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """Analyze monthly and quarterly performance"""
        
        # Monthly returns
        portfolio_history['year_month'] = portfolio_history.index.to_period('M')
        monthly_returns = portfolio_history.groupby('year_month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        # Quarterly returns
        portfolio_history['year_quarter'] = portfolio_history.index.to_period('Q')
        quarterly_returns = portfolio_history.groupby('year_quarter')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        # Monthly statistics
        monthly_stats = {
            'mean': monthly_returns.mean(),
            'std': monthly_returns.std(),
            'sharpe': monthly_returns.mean() / monthly_returns.std() * np.sqrt(12) if monthly_returns.std() > 0 else 0,
            'best_month': monthly_returns.max(),
            'worst_month': monthly_returns.min(),
            'positive_months': len(monthly_returns[monthly_returns > 0]),
            'total_months': len(monthly_returns),
            'win_rate': len(monthly_returns[monthly_returns > 0]) / len(monthly_returns) if len(monthly_returns) > 0 else 0
        }
        
        # Quarterly statistics
        quarterly_stats = {
            'mean': quarterly_returns.mean(),
            'std': quarterly_returns.std(),
            'sharpe': quarterly_returns.mean() / quarterly_returns.std() * 2 if quarterly_returns.std() > 0 else 0,  # Quarterly Sharpe
            'best_quarter': quarterly_returns.max(),
            'worst_quarter': quarterly_returns.min(),
            'positive_quarters': len(quarterly_returns[quarterly_returns > 0]),
            'total_quarters': len(quarterly_returns)
        }
        
        period_analysis = {
            'monthly_stats': monthly_stats,
            'quarterly_stats': quarterly_stats,
            'monthly_returns': monthly_returns,
            'quarterly_returns': quarterly_returns
        }
        
        return period_analysis
    
    def _analyze_factor_exposure(self, portfolio_history: pd.DataFrame, 
                                trade_history: pd.DataFrame) -> Dict[str, Any]:
        """Analyze factor exposures and style characteristics"""
        
        # Long/Short exposure over time
        long_short_ratio = portfolio_history['long_exposure'] / (portfolio_history['short_exposure'] + 1e-6)
        
        # Net exposure analysis
        net_exposure_stats = {
            'mean': portfolio_history['net_exposure'].mean(),
            'std': portfolio_history['net_exposure'].std(),
            'min': portfolio_history['net_exposure'].min(),
            'max': portfolio_history['net_exposure'].max()
        }
        
        # Turnover analysis (simplified)
        if not trade_history.empty and 'date' in trade_history.columns:
            daily_trade_volume = trade_history.groupby(pd.to_datetime(trade_history['date']).dt.date).apply(
                lambda x: (x['quantity'] * x['price']).sum()
            )
            avg_portfolio_value = portfolio_history['portfolio_value'].mean()
            avg_daily_turnover = daily_trade_volume.mean() / avg_portfolio_value if avg_portfolio_value > 0 else 0
        else:
            avg_daily_turnover = 0
        
        factor_analysis = {
            'net_exposure_stats': net_exposure_stats,
            'long_short_ratio_stats': {
                'mean': long_short_ratio.mean(),
                'std': long_short_ratio.std(),
                'median': long_short_ratio.median()
            },
            'turnover_analysis': {
                'avg_daily_turnover_pct': avg_daily_turnover * 100,
                'annualized_turnover_pct': avg_daily_turnover * 252 * 100
            }
        }
        
        return factor_analysis
    
    def _calculate_max_drawdown_from_returns(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns series"""
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        return np.min(drawdown)
    
    def _calculate_vol_of_vol(self, returns: np.ndarray, window: int = 30) -> float:
        """Calculate volatility of volatility"""
        if len(returns) < window * 2:
            return 0.0
        
        returns_series = pd.Series(returns)
        rolling_vol = returns_series.rolling(window).std()
        vol_of_vol = rolling_vol.std()
        
        return vol_of_vol * np.sqrt(252)  # Annualized
    
    def generate_performance_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate a comprehensive text performance report"""
        
        performance = analysis_results.get('performance_metrics', {})
        risk = analysis_results.get('risk_metrics', {})
        trades = analysis_results.get('trade_metrics', {})
        benchmark = analysis_results.get('benchmark_analysis', {})
        drawdown = analysis_results.get('drawdown_analysis', {})
        
        report = f"""
# Momentum Strategy Performance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
Total Return: {performance.get('total_return', 0):.2%}
Annualized Return: {performance.get('annualized_return', 0):.2%}
Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}
Maximum Drawdown: {performance.get('max_drawdown', 0):.2%}
Win Rate: {performance.get('win_rate', 0):.2%}

## Performance Metrics
- Annualized Volatility: {performance.get('annualized_volatility', 0):.2%}
- Sortino Ratio: {performance.get('sortino_ratio', 0):.2f}
- Calmar Ratio: {performance.get('calmar_ratio', 0):.2f}
- Profit Factor: {performance.get('profit_factor', 0):.2f}
- Best Day: {performance.get('best_day', 0):.2%}
- Worst Day: {performance.get('worst_day', 0):.2%}

## Risk Metrics
- Value at Risk (5%): {performance.get('var_5pct', 0):.2%}
- Conditional VaR (5%): {performance.get('cvar_5pct', 0):.2%}
- Skewness: {performance.get('skewness', 0):.3f}
- Kurtosis: {performance.get('kurtosis', 0):.3f}

## Trading Statistics
Total Trades: {trades.get('trade_summary', {}).get('total_trades', 0)}
Transaction Costs: ${trades.get('cost_analysis', {}).get('total_transaction_costs', 0):,.0f}
Average Commission: ${trades.get('cost_analysis', {}).get('avg_commission', 0):.2f}

## Benchmark Comparison
"""
        
        if benchmark:
            report += f"""
Alpha (Annualized): {benchmark.get('alpha_annualized', 0):.2%}
Beta: {benchmark.get('beta', 0):.2f}
Information Ratio: {benchmark.get('information_ratio', 0):.2f}
Correlation: {benchmark.get('correlation', 0):.3f}
Excess Return: {benchmark.get('excess_return', 0):.2%}
"""
        else:
            report += "No benchmark data available.\n"
        
        report += f"""
## Drawdown Analysis
Maximum Drawdown: {drawdown.get('max_drawdown', 0):.2%}
Average Drawdown: {drawdown.get('average_drawdown', 0):.2%}
Time Underwater: {drawdown.get('time_underwater_pct', 0):.1%}
Number of Drawdowns: {drawdown.get('number_of_drawdowns', 0)}
Average Recovery Time: {drawdown.get('average_recovery_time_days', 0):.0f} days
"""
        
        return report
