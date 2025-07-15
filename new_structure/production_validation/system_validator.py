"""
Advanced System Validation Framework for StatArb Gemini
====================================================

Comprehensive validation framework that compares production vs backtesting performance,
validates system integrity, and provides recommendations for improvement.

Features:
- Production vs Backtest comparison
- Real-time validation monitoring
- Performance degradation detection
- Cost structure validation
- Risk metric comparison
- Automated recommendations
- Integration with new system architecture
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import asyncio
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
import json
from pathlib import Path

# Import new structure components
from ...benchmarks.backtesting.engine import BacktestEngine, BacktestConfig
from ...analytics.performance_analytics import PerformanceAnalytics
from ...infrastructure.config.base_config import BaseConfig
from ...market_data.data_manager import MarketDataManager
from ...risk_management.risk_manager import RiskManager
from ...portfolio_management.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)

@dataclass
class ValidationConfig(BaseConfig):
    """Configuration for system validation."""
    
    # Tolerance thresholds
    performance_tolerance: float = 0.05  # 5% tolerance for performance differences
    risk_tolerance: float = 0.02  # 2% tolerance for risk metric differences
    cost_tolerance: float = 0.01  # 1% tolerance for transaction cost differences
    correlation_threshold: float = 0.8  # Minimum correlation between prod and backtest
    
    # Validation parameters
    test_duration_minutes: int = 60
    min_trades_required: int = 5
    max_drawdown_tolerance: float = 0.02  # 2% max acceptable drawdown difference
    
    # Scoring weights
    performance_weight: float = 0.4
    cost_weight: float = 0.3
    risk_weight: float = 0.3
    
    # Reporting
    min_passing_score: float = 70.0
    warning_score: float = 85.0
    save_detailed_results: bool = True
    
    # Real-time monitoring
    enable_continuous_monitoring: bool = True
    monitoring_frequency_seconds: int = 300  # 5 minutes
    alert_threshold_score: float = 60.0

@dataclass
class ValidationResults:
    """Results from system validation."""
    
    # Basic info
    timestamp: datetime
    validation_score: float
    status: str  # PASSED, WARNING, FAILED
    
    # System results
    production_results: Dict[str, Any]
    backtest_results: Dict[str, Any]
    
    # Comparisons
    performance_comparison: Dict[str, Any] = field(default_factory=dict)
    cost_comparison: Dict[str, Any] = field(default_factory=dict)
    risk_comparison: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis
    recommendations: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Additional metrics
    correlation_analysis: Dict[str, float] = field(default_factory=dict)
    degradation_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'validation_score': self.validation_score,
            'status': self.status,
            'production_results': self.production_results,
            'backtest_results': self.backtest_results,
            'performance_comparison': self.performance_comparison,
            'cost_comparison': self.cost_comparison,
            'risk_comparison': self.risk_comparison,
            'recommendations': self.recommendations,
            'issues': self.issues,
            'warnings': self.warnings,
            'correlation_analysis': self.correlation_analysis,
            'degradation_metrics': self.degradation_metrics
        }

class ProductionSystemInterface:
    """Interface for production system interaction."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # In real implementation, this would connect to actual production system
        
    async def get_production_metrics(self, 
                                   start_time: datetime,
                                   end_time: datetime) -> Dict[str, Any]:
        """Get production system metrics for specified period."""
        
        # Mock production data - replace with actual production system interface
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        # Simulate realistic production metrics
        base_return = np.random.normal(0.001, 0.002)  # Small positive bias
        volatility = np.random.uniform(0.05, 0.15)
        
        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': duration_minutes,
            'total_return': base_return,
            'annualized_return': base_return * (252 * 24 * 60 / duration_minutes),
            'volatility': volatility,
            'sharpe_ratio': base_return / volatility if volatility > 0 else 0,
            'max_drawdown': -abs(np.random.normal(0.001, 0.001)),
            'total_trades': max(1, int(duration_minutes / 10 + np.random.poisson(2))),
            'win_rate': np.random.uniform(0.5, 0.7),
            'transaction_costs': {
                'commissions': np.random.uniform(0.0005, 0.002),
                'slippage': np.random.uniform(0.0003, 0.001),
                'market_impact': np.random.uniform(0.0001, 0.0005)
            },
            'portfolio_values': self._generate_portfolio_timeline(start_time, end_time, base_return),
            'risk_metrics': {
                'var_95': np.random.uniform(-0.02, -0.005),
                'expected_shortfall': np.random.uniform(-0.03, -0.01),
                'beta': np.random.uniform(0.8, 1.2)
            }
        }
    
    def _generate_portfolio_timeline(self, start_time: datetime, end_time: datetime, 
                                   base_return: float) -> List[Dict[str, Any]]:
        """Generate realistic portfolio value timeline."""
        
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        initial_value = 1_000_000
        
        timeline = []
        current_value = initial_value
        
        for i in range(duration_minutes + 1):
            timestamp = start_time + timedelta(minutes=i)
            
            # Add some random walk
            change = np.random.normal(base_return / duration_minutes, 0.001)
            current_value *= (1 + change)
            
            timeline.append({
                'timestamp': timestamp,
                'portfolio_value': current_value,
                'return': (current_value - initial_value) / initial_value
            })
        
        return timeline

