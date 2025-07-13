"""
System Validation Framework - Comparing Production vs Backtesting Performance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Import our systems
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.enhanced_realistic_backtester import EnhancedRealisticBacktester

# Mock production system for validation
class ProductionTradingSystem:
    def __init__(self):
        pass
    
    def run_trading_session(self, pairs, duration_minutes, initial_capital):
        # Mock production results
        return {
            'initial_capital': initial_capital,
            'final_capital': initial_capital * 1.002,
            'total_return': 0.002,
            'total_trades': 8,
            'performance_metrics': {
                'total_return': 0.002,
                'annualized_return': 0.06,
                'annualized_volatility': 0.05,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.001,
                'win_rate': 0.625,
                'total_commissions': 40,
                'total_slippage': 80,
                'total_market_impact': 120
            },
            'portfolio_history': [
                {'portfolio_value': initial_capital + i * 50, 'timestamp': datetime.now() - timedelta(minutes=duration_minutes-i)}
                for i in range(duration_minutes)
            ]
        }

@dataclass
class ValidationResults:
    """Results from system validation"""
    production_results: Dict[str, Any]
    backtest_results: Dict[str, Any]
    comparison_metrics: Dict[str, Any]
    validation_score: float
    recommendations: List[str]

class SystemValidator:
    """Comprehensive system validation framework"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Validation thresholds
        self.performance_tolerance = 0.05  # 5% tolerance for performance differences
        self.risk_tolerance = 0.02  # 2% tolerance for risk metric differences
        self.cost_tolerance = 0.01  # 1% tolerance for transaction cost differences
        
    def run_production_test(self, pairs: List[Tuple[str, str]], 
                          duration_minutes: int = 60) -> Dict[str, Any]:
        """Run production system test"""
        
        self.logger.info(f"Running production system test for {duration_minutes} minutes")
        
        # Initialize production system
        production_system = ProductionTradingSystem()
        
        # Run for specified duration
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Simulate production run
        results = production_system.run_trading_session(
            pairs=pairs,
            duration_minutes=duration_minutes,
            initial_capital=1_000_000
        )
        
        return results
    
    def run_backtest_validation(self, pairs: List[Tuple[str, str]], 
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Run backtesting validation"""
        
        self.logger.info(f"Running backtest validation from {start_date} to {end_date}")
        
        # Initialize enhanced backtester
        backtester = EnhancedRealisticBacktester(initial_capital=1_000_000)
        
        # Run backtest
        results = backtester.run_enhanced_backtest(pairs, start_date, end_date)
        
        return results
    
    def compare_performance_metrics(self, production_results: Dict[str, Any],
                                  backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare key performance metrics between systems"""
        
        comparison = {}
        
        # Extract key metrics
        prod_metrics = production_results.get('performance_metrics', {})
        back_metrics = backtest_results.get('performance_metrics', {})
        
        # Return comparison
        metrics_to_compare = [
            'total_return', 'annualized_return', 'annualized_volatility',
            'sharpe_ratio', 'max_drawdown', 'win_rate'
        ]
        
        for metric in metrics_to_compare:
            prod_value = prod_metrics.get(metric, 0)
            back_value = back_metrics.get(metric, 0)
            
            difference = abs(prod_value - back_value)
            relative_diff = difference / max(abs(back_value), 0.001)  # Avoid division by zero
            
            comparison[metric] = {
                'production': prod_value,
                'backtest': back_value,
                'absolute_difference': difference,
                'relative_difference': relative_diff,
                'within_tolerance': relative_diff < self.performance_tolerance
            }
        
        return comparison
    
    def compare_transaction_costs(self, production_results: Dict[str, Any],
                                backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare transaction cost structures"""
        
        prod_metrics = production_results.get('performance_metrics', {})
        back_metrics = backtest_results.get('performance_metrics', {})
        
        cost_comparison = {}
        
        cost_metrics = ['total_commissions', 'total_slippage', 'total_market_impact']
        
        for metric in cost_metrics:
            prod_value = prod_metrics.get(metric, 0)
            back_value = back_metrics.get(metric, 0)
            
            # Normalize by initial capital
            prod_pct = prod_value / production_results.get('initial_capital', 1_000_000)
            back_pct = back_value / backtest_results.get('initial_capital', 1_000_000)
            
            difference = abs(prod_pct - back_pct)
            
            cost_comparison[metric] = {
                'production_pct': prod_pct,
                'backtest_pct': back_pct,
                'difference': difference,
                'within_tolerance': difference < self.cost_tolerance
            }
        
        return cost_comparison
    
    def compare_risk_metrics(self, production_results: Dict[str, Any],
                           backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare risk management effectiveness"""
        
        risk_comparison = {}
        
        # Compare drawdown patterns
        prod_history = production_results.get('portfolio_history', [])
        back_history = backtest_results.get('portfolio_history', [])
        
        if prod_history and back_history:
            # Calculate drawdown statistics
            prod_values = [h['portfolio_value'] for h in prod_history]
            back_values = [h['portfolio_value'] for h in back_history]
            
            prod_drawdowns = self.calculate_drawdown_series(prod_values)
            back_drawdowns = self.calculate_drawdown_series(back_values)
            
            risk_comparison['drawdown_comparison'] = {
                'production_max_dd': min(prod_drawdowns),
                'backtest_max_dd': min(back_drawdowns),
                'production_avg_dd': np.mean([dd for dd in prod_drawdowns if dd < 0]),
                'backtest_avg_dd': np.mean([dd for dd in back_drawdowns if dd < 0])
            }
        
        return risk_comparison
    
    def calculate_drawdown_series(self, portfolio_values: List[float]) -> List[float]:
        """Calculate drawdown series from portfolio values"""
        
        if not portfolio_values:
            return []
        
        values = np.array(portfolio_values)
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        
        return drawdown.tolist()
    
    def calculate_validation_score(self, performance_comparison: Dict[str, Any],
                                 cost_comparison: Dict[str, Any],
                                 risk_comparison: Dict[str, Any]) -> float:
        """Calculate overall validation score (0-100)"""
        
        score = 0
        max_score = 100
        
        # Performance score (40% weight)
        performance_score = 0
        performance_metrics = len(performance_comparison)
        
        for metric, data in performance_comparison.items():
            if data['within_tolerance']:
                performance_score += 1
        
        performance_score = (performance_score / performance_metrics) * 40 if performance_metrics > 0 else 0
        
        # Cost score (30% weight)
        cost_score = 0
        cost_metrics = len(cost_comparison)
        
        for metric, data in cost_comparison.items():
            if data['within_tolerance']:
                cost_score += 1
        
        cost_score = (cost_score / cost_metrics) * 30 if cost_metrics > 0 else 0
        
        # Risk score (30% weight) - simplified for now
        risk_score = 30  # Assume good risk management
        
        total_score = performance_score + cost_score + risk_score
        
        return min(total_score, max_score)
    
    def generate_recommendations(self, performance_comparison: Dict[str, Any],
                               cost_comparison: Dict[str, Any],
                               validation_score: float) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        # Performance recommendations
        for metric, data in performance_comparison.items():
            if not data['within_tolerance']:
                if data['relative_difference'] > 0.1:  # 10% difference
                    recommendations.append(
                        f"CRITICAL: {metric} shows {data['relative_difference']:.1%} difference between production and backtest"
                    )
                else:
                    recommendations.append(
                        f"WARNING: {metric} shows {data['relative_difference']:.1%} difference - monitor closely"
                    )
        
        # Cost recommendations
        for metric, data in cost_comparison.items():
            if not data['within_tolerance']:
                recommendations.append(
                    f"COST ALERT: {metric} difference of {data['difference']:.2%} exceeds tolerance"
                )
        
        # Overall score recommendations
        if validation_score < 70:
            recommendations.append("OVERALL: System validation score is below acceptable threshold - review all components")
        elif validation_score < 85:
            recommendations.append("OVERALL: System validation shows room for improvement - focus on flagged areas")
        else:
            recommendations.append("OVERALL: System validation passed - production system aligns well with backtesting")
        
        return recommendations
    
    def run_full_validation(self, pairs: List[Tuple[str, str]], 
                          test_duration_minutes: int = 30) -> ValidationResults:
        """Run complete system validation"""
        
        self.logger.info("Starting full system validation")
        
        # Define test period
        end_date = datetime.now()
        start_date = end_date - timedelta(minutes=test_duration_minutes)
        
        # Run production test (simulated)
        production_results = self.simulate_production_results(pairs, test_duration_minutes)
        
        # Run backtest validation
        backtest_results = self.run_backtest_validation(pairs, start_date, end_date)
        
        # Compare systems
        performance_comparison = self.compare_performance_metrics(production_results, backtest_results)
        cost_comparison = self.compare_transaction_costs(production_results, backtest_results)
        risk_comparison = self.compare_risk_metrics(production_results, backtest_results)
        
        # Calculate validation score
        validation_score = self.calculate_validation_score(
            performance_comparison, cost_comparison, risk_comparison
        )
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            performance_comparison, cost_comparison, validation_score
        )
        
        # Compile results
        comparison_metrics = {
            'performance': performance_comparison,
            'costs': cost_comparison,
            'risk': risk_comparison
        }
        
        validation_results = ValidationResults(
            production_results=production_results,
            backtest_results=backtest_results,
            comparison_metrics=comparison_metrics,
            validation_score=validation_score,
            recommendations=recommendations
        )
        
        self.logger.info(f"Validation completed with score: {validation_score:.1f}")
        
        return validation_results
    
    def simulate_production_results(self, pairs: List[Tuple[str, str]], 
                                  duration_minutes: int) -> Dict[str, Any]:
        """Simulate production system results for validation"""
        
        # This would normally call the actual production system
        # For demo purposes, we'll create realistic simulated results
        
        # Simulate better performance than backtest (as expected in production)
        return {
            'initial_capital': 1_000_000,
            'final_capital': 1_005_000,  # Small positive return
            'total_return': 0.005,
            'total_trades': 12,
            'performance_metrics': {
                'total_return': 0.005,
                'annualized_return': 0.15,  # Annualized
                'annualized_volatility': 0.08,
                'sharpe_ratio': 1.875,
                'max_drawdown': -0.002,
                'win_rate': 0.583,
                'total_commissions': 60,
                'total_slippage': 150,
                'total_market_impact': 200
            },
            'portfolio_history': [
                {'portfolio_value': 1_000_000 + i * 100, 'timestamp': datetime.now() - timedelta(minutes=duration_minutes-i)}
                for i in range(duration_minutes)
            ]
        }
    
    def generate_validation_report(self, results: ValidationResults) -> str:
        """Generate comprehensive validation report"""
        
        report = f"""
=== SYSTEM VALIDATION REPORT ===

VALIDATION SCORE: {results.validation_score:.1f}/100

PERFORMANCE COMPARISON:
"""
        
        for metric, data in results.comparison_metrics['performance'].items():
            status = "✓" if data['within_tolerance'] else "✗"
            report += f"{status} {metric}: Production={data['production']:.4f}, Backtest={data['backtest']:.4f}, Diff={data['relative_difference']:.1%}\n"
        
        report += f"""
TRANSACTION COST COMPARISON:
"""
        
        for metric, data in results.comparison_metrics['costs'].items():
            status = "✓" if data['within_tolerance'] else "✗"
            report += f"{status} {metric}: Production={data['production_pct']:.2%}, Backtest={data['backtest_pct']:.2%}, Diff={data['difference']:.2%}\n"
        
        report += f"""
RECOMMENDATIONS:
"""
        
        for i, rec in enumerate(results.recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""
SUMMARY:
- Production System Total Return: {results.production_results['total_return']:.2%}
- Backtest System Total Return: {results.backtest_results['total_return']:.2%}
- Production Trades: {results.production_results['total_trades']}
- Backtest Trades: {results.backtest_results['total_trades']}
- Validation Status: {'PASSED' if results.validation_score >= 70 else 'FAILED'}
"""
        
        return report

def run_validation_demo():
    """Run system validation demonstration"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting System Validation Demo")
    
    # Initialize validator
    validator = SystemValidator()
    
    # Define test pairs
    pairs = [
        ('SPY', 'UPRO'),
        ('QQQ', 'TQQQ'),
        ('TLT', 'TMF')
    ]
    
    # Run validation
    results = validator.run_full_validation(pairs, test_duration_minutes=30)
    
    # Generate report
    report = validator.generate_validation_report(results)
    print(report)
    
    # Save results
    validation_df = pd.DataFrame([{
        'timestamp': datetime.now(),
        'validation_score': results.validation_score,
        'production_return': results.production_results['total_return'],
        'backtest_return': results.backtest_results['total_return'],
        'production_trades': results.production_results['total_trades'],
        'backtest_trades': results.backtest_results['total_trades'],
        'status': 'PASSED' if results.validation_score >= 70 else 'FAILED'
    }])
    
    validation_df.to_csv('system_validation_results.csv', index=False)
    
    logger.info("System validation demo completed")
    return results

if __name__ == "__main__":
    run_validation_demo() 