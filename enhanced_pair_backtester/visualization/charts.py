"""
Comprehensive charts module for enhanced pair trading system.

This module provides various chart types for analyzing pair trading performance,
including performance charts, walk forward analysis, signals, and risk metrics.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Set professional style
plt.style.use('default')
sns.set_palette("husl")

class PerformanceCharts:
    """Charts for analyzing trading performance and returns."""
    
    def __init__(self, figsize: Tuple[int, int] = (15, 10)):
        self.figsize = figsize
        self.colors = {
            'profit': '#2ca02c',
            'loss': '#d62728',
            'neutral': '#1f77b4',
            'long': '#2ca02c',
            'short': '#d62728',
            'hold': '#808080'
        }
    
    def plot_cumulative_returns(self, returns: np.ndarray, dates: pd.DatetimeIndex = None,
                               title: str = "Cumulative Returns", benchmark_returns: np.ndarray = None) -> plt.Figure:
        """Plot cumulative returns over time."""
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Calculate cumulative returns
        cumulative = np.cumprod(1 + returns)
        
        # Use dates if provided, otherwise use index
        x_axis = dates if dates is not None else np.arange(len(returns))
        
        # Plot main strategy
        ax.plot(x_axis, cumulative, color=self.colors['neutral'], linewidth=2, label='Strategy')
        
        # Plot benchmark if provided
        if benchmark_returns is not None:
            benchmark_cumulative = np.cumprod(1 + benchmark_returns)
            ax.plot(x_axis, benchmark_cumulative, color='gray', linewidth=1, 
                   linestyle='--', label='Benchmark')
        
        # Formatting
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date' if dates is not None else 'Period', fontsize=12)
        ax.set_ylabel('Cumulative Return', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Format x-axis for dates
        if dates is not None:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def plot_drawdown(self, returns: np.ndarray, dates: pd.DatetimeIndex = None,
                     title: str = "Drawdown Analysis") -> plt.Figure:
        """Plot drawdown analysis."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, height_ratios=[2, 1])
        
        # Calculate cumulative returns and drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        x_axis = dates if dates is not None else np.arange(len(returns))
        
        # Plot cumulative returns
        ax1.plot(x_axis, cumulative, color=self.colors['neutral'], linewidth=2)
        ax1.plot(x_axis, running_max, color='gray', linewidth=1, linestyle='--', alpha=0.7)
        ax1.set_title(title, fontsize=16, fontweight='bold')
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Plot drawdown
        ax2.fill_between(x_axis, drawdown, 0, color=self.colors['loss'], alpha=0.3)
        ax2.plot(x_axis, drawdown, color=self.colors['loss'], linewidth=1)
        ax2.set_ylabel('Drawdown', fontsize=12)
        ax2.set_xlabel('Date' if dates is not None else 'Period', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis for dates
        if dates is not None:
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def plot_returns_distribution(self, returns: np.ndarray, 
                                 title: str = "Returns Distribution") -> plt.Figure:
        """Plot returns distribution with statistics."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)
        
        # Histogram
        ax1.hist(returns, bins=50, density=True, alpha=0.7, color=self.colors['neutral'])
        ax1.axvline(np.mean(returns), color=self.colors['profit'], linestyle='--', 
                   label=f'Mean: {np.mean(returns):.4f}')
        ax1.axvline(np.median(returns), color=self.colors['loss'], linestyle='--', 
                   label=f'Median: {np.median(returns):.4f}')
        ax1.set_title('Returns Histogram', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Returns', fontsize=12)
        ax1.set_ylabel('Density', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Q-Q plot
        from scipy import stats
        stats.probplot(returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot (Normal Distribution)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    
    def plot_rolling_metrics(self, returns: np.ndarray, window: int = 252,
                           dates: pd.DatetimeIndex = None,
                           title: str = "Rolling Performance Metrics") -> plt.Figure:
        """Plot rolling performance metrics."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        axes = axes.flatten()
        
        # Calculate rolling metrics
        returns_series = pd.Series(returns, index=dates)
        rolling_return = returns_series.rolling(window).mean() * 252  # Annualized
        rolling_vol = returns_series.rolling(window).std() * np.sqrt(252)  # Annualized
        rolling_sharpe = rolling_return / rolling_vol
        
        # Rolling cumulative returns
        rolling_cumret = returns_series.rolling(window).apply(lambda x: np.prod(1 + x) - 1)
        
        x_axis = dates if dates is not None else np.arange(len(returns))
        
        # Plot rolling returns
        axes[0].plot(x_axis, rolling_return, color=self.colors['neutral'], linewidth=2)
        axes[0].set_title('Rolling Annual Return', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Annual Return', fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # Plot rolling volatility
        axes[1].plot(x_axis, rolling_vol, color=self.colors['loss'], linewidth=2)
        axes[1].set_title('Rolling Annual Volatility', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Annual Volatility', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        # Plot rolling Sharpe ratio
        axes[2].plot(x_axis, rolling_sharpe, color=self.colors['profit'], linewidth=2)
        axes[2].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axes[2].set_title('Rolling Sharpe Ratio', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('Sharpe Ratio', fontsize=10)
        axes[2].grid(True, alpha=0.3)
        
        # Plot rolling cumulative returns
        axes[3].plot(x_axis, rolling_cumret, color=self.colors['neutral'], linewidth=2)
        axes[3].set_title(f'Rolling {window}-Day Cumulative Return', fontsize=12, fontweight='bold')
        axes[3].set_ylabel('Cumulative Return', fontsize=10)
        axes[3].grid(True, alpha=0.3)
        
        # Format x-axis for dates
        if dates is not None:
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig

class WalkForwardCharts:
    """Charts for walk forward analysis results."""
    
    def __init__(self, figsize: Tuple[int, int] = (15, 10)):
        self.figsize = figsize
        self.colors = {
            'performance': '#1f77b4',
            'stability': '#ff7f0e', 
            'success': '#2ca02c',
            'failure': '#d62728'
        }
    
    def plot_period_performance(self, wf_result, title: str = "Walk Forward Period Performance") -> plt.Figure:
        """Plot performance metrics for each walk forward period."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        axes = axes.flatten()
        
        if not wf_result.periods:
            # Empty result
            fig.suptitle("No Walk Forward Results to Display", fontsize=16, fontweight='bold')
            return fig
        
        # Extract data
        periods = wf_result.periods
        dates = [p.test_start for p in periods]
        sharpe_ratios = [p.oos_sharpe for p in periods]
        returns = [p.oos_total_return for p in periods]
        max_drawdowns = [p.oos_max_drawdown for p in periods]
        trade_counts = [p.oos_trades for p in periods]
        
        # Plot Sharpe ratios
        axes[0].plot(dates, sharpe_ratios, 'o-', color=self.colors['performance'], linewidth=2, markersize=4)
        axes[0].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axes[0].set_title('Out-of-Sample Sharpe Ratio', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Sharpe Ratio', fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # Plot returns
        colors = [self.colors['success'] if r > 0 else self.colors['failure'] for r in returns]
        axes[1].bar(dates, [r * 100 for r in returns], color=colors, alpha=0.7)
        axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axes[1].set_title('Out-of-Sample Returns (%)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Return (%)', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        # Plot max drawdowns
        axes[2].bar(dates, [dd * 100 for dd in max_drawdowns], color=self.colors['failure'], alpha=0.7)
        axes[2].set_title('Max Drawdown (%)', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('Drawdown (%)', fontsize=10)
        axes[2].grid(True, alpha=0.3)
        
        # Plot trade counts
        axes[3].bar(dates, trade_counts, color=self.colors['stability'], alpha=0.7)
        axes[3].set_title('Number of Trades', fontsize=12, fontweight='bold')
        axes[3].set_ylabel('Trade Count', fontsize=10)
        axes[3].grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    
    def plot_parameter_stability(self, wf_result, title: str = "Parameter Stability Analysis") -> plt.Figure:
        """Plot parameter stability across periods."""
        if not wf_result.periods:
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No Walk Forward Results to Display', 
                   ha='center', va='center', fontsize=16, transform=ax.transAxes)
            return fig
        
        # Extract parameter data
        periods = wf_result.periods
        dates = [p.test_start for p in periods]
        
        # Get all parameter names
        param_names = set()
        for period in periods:
            param_names.update(period.best_parameters.keys())
        param_names = sorted(param_names)
        
        # Create subplots
        n_params = len(param_names)
        if n_params == 0:
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No Parameters to Display', 
                   ha='center', va='center', fontsize=16, transform=ax.transAxes)
            return fig
        
        nrows = (n_params + 1) // 2
        ncols = min(2, n_params)
        
        fig, axes = plt.subplots(nrows, ncols, figsize=self.figsize)
        if nrows == 1 and ncols == 1:
            axes = [axes]
        elif nrows == 1 or ncols == 1:
            axes = axes.flatten()
        else:
            axes = axes.flatten()
        
        # Plot each parameter
        for i, param_name in enumerate(param_names):
            if i >= len(axes):
                break
                
            values = [p.best_parameters.get(param_name, 0) for p in periods]
            
            axes[i].plot(dates, values, 'o-', linewidth=2, markersize=4)
            axes[i].set_title(f'{param_name}', fontsize=12, fontweight='bold')
            axes[i].set_ylabel('Value', fontsize=10)
            axes[i].grid(True, alpha=0.3)
            
            # Format x-axis
            axes[i].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            axes[i].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(axes[i].xaxis.get_majorticklabels(), rotation=45)
        
        # Hide unused subplots
        for i in range(len(param_names), len(axes)):
            axes[i].set_visible(False)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig

class SignalCharts:
    """Charts for analyzing trading signals and positions."""
    
    def __init__(self, figsize: Tuple[int, int] = (15, 10)):
        self.figsize = figsize
        self.colors = {
            'long': '#2ca02c',
            'short': '#d62728',
            'hold': '#808080',
            'spread': '#1f77b4',
            'z_score': '#ff7f0e'
        }
    
    def plot_spread_and_signals(self, spread_data: pd.DataFrame, signals: pd.DataFrame = None,
                               title: str = "Spread Analysis with Trading Signals") -> plt.Figure:
        """Plot spread, z-score, and trading signals."""
        fig, axes = plt.subplots(3, 1, figsize=self.figsize, height_ratios=[2, 1, 1])
        
        dates = spread_data.index
        
        # Plot spread
        axes[0].plot(dates, spread_data['spread'], color=self.colors['spread'], linewidth=1)
        axes[0].set_title('Price Spread', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Spread', fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # Plot z-score
        axes[1].plot(dates, spread_data['z_score'], color=self.colors['z_score'], linewidth=1)
        axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axes[1].axhline(y=2, color='red', linestyle='--', alpha=0.5, label='Entry Threshold')
        axes[1].axhline(y=-2, color='red', linestyle='--', alpha=0.5)
        axes[1].axhline(y=1, color='green', linestyle='--', alpha=0.5, label='Exit Threshold')
        axes[1].axhline(y=-1, color='green', linestyle='--', alpha=0.5)
        axes[1].set_title('Z-Score', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Z-Score', fontsize=10)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot signals if provided
        if signals is not None:
            signal_colors = []
            for signal in signals['signal_type']:
                if signal == 'LONG':
                    signal_colors.append(self.colors['long'])
                elif signal == 'SHORT':
                    signal_colors.append(self.colors['short'])
                else:
                    signal_colors.append(self.colors['hold'])
            
            axes[2].scatter(signals.index, signals['position_size'], 
                          c=signal_colors, alpha=0.7, s=20)
            axes[2].axhline(y=0, color='black', linestyle='-', alpha=0.3)
            axes[2].set_title('Position Size', fontsize=12, fontweight='bold')
            axes[2].set_ylabel('Position', fontsize=10)
            axes[2].grid(True, alpha=0.3)
        else:
            axes[2].text(0.5, 0.5, 'No Signal Data Available', 
                        ha='center', va='center', fontsize=12, transform=axes[2].transAxes)
        
        # Format x-axis
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig

class RiskCharts:
    """Charts for risk analysis and metrics."""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize
        self.colors = {
            'var': '#d62728',
            'es': '#ff7f0e',
            'returns': '#1f77b4'
        }
    
    def plot_risk_metrics(self, returns: np.ndarray, 
                         title: str = "Risk Analysis") -> plt.Figure:
        """Plot comprehensive risk metrics."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        axes = axes.flatten()
        
        # VaR analysis
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        axes[0].hist(returns, bins=50, density=True, alpha=0.7, color=self.colors['returns'])
        axes[0].axvline(var_95, color=self.colors['var'], linestyle='--', 
                       label=f'VaR 95%: {var_95:.4f}')
        axes[0].axvline(var_99, color=self.colors['es'], linestyle='--', 
                       label=f'VaR 99%: {var_99:.4f}')
        axes[0].set_title('Value at Risk (VaR)', fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Returns', fontsize=10)
        axes[0].set_ylabel('Density', fontsize=10)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Rolling volatility
        rolling_vol = pd.Series(returns).rolling(30).std() * np.sqrt(252)
        axes[1].plot(rolling_vol, color=self.colors['var'], linewidth=2)
        axes[1].set_title('Rolling 30-Day Volatility (Annualized)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Volatility', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        # Return autocorrelation
        from statsmodels.tsa.stattools import acf
        lags = 20
        autocorr = acf(returns, nlags=lags)
        axes[2].bar(range(lags+1), autocorr, color=self.colors['returns'], alpha=0.7)
        axes[2].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        axes[2].set_title('Return Autocorrelation', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('Lag', fontsize=10)
        axes[2].set_ylabel('Autocorrelation', fontsize=10)
        axes[2].grid(True, alpha=0.3)
        
        # Tail risk
        tail_returns = returns[returns <= var_95]
        if len(tail_returns) > 0:
            expected_shortfall = np.mean(tail_returns)
            axes[3].hist(tail_returns, bins=20, density=True, alpha=0.7, color=self.colors['es'])
            axes[3].axvline(expected_shortfall, color='red', linestyle='--', 
                           label=f'Expected Shortfall: {expected_shortfall:.4f}')
            axes[3].set_title('Tail Risk (5% Worst Returns)', fontsize=12, fontweight='bold')
            axes[3].set_xlabel('Returns', fontsize=10)
            axes[3].set_ylabel('Density', fontsize=10)
            axes[3].legend()
            axes[3].grid(True, alpha=0.3)
        else:
            axes[3].text(0.5, 0.5, 'Insufficient tail data', 
                        ha='center', va='center', fontsize=12, transform=axes[3].transAxes)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig 