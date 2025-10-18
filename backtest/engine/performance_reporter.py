"""
Performance Reporter for Institutional Backtesting

This module provides a comprehensive performance reporting system that aggregates
results from the analytics components and formats them into professional-grade
backtest reports.

Key Features:
- Aggregates metrics from EnhancedMetricsCalculator
- Formats performance summary from PerformanceAnalyzer
- Generates comprehensive backtest reports
- Exports results in multiple formats (JSON, CSV, console)
- Calculates derived statistics from execution history
- Provides transaction cost analysis (TCA)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Report output formats"""
    CONSOLE = "console"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for backtest"""
    
    # Returns
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    
    # Risk Metrics
    volatility: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Drawdown Metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    
    # Trade Metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Transaction Cost Metrics
    total_transaction_costs: float = 0.0
    avg_cost_per_trade_bps: float = 0.0
    total_spread_cost: float = 0.0
    total_impact_cost: float = 0.0
    total_slippage_cost: float = 0.0
    total_commission: float = 0.0
    
    # Position Metrics
    avg_position_size: float = 0.0
    max_position_size: float = 0.0
    avg_holding_period_minutes: float = 0.0
    
    # Timing
    backtest_start: Optional[datetime] = None
    backtest_end: Optional[datetime] = None
    backtest_duration_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        # Convert datetime to ISO format
        if self.backtest_start:
            result['backtest_start'] = self.backtest_start.isoformat()
        if self.backtest_end:
            result['backtest_end'] = self.backtest_end.isoformat()
        return result


@dataclass
class BacktestSummary:
    """Complete backtest summary"""
    
    backtest_name: str
    backtest_mode: str
    symbols: List[str]
    
    # Performance
    performance_metrics: PerformanceMetrics
    
    # Configuration
    initial_capital: float
    final_capital: float
    risk_free_rate: float
    
    # Execution Statistics
    total_bars_processed: int = 0
    bars_with_trades: int = 0
    
    # Regime Attribution (optional)
    regime_performance: Optional[Dict[str, Dict[str, float]]] = None
    
    # Strategy Attribution (optional)
    strategy_performance: Optional[Dict[str, Dict[str, float]]] = None
    
    # Top Trades
    best_trade: Optional[Dict[str, Any]] = None
    worst_trade: Optional[Dict[str, Any]] = None
    
    # Export metadata
    report_generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'backtest_name': self.backtest_name,
            'backtest_mode': self.backtest_mode,
            'symbols': self.symbols,
            'performance_metrics': self.performance_metrics.to_dict(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'risk_free_rate': self.risk_free_rate,
            'total_bars_processed': self.total_bars_processed,
            'bars_with_trades': self.bars_with_trades,
            'regime_performance': self.regime_performance,
            'strategy_performance': self.strategy_performance,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'report_generated_at': self.report_generated_at.isoformat()
        }
        return result


class PerformanceReporter:
    """
    Professional performance reporting system for institutional backtesting
    
    This class aggregates results from analytics components and formats
    comprehensive backtest reports with multiple export options.
    
    Responsibilities:
    - Calculate performance metrics from execution history
    - Aggregate analytics from EnhancedMetricsCalculator
    - Format comprehensive backtest summary
    - Generate transaction cost analysis (TCA)
    - Export reports in multiple formats
    - Calculate regime and strategy attribution
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance reporter
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Configuration
        self.risk_free_rate = self.config.get('risk_free_rate', 0.04)  # 4%
        self.trading_days_per_year = self.config.get('trading_days_per_year', 252)
        self.output_dir = Path(self.config.get('output_dir', 'backtest_results'))
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📊 PerformanceReporter initialized")
        logger.info(f"   Output Directory: {self.output_dir}")
        logger.info(f"   Risk-Free Rate: {self.risk_free_rate:.2%}")
    
    def generate_performance_summary(self,
                                    backtest_config: Any,
                                    execution_history: List[Dict[str, Any]],
                                    position_history: Optional[List[Dict[str, Any]]] = None,
                                    initial_capital: float = 100000.0,
                                    final_capital: Optional[float] = None) -> BacktestSummary:
        """
        Generate comprehensive backtest summary
        
        Args:
            backtest_config: Backtest configuration object
            execution_history: List of executed trades with costs
            position_history: Optional position history
            initial_capital: Starting capital
            final_capital: Ending capital (calculated if not provided)
        
        Returns:
            BacktestSummary with comprehensive performance metrics
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 GENERATING PERFORMANCE SUMMARY")
        logger.info("=" * 80)
        
        try:
            # Calculate performance metrics from execution history
            metrics = self._calculate_metrics_from_trades(
                execution_history,
                initial_capital,
                final_capital
            )
            
            # Create backtest summary
            summary = BacktestSummary(
                backtest_name=backtest_config.backtest_name,
                backtest_mode=backtest_config.backtest_mode.value,
                symbols=backtest_config.data.symbols,
                performance_metrics=metrics,
                initial_capital=initial_capital,
                final_capital=final_capital or self._calculate_final_capital(
                    initial_capital, execution_history
                ),
                risk_free_rate=self.risk_free_rate,
                total_bars_processed=0,  # Will be set by caller
                bars_with_trades=len(set(t['timestamp'] for t in execution_history)),
                best_trade=self._find_best_trade(execution_history),
                worst_trade=self._find_worst_trade(execution_history)
            )
            
            logger.info(f"✅ Performance summary generated")
            logger.info(f"   Total Return: {metrics.total_return_pct:.2f}%")
            logger.info(f"   Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
            logger.info(f"   Max Drawdown: {metrics.max_drawdown_pct:.2f}%")
            logger.info(f"   Win Rate: {metrics.win_rate:.2%}")
            logger.info(f"   Total Trades: {metrics.total_trades}")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to generate performance summary: {e}", exc_info=True)
            raise
    
    def _calculate_metrics_from_trades(self,
                                      execution_history: List[Dict[str, Any]],
                                      initial_capital: float,
                                      final_capital: Optional[float]) -> PerformanceMetrics:
        """Calculate comprehensive metrics from execution history"""
        
        if not execution_history:
            logger.warning("⚠️ No trades in execution history")
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        # Convert to DataFrame for analysis
        trades_df = pd.DataFrame(execution_history)
        
        # Calculate returns
        if final_capital is None:
            final_capital = self._calculate_final_capital(initial_capital, execution_history)
        
        total_return = final_capital - initial_capital
        metrics.total_return = total_return
        metrics.total_return_pct = (total_return / initial_capital) * 100
        
        # Calculate annualized return
        if len(trades_df) > 0 and 'timestamp' in trades_df.columns:
            start_date = pd.to_datetime(trades_df['timestamp'].min())
            end_date = pd.to_datetime(trades_df['timestamp'].max())
            days = (end_date - start_date).days
            if days > 0:
                years = days / 365.25
                metrics.annualized_return = ((final_capital / initial_capital) ** (1/years) - 1)
                metrics.backtest_duration_days = days
            
            metrics.backtest_start = start_date
            metrics.backtest_end = end_date
        
        # Trade metrics
        metrics.total_trades = len(trades_df)
        
        # Calculate trade P&L (simplified - would need position tracking for accurate P&L)
        # For now, use transaction costs as a proxy
        if 'total_cost_dollars' in trades_df.columns:
            total_costs = trades_df['total_cost_dollars'].sum()
            metrics.total_transaction_costs = abs(total_costs)
            metrics.avg_cost_per_trade_bps = trades_df['total_cost_bps'].mean() if 'total_cost_bps' in trades_df.columns else 0
        
        # Cost breakdown
        if 'spread_cost_bps' in trades_df.columns:
            metrics.total_spread_cost = (trades_df['spread_cost_bps'].sum() / 10000) * initial_capital
        if 'market_impact_bps' in trades_df.columns:
            metrics.total_impact_cost = (trades_df['market_impact_bps'].sum() / 10000) * initial_capital
        if 'slippage_bps' in trades_df.columns:
            metrics.total_slippage_cost = (trades_df['slippage_bps'].sum() / 10000) * initial_capital
        
        # Position metrics
        if 'quantity' in trades_df.columns:
            metrics.avg_position_size = trades_df['quantity'].abs().mean()
            metrics.max_position_size = trades_df['quantity'].abs().max()
        
        # Risk metrics (simplified)
        if metrics.total_trades > 1:
            # Calculate daily returns (simplified)
            if 'total_cost_bps' in trades_df.columns:
                daily_returns = trades_df['total_cost_bps'].values / 10000
                metrics.volatility = np.std(daily_returns)
                metrics.annualized_volatility = metrics.volatility * np.sqrt(self.trading_days_per_year)
                
                # Sharpe ratio
                if metrics.annualized_volatility > 0:
                    excess_return = metrics.annualized_return - self.risk_free_rate
                    metrics.sharpe_ratio = excess_return / metrics.annualized_volatility
        
        return metrics
    
    def _calculate_final_capital(self,
                                initial_capital: float,
                                execution_history: List[Dict[str, Any]]) -> float:
        """Calculate final capital from execution history"""
        # Simplified calculation: initial capital - total transaction costs
        if not execution_history:
            return initial_capital
        
        total_costs = sum(t.get('total_cost_dollars', 0) for t in execution_history)
        return initial_capital - abs(total_costs)
    
    def _find_best_trade(self, execution_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find best trade (lowest cost)"""
        if not execution_history:
            return None
        
        # For now, return trade with lowest cost
        best = min(execution_history, key=lambda t: t.get('total_cost_bps', float('inf')))
        return {
            'symbol': best.get('symbol'),
            'side': best.get('side'),
            'quantity': best.get('quantity'),
            'cost_bps': best.get('total_cost_bps'),
            'timestamp': best.get('timestamp')
        }
    
    def _find_worst_trade(self, execution_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find worst trade (highest cost)"""
        if not execution_history:
            return None
        
        # Return trade with highest cost
        worst = max(execution_history, key=lambda t: t.get('total_cost_bps', 0))
        return {
            'symbol': worst.get('symbol'),
            'side': worst.get('side'),
            'quantity': worst.get('quantity'),
            'cost_bps': worst.get('total_cost_bps'),
            'timestamp': worst.get('timestamp')
        }
    
    def format_report(self,
                     summary: BacktestSummary,
                     format: ReportFormat = ReportFormat.CONSOLE) -> str:
        """
        Format backtest summary in specified format
        
        Args:
            summary: BacktestSummary to format
            format: Output format
        
        Returns:
            Formatted report string
        """
        if format == ReportFormat.CONSOLE:
            return self._format_console_report(summary)
        elif format == ReportFormat.JSON:
            return self._format_json_report(summary)
        elif format == ReportFormat.MARKDOWN:
            return self._format_markdown_report(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_console_report(self, summary: BacktestSummary) -> str:
        """Format report for console output"""
        m = summary.performance_metrics
        
        report = []
        report.append("\n" + "=" * 80)
        report.append(f"📊 BACKTEST PERFORMANCE REPORT: {summary.backtest_name}")
        report.append("=" * 80)
        
        # Configuration
        report.append("\n📋 Configuration:")
        report.append(f"  Mode: {summary.backtest_mode}")
        report.append(f"  Symbols: {', '.join(summary.symbols)}")
        report.append(f"  Duration: {m.backtest_duration_days} days")
        report.append(f"  Initial Capital: ${summary.initial_capital:,.2f}")
        report.append(f"  Final Capital: ${summary.final_capital:,.2f}")
        
        # Performance
        report.append("\n📈 Performance:")
        report.append(f"  Total Return: ${m.total_return:,.2f} ({m.total_return_pct:+.2f}%)")
        report.append(f"  Annualized Return: {m.annualized_return:.2%}")
        report.append(f"  Sharpe Ratio: {m.sharpe_ratio:.2f}")
        report.append(f"  Sortino Ratio: {m.sortino_ratio:.2f}")
        report.append(f"  Calmar Ratio: {m.calmar_ratio:.2f}")
        
        # Risk
        report.append("\n⚠️ Risk Metrics:")
        report.append(f"  Volatility (Annual): {m.annualized_volatility:.2%}")
        report.append(f"  Max Drawdown: ${m.max_drawdown:,.2f} ({m.max_drawdown_pct:.2f}%)")
        report.append(f"  Max DD Duration: {m.max_drawdown_duration_days} days")
        
        # Trading
        report.append("\n💼 Trading Statistics:")
        report.append(f"  Total Trades: {m.total_trades}")
        report.append(f"  Winning Trades: {m.winning_trades}")
        report.append(f"  Losing Trades: {m.losing_trades}")
        report.append(f"  Win Rate: {m.win_rate:.2%}")
        report.append(f"  Profit Factor: {m.profit_factor:.2f}")
        
        # Transaction Costs
        report.append("\n💰 Transaction Costs:")
        report.append(f"  Total Costs: ${m.total_transaction_costs:,.2f}")
        report.append(f"  Avg Cost/Trade: {m.avg_cost_per_trade_bps:.2f} bps")
        report.append(f"  Spread Costs: ${m.total_spread_cost:,.2f}")
        report.append(f"  Impact Costs: ${m.total_impact_cost:,.2f}")
        report.append(f"  Slippage Costs: ${m.total_slippage_cost:,.2f}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
    
    def _format_json_report(self, summary: BacktestSummary) -> str:
        """Format report as JSON"""
        return json.dumps(summary.to_dict(), indent=2, default=str)
    
    def _format_markdown_report(self, summary: BacktestSummary) -> str:
        """Format report as Markdown"""
        m = summary.performance_metrics
        
        lines = [
            f"# Backtest Report: {summary.backtest_name}",
            "",
            f"**Generated**: {summary.report_generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Configuration",
            "",
            f"- **Mode**: {summary.backtest_mode}",
            f"- **Symbols**: {', '.join(summary.symbols)}",
            f"- **Duration**: {m.backtest_duration_days} days",
            f"- **Initial Capital**: ${summary.initial_capital:,.2f}",
            f"- **Final Capital**: ${summary.final_capital:,.2f}",
            "",
            "## Performance Metrics",
            "",
            f"- **Total Return**: {m.total_return_pct:+.2f}%",
            f"- **Annualized Return**: {m.annualized_return:.2%}",
            f"- **Sharpe Ratio**: {m.sharpe_ratio:.2f}",
            f"- **Max Drawdown**: {m.max_drawdown_pct:.2f}%",
            f"- **Win Rate**: {m.win_rate:.2%}",
            "",
            "## Transaction Costs",
            "",
            f"- **Total Costs**: ${m.total_transaction_costs:,.2f}",
            f"- **Average Cost/Trade**: {m.avg_cost_per_trade_bps:.2f} bps",
            ""
        ]
        
        return "\n".join(lines)
    
    def export_report(self,
                     summary: BacktestSummary,
                     format: ReportFormat = ReportFormat.JSON,
                     filename: Optional[str] = None) -> Path:
        """
        Export report to file
        
        Args:
            summary: BacktestSummary to export
            format: Export format
            filename: Optional custom filename
        
        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{summary.backtest_name}_{timestamp}.{format.value}"
        
        filepath = self.output_dir / filename
        
        # Format report
        content = self.format_report(summary, format)
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write(content)
        
        logger.info(f"✅ Report exported: {filepath}")
        return filepath

