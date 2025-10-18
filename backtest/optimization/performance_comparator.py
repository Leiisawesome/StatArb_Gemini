"""
Performance Comparator

Compare and rank strategy performance across configurations and symbols.

Features:
- Side-by-side comparison
- Statistical significance testing
- Symbol comparison
- Performance ranking
- Report generation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from scipy import stats


logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result from performance comparison"""
    compared_items: List[str]
    best_item: str
    rankings: Dict[str, int]
    metrics_comparison: pd.DataFrame
    statistical_significance: Dict[str, Any]
    timestamp: datetime


class PerformanceComparator:
    """
    Compare strategy performance with statistical analysis.
    
    Provides comprehensive comparison across configurations and symbols.
    """
    
    def __init__(self):
        """Initialize performance comparator"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.comparison_history: List[ComparisonResult] = []
        self.logger.info("PerformanceComparator initialized")
    
    def compare_strategies(
        self,
        results: List[Dict[str, Any]],
        primary_metric: str = "sharpe_ratio",
        include_statistical_tests: bool = True
    ) -> ComparisonResult:
        """
        Compare multiple strategy results.
        
        Args:
            results: List of strategy results (dicts with metrics)
            primary_metric: Primary metric for ranking
            include_statistical_tests: Whether to run statistical tests
        
        Returns:
            Comparison result
        """
        if not results:
            self.logger.warning("No results provided for comparison")
            return None
        
        self.logger.info(f"Comparing {len(results)} configurations")
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(results)
        
        # Calculate rankings
        rankings = self._calculate_rankings(comparison_df, primary_metric)
        
        # Find best
        best_idx = rankings[primary_metric].idxmin()  # Rank 1 is best
        best_item = str(results[best_idx].get('strategy_type', 'Unknown')) + ":" + \
                   str(results[best_idx].get('symbol', 'default'))
        
        # Statistical significance
        if include_statistical_tests and len(results) > 1:
            significance = self._test_statistical_significance(results, primary_metric)
        else:
            significance = {}
        
        # Create result
        item_names = [
            f"{r.get('strategy_type', 'Unknown')}:{r.get('symbol', 'default')}"
            for r in results
        ]
        
        comparison_result = ComparisonResult(
            compared_items=item_names,
            best_item=best_item,
            rankings=rankings.to_dict(),
            metrics_comparison=comparison_df,
            statistical_significance=significance,
            timestamp=datetime.now()
        )
        
        self.comparison_history.append(comparison_result)
        
        self.logger.info(f"Comparison complete. Best: {best_item}")
        
        return comparison_result
    
    def compare_parameters(
        self,
        results: List[Dict[str, Any]],
        parameter_name: str,
        metric: str = "sharpe_ratio"
    ) -> pd.DataFrame:
        """
        Compare performance across parameter values.
        
        Args:
            results: List of results
            parameter_name: Parameter to analyze
            metric: Performance metric
        
        Returns:
            DataFrame with parameter values and metrics
        """
        if not results:
            return pd.DataFrame()
        
        # Extract parameter values and metrics
        data = []
        for result in results:
            params = result.get('parameters', {})
            if parameter_name in params:
                data.append({
                    'parameter_value': params[parameter_name],
                    metric: result.get(metric, np.nan)
                })
        
        if not data:
            self.logger.warning(f"No data found for parameter: {parameter_name}")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Group by parameter value and calculate statistics
        grouped = df.groupby('parameter_value')[metric].agg([
            'count', 'mean', 'std', 'min', 'max'
        ]).reset_index()
        
        grouped = grouped.sort_values('mean', ascending=False)
        
        return grouped
    
    def compare_symbols(
        self,
        results: List[Dict[str, Any]],
        strategy_type: str,
        metric: str = "sharpe_ratio"
    ) -> pd.DataFrame:
        """
        Compare performance across symbols for a strategy.
        
        Args:
            results: List of results
            strategy_type: Strategy type to filter
            metric: Performance metric
        
        Returns:
            DataFrame with symbol comparison
        """
        # Filter by strategy type
        filtered = [r for r in results if r.get('strategy_type') == strategy_type]
        
        if not filtered:
            self.logger.warning(f"No results found for strategy: {strategy_type}")
            return pd.DataFrame()
        
        # Group by symbol
        data = []
        for result in filtered:
            symbol = result.get('symbol', 'default')
            data.append({
                'symbol': symbol,
                'sharpe_ratio': result.get('sharpe_ratio', np.nan),
                'max_drawdown': result.get('max_drawdown', np.nan),
                'win_rate': result.get('win_rate', np.nan),
                'profit_factor': result.get('profit_factor', np.nan),
                'trade_count': result.get('trade_count', 0)
            })
        
        df = pd.DataFrame(data)
        
        # Sort by metric
        df = df.sort_values(metric, ascending=(metric == 'max_drawdown'))
        
        return df
    
    def _calculate_rankings(
        self,
        df: pd.DataFrame,
        primary_metric: str
    ) -> pd.DataFrame:
        """
        Calculate rankings for each metric.
        
        Args:
            df: DataFrame with metrics
            primary_metric: Primary metric for ranking
        
        Returns:
            DataFrame with rankings (1 = best)
        """
        rankings = pd.DataFrame()
        
        # Metrics where higher is better
        maximize_metrics = ['sharpe_ratio', 'win_rate', 'profit_factor', 'total_return', 'trade_count']
        
        # Metrics where lower is better
        minimize_metrics = ['max_drawdown']
        
        for col in df.columns:
            if col in maximize_metrics:
                # Higher is better - rank descending
                rankings[col] = df[col].rank(ascending=False, method='min')
            elif col in minimize_metrics:
                # Lower is better - rank ascending
                rankings[col] = df[col].rank(ascending=True, method='min')
        
        return rankings
    
    def _test_statistical_significance(
        self,
        results: List[Dict[str, Any]],
        metric: str
    ) -> Dict[str, Any]:
        """
        Test statistical significance between results.
        
        Args:
            results: List of results
            metric: Metric to test
        
        Returns:
            Statistical test results
        """
        # Extract metric values
        values = [r.get(metric, np.nan) for r in results]
        values = [v for v in values if not np.isnan(v)]
        
        if len(values) < 2:
            return {'error': 'Insufficient data for statistical tests'}
        
        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values, ddof=1)
        sem = stats.sem(values)
        
        # Confidence interval (95%)
        ci = stats.t.interval(
            0.95,
            len(values) - 1,
            loc=mean,
            scale=sem
        )
        
        # Test if significantly different from zero
        if std > 0:
            t_stat, p_value = stats.ttest_1samp(values, 0)
        else:
            t_stat, p_value = 0, 1.0
        
        return {
            'metric': metric,
            'n_samples': len(values),
            'mean': mean,
            'std': std,
            'sem': sem,
            'confidence_interval_95': ci,
            't_statistic': t_stat,
            'p_value': p_value,
            'significantly_different_from_zero': p_value < 0.05
        }
    
    def generate_comparison_report(
        self,
        comparison_result: ComparisonResult,
        include_charts: bool = False
    ) -> str:
        """
        Generate human-readable comparison report.
        
        Args:
            comparison_result: Comparison result
            include_charts: Whether to include chart recommendations
        
        Returns:
            Report string
        """
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("PERFORMANCE COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {comparison_result.timestamp.isoformat()}")
        report_lines.append(f"Compared Items: {len(comparison_result.compared_items)}")
        report_lines.append("")
        
        # Best result
        report_lines.append(f"BEST CONFIGURATION: {comparison_result.best_item}")
        report_lines.append("")
        
        # Rankings
        report_lines.append("RANKINGS (1 = Best):")
        report_lines.append("-" * 80)
        
        df = comparison_result.metrics_comparison
        rankings_df = pd.DataFrame(comparison_result.rankings)
        
        for i, row in df.iterrows():
            item_name = f"{row.get('strategy_type', 'Unknown')}:{row.get('symbol', 'default')}"
            report_lines.append(f"\n{i+1}. {item_name}")
            report_lines.append(f"   Sharpe: {row.get('sharpe_ratio', 0):.2f}")
            report_lines.append(f"   Max DD: {row.get('max_drawdown', 0):.1%}")
            report_lines.append(f"   Win Rate: {row.get('win_rate', 0):.1%}")
            report_lines.append(f"   Profit Factor: {row.get('profit_factor', 0):.2f}")
        
        report_lines.append("")
        
        # Statistical significance
        if comparison_result.statistical_significance:
            report_lines.append("\nSTATISTICAL ANALYSIS:")
            report_lines.append("-" * 80)
            
            sig = comparison_result.statistical_significance
            report_lines.append(f"Metric: {sig.get('metric', 'N/A')}")
            report_lines.append(f"Sample Size: {sig.get('n_samples', 0)}")
            report_lines.append(f"Mean: {sig.get('mean', 0):.4f}")
            report_lines.append(f"Std Dev: {sig.get('std', 0):.4f}")
            
            ci = sig.get('confidence_interval_95', (0, 0))
            report_lines.append(f"95% CI: [{ci[0]:.4f}, {ci[1]:.4f}]")
            
            p_val = sig.get('p_value', 1.0)
            report_lines.append(f"P-value: {p_val:.4f}")
            report_lines.append(f"Significantly > 0: {'Yes' if p_val < 0.05 else 'No'}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def get_best_by_metric(
        self,
        results: List[Dict[str, Any]],
        metric: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get best result by specific metric.
        
        Args:
            results: List of results
            metric: Metric to optimize
        
        Returns:
            Best result or None
        """
        if not results:
            return None
        
        # Determine if higher or lower is better
        maximize_metrics = ['sharpe_ratio', 'win_rate', 'profit_factor', 'total_return']
        
        if metric in maximize_metrics:
            best = max(results, key=lambda r: r.get(metric, -np.inf))
        else:
            best = min(results, key=lambda r: r.get(metric, np.inf))
        
        return best
    
    def filter_by_criteria(
        self,
        results: List[Dict[str, Any]],
        min_sharpe: float = 1.5,
        max_dd: float = 0.15,
        min_win_rate: float = 0.55,
        min_pf: float = 1.5,
        min_trades: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Filter results by success criteria.
        
        Args:
            results: List of results
            min_sharpe: Minimum Sharpe ratio
            max_dd: Maximum drawdown
            min_win_rate: Minimum win rate
            min_pf: Minimum profit factor
            min_trades: Minimum trade count
        
        Returns:
            Filtered results
        """
        filtered = []
        
        for result in results:
            if (result.get('sharpe_ratio', 0) >= min_sharpe and
                result.get('max_drawdown', 1) <= max_dd and
                result.get('win_rate', 0) >= min_win_rate and
                result.get('profit_factor', 0) >= min_pf and
                result.get('trade_count', 0) >= min_trades):
                filtered.append(result)
        
        self.logger.info(
            f"Filtered {len(results)} results: {len(filtered)} meet criteria "
            f"({len(filtered)/len(results)*100:.1f}%)"
        )
        
        return filtered