class SystemValidator:
    """Advanced system validation framework for StatArb Gemini."""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the system validator.
        
        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.production_interface = ProductionSystemInterface()
        self.backtest_engine = BacktestEngine(BacktestConfig())
        self.performance_analytics = PerformanceAnalytics()
        self.data_manager = MarketDataManager()
        
        # State tracking
        self.validation_history = []
        self.continuous_monitoring = False
        
        # Results storage
        self.results_path = Path("validation_results")
        self.results_path.mkdir(exist_ok=True)
        
        self.logger.info("SystemValidator initialized")
    
    async def run_full_validation(self, 
                                symbols: List[str],
                                test_duration_minutes: Optional[int] = None) -> ValidationResults:
        """
        Run comprehensive system validation.
        
        Args:
            symbols: List of symbols to test
            test_duration_minutes: Duration of test period
            
        Returns:
            ValidationResults object
        """
        test_duration = test_duration_minutes or self.config.test_duration_minutes
        
        self.logger.info(f"Starting full system validation for {len(symbols)} symbols")
        self.logger.info(f"Test duration: {test_duration} minutes")
        
        try:
            # Define test period
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=test_duration)
            
            # Run production and backtest systems in parallel
            production_task = self._run_production_test(start_time, end_time, symbols)
            backtest_task = self._run_backtest_validation(start_time, end_time, symbols)
            
            production_results, backtest_results = await asyncio.gather(
                production_task, backtest_task
            )
            
            # Perform comparisons
            performance_comparison = await self._compare_performance_metrics(
                production_results, backtest_results
            )
            
            cost_comparison = await self._compare_transaction_costs(
                production_results, backtest_results
            )
            
            risk_comparison = await self._compare_risk_metrics(
                production_results, backtest_results
            )
            
            # Analyze correlations
            correlation_analysis = await self._analyze_correlations(
                production_results, backtest_results
            )
            
            # Detect performance degradation
            degradation_metrics = await self._detect_degradation(
                production_results, backtest_results
            )
            
            # Calculate validation score
            validation_score = self._calculate_validation_score(
                performance_comparison, cost_comparison, risk_comparison, correlation_analysis
            )
            
            # Generate recommendations
            recommendations, issues, warnings = self._generate_recommendations(
                performance_comparison, cost_comparison, risk_comparison, 
                correlation_analysis, validation_score
            )
            
            # Determine status
            status = self._determine_status(validation_score)
            
            # Create results object
            results = ValidationResults(
                timestamp=datetime.now(),
                validation_score=validation_score,
                status=status,
                production_results=production_results,
                backtest_results=backtest_results,
                performance_comparison=performance_comparison,
                cost_comparison=cost_comparison,
                risk_comparison=risk_comparison,
                recommendations=recommendations,
                issues=issues,
                warnings=warnings,
                correlation_analysis=correlation_analysis,
                degradation_metrics=degradation_metrics
            )
            
            # Store results
            await self._store_results(results)
            
            # Add to history
            self.validation_history.append(results)
            
            self.logger.info(f"Validation completed with score: {validation_score:.1f} ({status})")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            raise
    
    async def _run_production_test(self, start_time: datetime, end_time: datetime,
                                 symbols: List[str]) -> Dict[str, Any]:
        """Run production system test."""
        
        self.logger.info("Running production system test")
        
        # Get production metrics
        production_results = await self.production_interface.get_production_metrics(
            start_time, end_time
        )
        
        # Add symbol information
        production_results['symbols'] = symbols
        production_results['symbol_count'] = len(symbols)
        
        return production_results
    
    async def _run_backtest_validation(self, start_time: datetime, end_time: datetime,
                                     symbols: List[str]) -> Dict[str, Any]:
        """Run backtest validation."""
        
        self.logger.info("Running backtest validation")
        
        # Configure backtest
        backtest_config = BacktestConfig(
            symbols=symbols,
            start_date=start_time,
            end_date=end_time
        )
        
        # Update backtest engine config
        self.backtest_engine.config = backtest_config
        
        # Load data for backtesting
        data = await self.data_manager.get_historical_data(
            symbols=symbols,
            start_date=start_time,
            end_date=end_time,
            frequency='1min'
        )
        
        # Run backtest
        backtest_result = await self.backtest_engine.run_backtest(data)
        
        # Convert to comparable format
        return {
            'start_time': start_time,
            'end_time': end_time,
            'symbols': symbols,
            'symbol_count': len(symbols),
            'total_return': backtest_result.total_return,
            'annualized_return': backtest_result.annualized_return,
            'volatility': np.std(backtest_result.returns) * np.sqrt(252) if len(backtest_result.returns) > 0 else 0,
            'sharpe_ratio': backtest_result.sharpe_ratio,
            'max_drawdown': backtest_result.max_drawdown,
            'total_trades': backtest_result.total_trades,
            'win_rate': backtest_result.win_rate,
            'transaction_costs': {
                'commissions': backtest_result.config.commission_rate,
                'slippage': backtest_result.config.slippage_rate,
                'market_impact': 0.0  # Would be calculated from execution engine
            },
            'portfolio_values': [
                {'timestamp': backtest_result.start_date + timedelta(days=i), 
                 'portfolio_value': val}
                for i, val in enumerate(backtest_result.portfolio_values)
            ],
            'risk_metrics': {
                'var_95': backtest_result.var_95,
                'expected_shortfall': backtest_result.cvar_95,
                'beta': backtest_result.beta
            }
        }
    
    async def _compare_performance_metrics(self, production_results: Dict[str, Any],
                                         backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance metrics between systems."""
        
        comparison = {}
        
        metrics_to_compare = [
            'total_return', 'annualized_return', 'volatility',
            'sharpe_ratio', 'max_drawdown', 'win_rate'
        ]
        
        for metric in metrics_to_compare:
            prod_value = production_results.get(metric, 0)
            back_value = backtest_results.get(metric, 0)
            
            # Handle negative values appropriately
            if metric == 'max_drawdown':
                difference = abs(abs(prod_value) - abs(back_value))
                relative_diff = difference / max(abs(back_value), 0.001)
            else:
                difference = abs(prod_value - back_value)
                relative_diff = difference / max(abs(back_value), 0.001)
            
            comparison[metric] = {
                'production': prod_value,
                'backtest': back_value,
                'absolute_difference': difference,
                'relative_difference': relative_diff,
                'within_tolerance': relative_diff < self.config.performance_tolerance,
                'grade': self._grade_metric_difference(relative_diff, self.config.performance_tolerance)
            }
        
        return comparison
    
    async def _compare_transaction_costs(self, production_results: Dict[str, Any],
                                       backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare transaction cost structures."""
        
        prod_costs = production_results.get('transaction_costs', {})
        back_costs = backtest_results.get('transaction_costs', {})
        
        cost_comparison = {}
        cost_metrics = ['commissions', 'slippage', 'market_impact']
        
        for metric in cost_metrics:
            prod_value = prod_costs.get(metric, 0)
            back_value = back_costs.get(metric, 0)
            
            difference = abs(prod_value - back_value)
            
            cost_comparison[metric] = {
                'production': prod_value,
                'backtest': back_value,
                'difference': difference,
                'within_tolerance': difference < self.config.cost_tolerance,
                'grade': self._grade_metric_difference(difference, self.config.cost_tolerance)
            }
        
        return cost_comparison
    
    async def _compare_risk_metrics(self, production_results: Dict[str, Any],
                                  backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare risk management effectiveness."""
        
        prod_risk = production_results.get('risk_metrics', {})
        back_risk = backtest_results.get('risk_metrics', {})
        
        risk_comparison = {}
        risk_metrics = ['var_95', 'expected_shortfall', 'beta']
        
        for metric in risk_metrics:
            prod_value = prod_risk.get(metric, 0)
            back_value = back_risk.get(metric, 0)
            
            difference = abs(prod_value - back_value)
            relative_diff = difference / max(abs(back_value), 0.001)
            
            risk_comparison[metric] = {
                'production': prod_value,
                'backtest': back_value,
                'difference': difference,
                'relative_difference': relative_diff,
                'within_tolerance': relative_diff < self.config.risk_tolerance,
                'grade': self._grade_metric_difference(relative_diff, self.config.risk_tolerance)
            }
        
        return risk_comparison
    
    async def _analyze_correlations(self, production_results: Dict[str, Any],
                                  backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """Analyze correlations between production and backtest returns."""
        
        correlation_analysis = {}
        
        try:
            # Extract portfolio value series
            prod_timeline = production_results.get('portfolio_values', [])
            back_timeline = backtest_results.get('portfolio_values', [])
            
            if len(prod_timeline) > 1 and len(back_timeline) > 1:
                # Calculate returns
                prod_returns = [
                    (prod_timeline[i]['portfolio_value'] - prod_timeline[i-1]['portfolio_value']) / 
                    prod_timeline[i-1]['portfolio_value']
                    for i in range(1, len(prod_timeline))
                ]
                
                back_returns = [
                    (back_timeline[i]['portfolio_value'] - back_timeline[i-1]['portfolio_value']) / 
                    back_timeline[i-1]['portfolio_value']
                    for i in range(1, len(back_timeline))
                ]
                
                # Align series length
                min_length = min(len(prod_returns), len(back_returns))
                if min_length > 0:
                    prod_returns = prod_returns[:min_length]
                    back_returns = back_returns[:min_length]
                    
                    # Calculate correlation
                    correlation = np.corrcoef(prod_returns, back_returns)[0, 1]
                    
                    correlation_analysis = {
                        'return_correlation': correlation if not np.isnan(correlation) else 0.0,
                        'correlation_quality': 'HIGH' if correlation > 0.8 else 'MEDIUM' if correlation > 0.5 else 'LOW',
                        'data_points': min_length
                    }
                    
        except Exception as e:
            self.logger.warning(f"Correlation analysis failed: {e}")
            correlation_analysis = {
                'return_correlation': 0.0,
                'correlation_quality': 'UNKNOWN',
                'data_points': 0
            }
        
        return correlation_analysis
    
    async def _detect_degradation(self, production_results: Dict[str, Any],
                                backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Detect performance degradation patterns."""
        
        degradation_metrics = {}
        
        # Compare with historical validation results
        if len(self.validation_history) > 0:
            recent_scores = [r.validation_score for r in self.validation_history[-5:]]
            
            if len(recent_scores) > 1:
                trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                degradation_metrics['score_trend'] = trend
                degradation_metrics['degradation_detected'] = trend < -2.0  # Declining > 2 points
        
        # Performance consistency check
        prod_return = production_results.get('total_return', 0)
        back_return = backtest_results.get('total_return', 0)
        
        degradation_metrics['return_gap'] = prod_return - back_return
        degradation_metrics['concerning_gap'] = abs(degradation_metrics['return_gap']) > 0.01
        
        return degradation_metrics
    
    def _calculate_validation_score(self, performance_comparison: Dict[str, Any],
                                  cost_comparison: Dict[str, Any],
                                  risk_comparison: Dict[str, Any],
                                  correlation_analysis: Dict[str, float]) -> float:
        """Calculate overall validation score."""
        
        # Performance score
        perf_scores = [
            100 if data['within_tolerance'] else max(0, 100 - data['relative_difference'] * 200)
            for data in performance_comparison.values()
        ]
        performance_score = np.mean(perf_scores) if perf_scores else 0
        
        # Cost score
        cost_scores = [
            100 if data['within_tolerance'] else max(0, 100 - data['difference'] * 5000)
            for data in cost_comparison.values()
        ]
        cost_score = np.mean(cost_scores) if cost_scores else 0
        
        # Risk score
        risk_scores = [
            100 if data['within_tolerance'] else max(0, 100 - data['relative_difference'] * 500)
            for data in risk_comparison.values()
        ]
        risk_score = np.mean(risk_scores) if risk_scores else 0
        
        # Correlation bonus/penalty
        correlation = correlation_analysis.get('return_correlation', 0)
        correlation_bonus = max(0, (correlation - 0.5) * 40)  # Up to 20 point bonus
        
        # Weighted total
        total_score = (
            performance_score * self.config.performance_weight +
            cost_score * self.config.cost_weight +
            risk_score * self.config.risk_weight
        ) + correlation_bonus
        
        return min(100, max(0, total_score))
    
    def _generate_recommendations(self, performance_comparison: Dict[str, Any],
                                cost_comparison: Dict[str, Any],
                                risk_comparison: Dict[str, Any],
                                correlation_analysis: Dict[str, float],
                                validation_score: float) -> Tuple[List[str], List[str], List[str]]:
        """Generate recommendations, issues, and warnings."""
        
        recommendations = []
        issues = []
        warnings = []
        
        # Performance analysis
        for metric, data in performance_comparison.items():
            if not data['within_tolerance']:
                severity = data['relative_difference']
                if severity > 0.2:  # > 20% difference
                    issues.append(f"CRITICAL: {metric} differs by {severity:.1%} between systems")
                    recommendations.append(f"Immediate investigation required for {metric} discrepancy")
                elif severity > 0.1:  # > 10% difference
                    warnings.append(f"WARNING: {metric} differs by {severity:.1%}")
                    recommendations.append(f"Monitor {metric} closely and investigate causes")
        
        # Cost analysis
        for metric, data in cost_comparison.items():
            if not data['within_tolerance']:
                if data['difference'] > 0.005:  # > 0.5% difference
                    issues.append(f"COST ISSUE: {metric} difference of {data['difference']:.2%}")
                    recommendations.append(f"Review {metric} implementation in production system")
                else:
                    warnings.append(f"Cost difference in {metric}: {data['difference']:.2%}")
        
        # Correlation analysis
        correlation = correlation_analysis.get('return_correlation', 0)
        if correlation < self.config.correlation_threshold:
            if correlation < 0.3:
                issues.append(f"CRITICAL: Very low correlation ({correlation:.2f}) between systems")
                recommendations.append("Fundamental review of system alignment required")
            else:
                warnings.append(f"Low correlation ({correlation:.2f}) between systems")
                recommendations.append("Investigate sources of return divergence")
        
        # Overall score assessment
        if validation_score < self.config.min_passing_score:
            issues.append(f"OVERALL: Validation score ({validation_score:.1f}) below threshold")
            recommendations.append("Comprehensive system review and recalibration required")
        elif validation_score < self.config.warning_score:
            warnings.append(f"Overall validation score ({validation_score:.1f}) needs improvement")
            recommendations.append("Focus on identified issues to improve system alignment")
        else:
            recommendations.append("System validation passed - continue monitoring")
        
        return recommendations, issues, warnings
    
    def _determine_status(self, validation_score: float) -> str:
        """Determine validation status based on score."""
        if validation_score >= self.config.warning_score:
            return "PASSED"
        elif validation_score >= self.config.min_passing_score:
            return "WARNING"
        else:
            return "FAILED"
    
    def _grade_metric_difference(self, difference: float, tolerance: float) -> str:
        """Grade metric difference quality."""
        if difference <= tolerance:
            return "A"
        elif difference <= tolerance * 2:
            return "B"
        elif difference <= tolerance * 3:
            return "C"
        else:
            return "F"
    
    async def _store_results(self, results: ValidationResults):
        """Store validation results."""
        if self.config.save_detailed_results:
            filename = f"validation_{results.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.results_path / filename
            
            with open(filepath, 'w') as f:
                json.dump(results.to_dict(), f, indent=2, default=str)
            
            self.logger.info(f"Validation results saved to {filepath}")
    
    def generate_report(self, results: ValidationResults) -> str:
        """Generate comprehensive validation report."""
        
        report = []
        report.append("=" * 80)
        report.append("STATARB GEMINI SYSTEM VALIDATION REPORT")
        report.append("=" * 80)
        
        # Header
        report.append(f"\nTimestamp: {results.timestamp}")
        report.append(f"Validation Score: {results.validation_score:.1f}/100")
        report.append(f"Status: {results.status}")
        
        # Performance comparison
        report.append(f"\nPERFORMANCE COMPARISON:")
        for metric, data in results.performance_comparison.items():
            status = "✓" if data['within_tolerance'] else "✗"
            grade = data['grade']
            report.append(f"  {status} {metric} ({grade}): "
                         f"Prod={data['production']:.4f}, Back={data['backtest']:.4f}, "
                         f"Diff={data['relative_difference']:.1%}")
        
        # Cost comparison
        report.append(f"\nTRANSACTION COST COMPARISON:")
        for metric, data in results.cost_comparison.items():
            status = "✓" if data['within_tolerance'] else "✗"
            grade = data['grade']
            report.append(f"  {status} {metric} ({grade}): "
                         f"Prod={data['production']:.4f}, Back={data['backtest']:.4f}, "
                         f"Diff={data['difference']:.4f}")
        
        # Risk comparison
        report.append(f"\nRISK METRICS COMPARISON:")
        for metric, data in results.risk_comparison.items():
            status = "✓" if data['within_tolerance'] else "✗"
            grade = data['grade']
            report.append(f"  {status} {metric} ({grade}): "
                         f"Prod={data['production']:.4f}, Back={data['backtest']:.4f}, "
                         f"Diff={data['relative_difference']:.1%}")
        
        # Correlation analysis
        report.append(f"\nCORRELATION ANALYSIS:")
        correlation = results.correlation_analysis.get('return_correlation', 0)
        quality = results.correlation_analysis.get('correlation_quality', 'UNKNOWN')
        report.append(f"  Return Correlation: {correlation:.3f} ({quality})")
        
        # Issues and warnings
        if results.issues:
            report.append(f"\nISSUES:")
            for issue in results.issues:
                report.append(f"  🚨 {issue}")
        
        if results.warnings:
            report.append(f"\nWARNINGS:")
            for warning in results.warnings:
                report.append(f"  ⚠️  {warning}")
        
        # Recommendations
        report.append(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(results.recommendations, 1):
            report.append(f"  {i}. {rec}")
        
        # Summary
        report.append(f"\nSUMMARY:")
        prod_return = results.production_results.get('total_return', 0)
        back_return = results.backtest_results.get('total_return', 0)
        prod_trades = results.production_results.get('total_trades', 0)
        back_trades = results.backtest_results.get('total_trades', 0)
        
        report.append(f"  Production Return: {prod_return:.4f}")
        report.append(f"  Backtest Return: {back_return:.4f}")
        report.append(f"  Production Trades: {prod_trades}")
        report.append(f"  Backtest Trades: {back_trades}")
        report.append(f"  Final Status: {results.status}")
        
        return "\n".join(report)
    
    async def start_continuous_monitoring(self, symbols: List[str]):
        """Start continuous validation monitoring."""
        
        if self.continuous_monitoring:
            self.logger.warning("Continuous monitoring already running")
            return
        
        self.continuous_monitoring = True
        self.logger.info("Starting continuous validation monitoring")
        
        while self.continuous_monitoring:
            try:
                # Run validation
                results = await self.run_full_validation(
                    symbols, test_duration_minutes=30
                )
                
                # Check for alerts
                if results.validation_score < self.config.alert_threshold_score:
                    self.logger.error(f"VALIDATION ALERT: Score {results.validation_score:.1f} below threshold")
                    # In production, this would trigger alerts/notifications
                
                # Wait for next check
                await asyncio.sleep(self.config.monitoring_frequency_seconds)
                
            except Exception as e:
                self.logger.error(f"Continuous monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def stop_continuous_monitoring(self):
        """Stop continuous validation monitoring."""
        self.continuous_monitoring = False
        self.logger.info("Stopped continuous validation monitoring")
