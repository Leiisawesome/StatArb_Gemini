"""
Trading Dashboard for enhanced pair trading system.

This module provides a comprehensive dashboard that combines all visualization
components for analyzing pair trading performance and results.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

from .charts import PerformanceCharts, WalkForwardCharts, SignalCharts, RiskCharts

class TradingDashboard:
    """Comprehensive trading dashboard for pair trading analysis."""
    
    def __init__(self, figsize=(20, 15)):
        self.figsize = figsize
        self.performance_charts = PerformanceCharts()
        self.walkforward_charts = WalkForwardCharts()
        self.signal_charts = SignalCharts()
        self.risk_charts = RiskCharts()
    
    def create_performance_dashboard(self, returns: np.ndarray, 
                                   dates: pd.DatetimeIndex = None,
                                   benchmark_returns: np.ndarray = None,
                                   title: str = "Performance Dashboard") -> plt.Figure:
        """Create comprehensive performance dashboard."""
        fig = plt.figure(figsize=self.figsize)
        
        # Create subplot layout
        gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.3)
        
        # Cumulative returns (top row, full width)
        ax1 = fig.add_subplot(gs[0, :])
        cumulative = np.cumprod(1 + returns)
        x_axis = dates if dates is not None else np.arange(len(returns))
        ax1.plot(x_axis, cumulative, color='#1f77b4', linewidth=2, label='Strategy')
        
        if benchmark_returns is not None:
            benchmark_cumulative = np.cumprod(1 + benchmark_returns)
            ax1.plot(x_axis, benchmark_cumulative, color='gray', linewidth=1, 
                    linestyle='--', label='Benchmark')
        
        ax1.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Drawdown (middle left)
        ax2 = fig.add_subplot(gs[1, 0])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        ax2.fill_between(x_axis, drawdown, 0, color='#d62728', alpha=0.3)
        ax2.plot(x_axis, drawdown, color='#d62728', linewidth=1)
        ax2.set_title('Drawdown', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Drawdown', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # Returns distribution (middle right)
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.hist(returns, bins=30, density=True, alpha=0.7, color='#1f77b4')
        ax3.axvline(np.mean(returns), color='#2ca02c', linestyle='--', 
                   label=f'Mean: {np.mean(returns):.4f}')
        ax3.set_title('Returns Distribution', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Returns', fontsize=10)
        ax3.set_ylabel('Density', fontsize=10)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Performance metrics (bottom left)
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.axis('off')
        
        # Calculate metrics
        total_return = np.prod(1 + returns) - 1
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        max_drawdown = np.min(drawdown)
        win_rate = np.mean(returns > 0)
        
        metrics_text = f"""
        Performance Metrics:
        
        Total Return: {total_return:.2%}
        Sharpe Ratio: {sharpe_ratio:.3f}
        Max Drawdown: {max_drawdown:.2%}
        Win Rate: {win_rate:.2%}
        
        Volatility: {np.std(returns) * np.sqrt(252):.2%}
        Skewness: {pd.Series(returns).skew():.3f}
        Kurtosis: {pd.Series(returns).kurtosis():.3f}
        """
        
        ax4.text(0.1, 0.9, metrics_text, transform=ax4.transAxes, fontsize=11,
                verticalalignment='top', fontfamily='monospace')
        
        # Risk metrics (bottom right)
        ax5 = fig.add_subplot(gs[2, 1])
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        ax5.hist(returns, bins=30, density=True, alpha=0.7, color='#1f77b4')
        ax5.axvline(var_95, color='#d62728', linestyle='--', label=f'VaR 95%: {var_95:.4f}')
        ax5.axvline(var_99, color='#ff7f0e', linestyle='--', label=f'VaR 99%: {var_99:.4f}')
        ax5.set_title('Risk Metrics', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Returns', fontsize=10)
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    
    def create_walkforward_dashboard(self, wf_result, 
                                   title: str = "Walk Forward Analysis Dashboard") -> plt.Figure:
        """Create walk forward analysis dashboard."""
        if not wf_result.periods:
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No Walk Forward Results Available', 
                   ha='center', va='center', fontsize=20, transform=ax.transAxes)
            fig.suptitle(title, fontsize=16, fontweight='bold')
            return fig
        
        fig = plt.figure(figsize=self.figsize)
        gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], hspace=0.4, wspace=0.3)
        
        # Extract data
        periods = wf_result.periods
        dates = [p.test_start for p in periods]
        sharpe_ratios = [p.oos_sharpe for p in periods]
        returns = [p.oos_total_return for p in periods]
        max_drawdowns = [p.oos_max_drawdown for p in periods]
        trade_counts = [p.oos_trades for p in periods]
        
        # Sharpe ratios over time
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(dates, sharpe_ratios, 'o-', color='#1f77b4', linewidth=2, markersize=4)
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax1.set_title('Out-of-Sample Sharpe Ratio', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Sharpe Ratio', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Returns over time
        ax2 = fig.add_subplot(gs[0, 1])
        colors = ['#2ca02c' if r > 0 else '#d62728' for r in returns]
        ax2.bar(dates, [r * 100 for r in returns], color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.set_title('Out-of-Sample Returns (%)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Return (%)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # Performance distribution
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.hist(sharpe_ratios, bins=15, density=True, alpha=0.7, color='#1f77b4')
        ax3.axvline(np.mean(sharpe_ratios), color='#2ca02c', linestyle='--', 
                   label=f'Mean: {np.mean(sharpe_ratios):.3f}')
        ax3.set_title('Sharpe Ratio Distribution', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Sharpe Ratio', fontsize=10)
        ax3.set_ylabel('Density', fontsize=10)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Trade counts
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.bar(dates, trade_counts, color='#ff7f0e', alpha=0.7)
        ax4.set_title('Number of Trades per Period', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Trade Count', fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # Summary statistics
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        summary_text = f"""
        Walk Forward Analysis Summary:
        
        Total Periods: {wf_result.total_periods}                    Successful Periods: {wf_result.successful_periods}
        Success Rate: {wf_result.successful_periods/wf_result.total_periods*100:.1f}%          Aggregate Sharpe: {wf_result.aggregate_sharpe:.3f}
        Aggregate Return: {wf_result.aggregate_total_return*100:.2f}%            Max Drawdown: {wf_result.aggregate_max_drawdown*100:.2f}%
        
        Stability Metrics:
        Sharpe Stability: {wf_result.sharpe_stability:.3f}          Return Stability: {wf_result.return_stability:.3f}
        """
        
        ax5.text(0.1, 0.9, summary_text, transform=ax5.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace')
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    
    def create_signal_dashboard(self, spread_data: pd.DataFrame, 
                              signals: pd.DataFrame = None,
                              title: str = "Signal Analysis Dashboard") -> plt.Figure:
        """Create signal analysis dashboard."""
        fig = plt.figure(figsize=self.figsize)
        gs = fig.add_gridspec(4, 2, height_ratios=[1, 1, 1, 1], hspace=0.4, wspace=0.3)
        
        dates = spread_data.index
        
        # Price spread
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(dates, spread_data['spread'], color='#1f77b4', linewidth=1)
        ax1.set_title('Price Spread', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Spread', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Z-score
        ax2 = fig.add_subplot(gs[1, :])
        ax2.plot(dates, spread_data['z_score'], color='#ff7f0e', linewidth=1)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.axhline(y=2, color='red', linestyle='--', alpha=0.5, label='Entry (+2)')
        ax2.axhline(y=-2, color='red', linestyle='--', alpha=0.5, label='Entry (-2)')
        ax2.axhline(y=1, color='green', linestyle='--', alpha=0.5, label='Exit (+1)')
        ax2.axhline(y=-1, color='green', linestyle='--', alpha=0.5, label='Exit (-1)')
        ax2.set_title('Z-Score with Trading Thresholds', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Z-Score', fontsize=10)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Spread distribution
        ax3 = fig.add_subplot(gs[2, 0])
        ax3.hist(spread_data['spread'], bins=30, density=True, alpha=0.7, color='#1f77b4')
        ax3.axvline(np.mean(spread_data['spread']), color='#2ca02c', linestyle='--', 
                   label=f'Mean: {np.mean(spread_data["spread"]):.4f}')
        ax3.set_title('Spread Distribution', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Spread', fontsize=10)
        ax3.set_ylabel('Density', fontsize=10)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Z-score distribution
        ax4 = fig.add_subplot(gs[2, 1])
        ax4.hist(spread_data['z_score'], bins=30, density=True, alpha=0.7, color='#ff7f0e')
        ax4.axvline(0, color='black', linestyle='-', alpha=0.3)
        ax4.axvline(2, color='red', linestyle='--', alpha=0.5)
        ax4.axvline(-2, color='red', linestyle='--', alpha=0.5)
        ax4.set_title('Z-Score Distribution', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Z-Score', fontsize=10)
        ax4.set_ylabel('Density', fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # Signal analysis
        ax5 = fig.add_subplot(gs[3, :])
        if signals is not None:
            signal_colors = []
            for signal in signals['signal_type']:
                if signal == 'LONG':
                    signal_colors.append('#2ca02c')
                elif signal == 'SHORT':
                    signal_colors.append('#d62728')
                else:
                    signal_colors.append('#808080')
            
            ax5.scatter(signals.index, signals['position_size'], 
                       c=signal_colors, alpha=0.7, s=20)
            ax5.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax5.set_title('Trading Signals and Position Sizes', fontsize=12, fontweight='bold')
            ax5.set_ylabel('Position Size', fontsize=10)
            ax5.grid(True, alpha=0.3)
        else:
            ax5.text(0.5, 0.5, 'No Signal Data Available', 
                    ha='center', va='center', fontsize=14, transform=ax5.transAxes)
            ax5.set_title('Trading Signals', fontsize=12, fontweight='bold')
        
        fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    
    def save_dashboard(self, fig: plt.Figure, filename: str, dpi: int = 300) -> None:
        """Save dashboard to file."""
        fig.savefig(filename, dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"Dashboard saved to {filename}")
    
    def show_dashboard(self, fig: plt.Figure) -> None:
        """Display dashboard."""
        plt.show()
    
    def close_all(self) -> None:
        """Close all figures."""
        plt.close('all') 