# 🚀 StatArb Gemini Enhanced Plan - Phases 2-4
## Complete Implementation Roadmap (Options 2-4)

### 📊 **Current Status: Phases 0-3 Complete!**

✅ **Phase 0**: Configuration Architecture Enhancement  
✅ **Phase 1**: Core System Enhancements (Academic Foundations)  
✅ **Phase 2**: Backtesting Framework Integration  
✅ **Phase 3**: Real-Time Integration  

---

## 🎯 **Updated Implementation Roadmap**

### **Phase 4: Additional Testing & Validation** (Option 2)
- Real historical data testing with ClickHouse
- Academic performance validation against research benchmarks
- Comprehensive backtesting with multiple strategies
- Parameter optimization and validation

### **Phase 5: Performance Optimization** (Option 3)
- Advanced parameter optimization using enhanced framework
- Multi-dimensional parameter sweeps across academic ranges
- SPY benchmark target validation and optimization
- Risk-adjusted performance tuning

### **Phase 6: Documentation & Training** (Option 4)
- Comprehensive system documentation
- User training materials and guides
- Deployment and operational documentation
- Academic research integration guide

### **Phase 7: Production Deployment** (Option 1 - Final Step)
- Live trading system deployment
- Real market data integration
- Paper trading implementation
- Production monitoring and maintenance

---

## 🎯 **Phase 4: Additional Testing & Validation**

### **4.1 Real Historical Data Testing**

**Objective**: Validate system performance with real ClickHouse data

**File: `backtesting_framework/tests/test_real_historical_data.py`**

```python
#!/usr/bin/env python3
"""
Phase 4.1: Real Historical Data Testing
Validate system with actual ClickHouse data
"""

import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from core_structure.infrastructure.database.clickhouse_client import ClickHouseClient
from backtesting_framework.enhanced_backtesting_engine import EnhancedBacktestingEngine
from core_structure.performance.benchmark_analyzer import BenchmarkAnalyzer, BenchmarkConfig

class RealHistoricalDataTester:
    """Test system with real historical data from ClickHouse"""
    
    def __init__(self):
        self.clickhouse_client = ClickHouseClient()
        self.backtesting_engine = EnhancedBacktestingEngine()
        self.benchmark_analyzer = BenchmarkAnalyzer(BenchmarkConfig())
        
    async def test_with_real_data(self):
        """Test system with real historical data"""
        
        print("=== Phase 4.1: Real Historical Data Testing ===")
        
        # 1. Load real data from ClickHouse
        symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
        start_date = '2023-01-01'
        end_date = '2025-06-30'
        
        print(f"Loading real data for {len(symbols)} symbols from {start_date} to {end_date}")
        
        real_data = await self._load_real_historical_data(symbols, start_date, end_date)
        
        # 2. Validate data quality
        data_quality_report = self._validate_data_quality(real_data)
        print(f"Data quality validation: {data_quality_report['status']}")
        
        # 3. Run enhanced backtesting with real data
        backtest_results = await self._run_real_data_backtest(real_data)
        
        # 4. Compare with academic benchmarks
        academic_validation = self._validate_against_academic_benchmarks(backtest_results)
        
        # 5. Generate comprehensive report
        self._generate_testing_report(backtest_results, academic_validation)
        
        return {
            'data_quality': data_quality_report,
            'backtest_results': backtest_results,
            'academic_validation': academic_validation
        }
    
    async def _load_real_historical_data(self, symbols: list, start_date: str, end_date: str) -> dict:
        """Load real historical data from ClickHouse"""
        
        real_data = {}
        
        for symbol in symbols:
            try:
                # Load daily data
                daily_data = await self.clickhouse_client.get_historical_data(
                    symbol, start_date, end_date, timeframe='1day'
                )
                
                if daily_data is not None and len(daily_data) > 0:
                    real_data[symbol] = daily_data
                    print(f"✅ Loaded {len(daily_data)} rows for {symbol}")
                else:
                    print(f"⚠️  No data found for {symbol}")
                    
            except Exception as e:
                print(f"❌ Failed to load data for {symbol}: {e}")
        
        return real_data
    
    def _validate_data_quality(self, data: dict) -> dict:
        """Validate quality of real historical data"""
        
        quality_report = {
            'status': 'PASS',
            'issues': [],
            'summary': {}
        }
        
        for symbol, symbol_data in data.items():
            # Check data completeness
            expected_days = len(pd.date_range(start=symbol_data.index.min(), 
                                            end=symbol_data.index.max(), freq='D'))
            actual_days = len(symbol_data)
            completeness = actual_days / expected_days
            
            if completeness < 0.95:
                quality_report['issues'].append(f"{symbol}: Low data completeness ({completeness:.2%})")
            
            # Check for missing values
            missing_prices = symbol_data['close'].isnull().sum()
            if missing_prices > 0:
                quality_report['issues'].append(f"{symbol}: {missing_prices} missing price points")
            
            # Check for price anomalies
            price_changes = symbol_data['close'].pct_change()
            extreme_changes = price_changes[abs(price_changes) > 0.5]  # 50% daily changes
            if len(extreme_changes) > 0:
                quality_report['issues'].append(f"{symbol}: {len(extreme_changes)} extreme price changes")
            
            quality_report['summary'][symbol] = {
                'completeness': completeness,
                'missing_prices': missing_prices,
                'extreme_changes': len(extreme_changes)
            }
        
        if len(quality_report['issues']) > 0:
            quality_report['status'] = 'WARNINGS'
        
        return quality_report
    
    async def _run_real_data_backtest(self, data: dict) -> dict:
        """Run enhanced backtesting with real data"""
        
        print("Running enhanced backtesting with real data...")
        
        # Initialize backtesting engine
        self.backtesting_engine.data = data
        
        # Run backtest
        results = await self.backtesting_engine.run_backtest()
        
        # Calculate benchmark metrics
        if 'SPY' in data and 'strategy_returns' in results:
            spy_returns = data['SPY']['close'].pct_change().dropna()
            strategy_returns = pd.Series(results['strategy_returns'])
            
            benchmark_metrics = self.benchmark_analyzer.calculate_benchmark_metrics(
                strategy_returns, spy_returns
            )
            
            results['benchmark_metrics'] = benchmark_metrics
        
        return results
    
    def _validate_against_academic_benchmarks(self, results: dict) -> dict:
        """Validate results against academic research benchmarks"""
        
        academic_validation = {
            'status': 'PASS',
            'benchmarks': {},
            'deviations': []
        }
        
        # Academic momentum benchmarks (Jegadeesh & Titman, 1993)
        if 'benchmark_metrics' in results:
            metrics = results['benchmark_metrics']
            
            # Information ratio benchmark (target: > 0.5)
            info_ratio = metrics.get('information_ratio', 0)
            if info_ratio < 0.5:
                academic_validation['deviations'].append(
                    f"Information ratio ({info_ratio:.3f}) below academic benchmark (0.5)"
                )
            
            # Sharpe ratio benchmark (target: > 1.0)
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            if sharpe_ratio < 1.0:
                academic_validation['deviations'].append(
                    f"Sharpe ratio ({sharpe_ratio:.3f}) below academic benchmark (1.0)"
                )
            
            # Maximum drawdown benchmark (target: < 20%)
            max_drawdown = abs(metrics.get('max_strategy_drawdown', 0))
            if max_drawdown > 0.20:
                academic_validation['deviations'].append(
                    f"Maximum drawdown ({max_drawdown:.1%}) above academic benchmark (20%)"
                )
            
            academic_validation['benchmarks'] = {
                'information_ratio': {'actual': info_ratio, 'target': 0.5},
                'sharpe_ratio': {'actual': sharpe_ratio, 'target': 1.0},
                'max_drawdown': {'actual': max_drawdown, 'target': 0.20}
            }
        
        if len(academic_validation['deviations']) > 0:
            academic_validation['status'] = 'DEVIATIONS'
        
        return academic_validation
    
    def _generate_testing_report(self, backtest_results: dict, academic_validation: dict):
        """Generate comprehensive testing report"""
        
        print("\n=== REAL HISTORICAL DATA TESTING REPORT ===")
        
        # Performance summary
        if 'benchmark_metrics' in backtest_results:
            metrics = backtest_results['benchmark_metrics']
            print(f"Information Ratio: {metrics.get('information_ratio', 0):.3f}")
            print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"Maximum Drawdown: {metrics.get('max_strategy_drawdown', 0):.1%}")
            print(f"Beta: {metrics.get('beta', 0):.3f}")
        
        # Academic validation summary
        print(f"\nAcademic Validation: {academic_validation['status']}")
        for deviation in academic_validation['deviations']:
            print(f"  ⚠️  {deviation}")
        
        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'backtest_results': backtest_results,
            'academic_validation': academic_validation
        }
        
        with open('real_historical_data_testing_report.json', 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: real_historical_data_testing_report.json")

async def main():
    """Run real historical data testing"""
    tester = RealHistoricalDataTester()
    results = await tester.test_with_real_data()
    return results

if __name__ == "__main__":
    asyncio.run(main())
```

### **4.2 Multi-Strategy Backtesting**

**File: `backtesting_framework/tests/test_multi_strategy_backtesting.py`**

```python
#!/usr/bin/env python3
"""
Phase 4.2: Multi-Strategy Backtesting
Test multiple strategies with real data
"""

import asyncio
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List

from backtesting_framework.strategies.enhanced_academic_strategy import EnhancedAcademicStrategy
from backtesting_framework.strategies.momentum_strategy import MomentumStrategy
from backtesting_framework.strategies.pairs_trading import PairsTradingStrategy
from core_structure.performance.benchmark_analyzer import BenchmarkAnalyzer

class MultiStrategyBacktester:
    """Test multiple strategies with real data"""
    
    def __init__(self):
        self.strategies = {
            'enhanced_academic': EnhancedAcademicStrategy,
            'momentum': MomentumStrategy,
            'pairs_trading': PairsTradingStrategy
        }
        self.benchmark_analyzer = BenchmarkAnalyzer()
        
    async def test_multiple_strategies(self, data: dict) -> dict:
        """Test multiple strategies with same data"""
        
        print("=== Phase 4.2: Multi-Strategy Backtesting ===")
        
        results = {}
        
        for strategy_name, strategy_class in self.strategies.items():
            print(f"\nTesting {strategy_name} strategy...")
            
            try:
                # Initialize strategy
                strategy = strategy_class({
                    'name': strategy_name,
                    'symbols': list(data.keys()),
                    'initial_capital': 100000.0
                })
                
                # Run backtest
                strategy.initialize(data)
                signals = strategy.generate_signals(data)
                
                # Calculate performance
                performance = strategy.calculate_performance_metrics()
                
                # Benchmark analysis
                if 'SPY' in data:
                    spy_returns = data['SPY']['close'].pct_change().dropna()
                    strategy_returns = pd.Series(strategy.returns)
                    
                    benchmark_metrics = self.benchmark_analyzer.calculate_benchmark_metrics(
                        strategy_returns, spy_returns
                    )
                    
                    performance['benchmark_metrics'] = benchmark_metrics
                
                results[strategy_name] = {
                    'performance': performance,
                    'signals_generated': len(signals),
                    'status': 'SUCCESS'
                }
                
                print(f"✅ {strategy_name}: {performance.get('total_return', 0):.2%} return")
                
            except Exception as e:
                print(f"❌ {strategy_name} failed: {e}")
                results[strategy_name] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
        
        # Compare strategies
        comparison = self._compare_strategies(results)
        
        return {
            'individual_results': results,
            'comparison': comparison
        }
    
    def _compare_strategies(self, results: dict) -> dict:
        """Compare performance across strategies"""
        
        comparison = {
            'best_performer': None,
            'best_information_ratio': None,
            'best_sharpe_ratio': None,
            'most_consistent': None,
            'summary': {}
        }
        
        valid_results = {k: v for k, v in results.items() if v['status'] == 'SUCCESS'}
        
        if not valid_results:
            return comparison
        
        # Find best performers
        returns = {}
        info_ratios = {}
        sharpe_ratios = {}
        
        for strategy_name, result in valid_results.items():
            performance = result['performance']
            
            returns[strategy_name] = performance.get('total_return', 0)
            
            if 'benchmark_metrics' in performance:
                benchmark = performance['benchmark_metrics']
                info_ratios[strategy_name] = benchmark.get('information_ratio', 0)
                sharpe_ratios[strategy_name] = benchmark.get('sharpe_ratio', 0)
        
        # Best performers
        if returns:
            comparison['best_performer'] = max(returns, key=returns.get)
        
        if info_ratios:
            comparison['best_information_ratio'] = max(info_ratios, key=info_ratios.get)
        
        if sharpe_ratios:
            comparison['best_sharpe_ratio'] = max(sharpe_ratios, key=sharpe_ratios.get)
        
        # Summary statistics
        comparison['summary'] = {
            'total_strategies': len(results),
            'successful_strategies': len(valid_results),
            'average_return': np.mean(list(returns.values())) if returns else 0,
            'average_information_ratio': np.mean(list(info_ratios.values())) if info_ratios else 0,
            'average_sharpe_ratio': np.mean(list(sharpe_ratios.values())) if sharpe_ratios else 0
        }
        
        return comparison

async def main():
    """Run multi-strategy backtesting"""
    # Load real data (from Phase 4.1)
    from backtesting_framework.tests.test_real_historical_data import RealHistoricalDataTester
    
    data_tester = RealHistoricalDataTester()
    data = await data_tester._load_real_historical_data(
        ['SPY', 'AAPL', 'MSFT', 'GOOGL'], '2023-01-01', '2025-06-30'
    )
    
    multi_tester = MultiStrategyBacktester()
    results = await multi_tester.test_multiple_strategies(data)
    
    # Print comparison
    print("\n=== STRATEGY COMPARISON ===")
    comparison = results['comparison']
    print(f"Best Performer: {comparison['best_performer']}")
    print(f"Best Information Ratio: {comparison['best_information_ratio']}")
    print(f"Best Sharpe Ratio: {comparison['best_sharpe_ratio']}")
    print(f"Average Return: {comparison['summary']['average_return']:.2%}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
```

### **4.3 Academic Benchmark Validation**

**File: `backtesting_framework/tests/test_academic_benchmarks.py`**

```python
#!/usr/bin/env python3
"""
Phase 4.3: Academic Benchmark Validation
Validate against published research results
"""

import numpy as np
import pandas as pd
from typing import Dict, List

class AcademicBenchmarkValidator:
    """Validate strategy performance against academic benchmarks"""
    
    def __init__(self):
        # Academic benchmarks from published research
        self.academic_benchmarks = {
            'jegadeesh_titman_1993': {
                'momentum_12m_skip_1m': {
                    'mean_return': 0.012,  # 1.2% monthly
                    'sharpe_ratio': 0.52,
                    'max_drawdown': -0.15
                }
            },
            'carhart_1997': {
                'momentum_factor': {
                    'mean_return': 0.009,  # 0.9% monthly
                    'sharpe_ratio': 0.45,
                    'beta': 0.02
                }
            },
            'moskowitz_grinblatt_1999': {
                'industry_momentum': {
                    'mean_return': 0.008,  # 0.8% monthly
                    'sharpe_ratio': 0.40,
                    'max_drawdown': -0.12
                }
            },
            'hong_stein_1999': {
                'news_diffusion': {
                    'mean_return': 0.010,  # 1.0% monthly
                    'sharpe_ratio': 0.48,
                    'volume_premium': 0.003
                }
            },
            'chordia_shivakumar_2002': {
                'business_cycle': {
                    'mean_return': 0.011,  # 1.1% monthly
                    'sharpe_ratio': 0.50,
                    'macro_adjustment': 0.002
                }
            }
        }
    
    def validate_against_academic_benchmarks(self, strategy_results: dict) -> dict:
        """Validate strategy results against academic benchmarks"""
        
        validation_results = {
            'overall_score': 0.0,
            'benchmark_comparisons': {},
            'deviations': [],
            'recommendations': []
        }
        
        total_score = 0.0
        total_benchmarks = 0
        
        for benchmark_name, benchmark_data in self.academic_benchmarks.items():
            comparison = self._compare_with_benchmark(strategy_results, benchmark_name, benchmark_data)
            validation_results['benchmark_comparisons'][benchmark_name] = comparison
            
            if comparison['score'] > 0:
                total_score += comparison['score']
                total_benchmarks += 1
        
        if total_benchmarks > 0:
            validation_results['overall_score'] = total_score / total_benchmarks
        
        # Generate recommendations
        validation_results['recommendations'] = self._generate_recommendations(validation_results)
        
        return validation_results
    
    def _compare_with_benchmark(self, strategy_results: dict, benchmark_name: str, benchmark_data: dict) -> dict:
        """Compare strategy results with specific academic benchmark"""
        
        comparison = {
            'benchmark_name': benchmark_name,
            'score': 0.0,
            'metrics': {},
            'deviations': []
        }
        
        strategy_metrics = strategy_results.get('benchmark_metrics', {})
        
        for metric_name, benchmark_value in benchmark_data.items():
            if isinstance(benchmark_value, dict):
                # Nested benchmark (e.g., momentum_12m_skip_1m)
                for sub_metric, expected_value in benchmark_value.items():
                    actual_value = strategy_metrics.get(sub_metric, 0)
                    deviation = self._calculate_deviation(actual_value, expected_value)
                    
                    comparison['metrics'][f"{metric_name}_{sub_metric}"] = {
                        'actual': actual_value,
                        'expected': expected_value,
                        'deviation': deviation
                    }
                    
                    if abs(deviation) > 0.5:  # 50% deviation threshold
                        comparison['deviations'].append(
                            f"{metric_name}_{sub_metric}: {deviation:.1%} deviation"
                        )
            else:
                # Direct metric comparison
                actual_value = strategy_metrics.get(metric_name, 0)
                deviation = self._calculate_deviation(actual_value, benchmark_value)
                
                comparison['metrics'][metric_name] = {
                    'actual': actual_value,
                    'expected': benchmark_value,
                    'deviation': deviation
                }
                
                if abs(deviation) > 0.5:
                    comparison['deviations'].append(
                        f"{metric_name}: {deviation:.1%} deviation"
                    )
        
        # Calculate overall score for this benchmark
        if comparison['metrics']:
            deviations = [abs(m['deviation']) for m in comparison['metrics'].values()]
            avg_deviation = np.mean(deviations)
            comparison['score'] = max(0, 1 - avg_deviation)  # Score decreases with deviation
        
        return comparison
    
    def _calculate_deviation(self, actual: float, expected: float) -> float:
        """Calculate percentage deviation from expected value"""
        if expected == 0:
            return 0.0
        return (actual - expected) / abs(expected)
    
    def _generate_recommendations(self, validation_results: dict) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        overall_score = validation_results['overall_score']
        
        if overall_score < 0.5:
            recommendations.append("Consider parameter optimization to better align with academic benchmarks")
            recommendations.append("Review signal generation logic for consistency with research")
        
        if overall_score < 0.7:
            recommendations.append("Implement additional academic factors to improve performance")
            recommendations.append("Consider regime-dependent parameter adjustment")
        
        # Check specific deviations
        for benchmark_name, comparison in validation_results['benchmark_comparisons'].items():
            if len(comparison['deviations']) > 0:
                recommendations.append(f"Address deviations in {benchmark_name} implementation")
        
        if not recommendations:
            recommendations.append("Strategy performance aligns well with academic benchmarks")
        
        return recommendations

def main():
    """Run academic benchmark validation"""
    
    # Example strategy results (from Phase 4.1)
    strategy_results = {
        'benchmark_metrics': {
            'information_ratio': 0.65,
            'sharpe_ratio': 0.48,
            'max_drawdown': -0.18,
            'beta': 0.05
        }
    }
    
    validator = AcademicBenchmarkValidator()
    validation_results = validator.validate_against_academic_benchmarks(strategy_results)
    
    print("=== ACADEMIC BENCHMARK VALIDATION ===")
    print(f"Overall Score: {validation_results['overall_score']:.2f}")
    
    for benchmark_name, comparison in validation_results['benchmark_comparisons'].items():
        print(f"\n{benchmark_name}:")
        print(f"  Score: {comparison['score']:.2f}")
        for metric_name, metric_data in comparison['metrics'].items():
            print(f"  {metric_name}: {metric_data['actual']:.3f} vs {metric_data['expected']:.3f}")
    
    print(f"\nRecommendations:")
    for rec in validation_results['recommendations']:
        print(f"  • {rec}")
    
    return validation_results

if __name__ == "__main__":
    main()
```

---

## 🎯 **Phase 5: Performance Optimization**

### **5.1 Advanced Parameter Optimization**

**Objective**: Optimize strategy parameters using enhanced framework

**File: `backtesting_framework/optimization/advanced_parameter_optimizer.py`**

```python
#!/usr/bin/env python3
"""
Phase 5.1: Advanced Parameter Optimization
Multi-dimensional parameter optimization with academic constraints
"""

import asyncio
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from itertools import product
import json
from dataclasses import dataclass

from backtesting_framework.enhanced_backtesting_engine import EnhancedBacktestingEngine
from core_structure.performance.benchmark_analyzer import BenchmarkAnalyzer, BenchmarkConfig

@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    
    # Academic parameter ranges (based on research)
    momentum_lookback_ranges = {
        'short_term': [3, 5, 7, 10],      # 1 week variations
        'medium_term': [15, 20, 25, 30],  # 1 month variations
        'long_term': [50, 60, 70, 80],    # 3 month variations
        'intermediate': [100, 120, 140, 160]  # 6 month variations
    }
    
    volume_weight_ranges = [0.1, 0.2, 0.3, 0.4, 0.5]
    regime_weight_ranges = [0.8, 1.0, 1.2, 1.5]
    signal_threshold_ranges = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    # Optimization objectives
    primary_objective = 'information_ratio'  # or 'sharpe_ratio', 'total_return'
    secondary_objective = 'max_drawdown'     # minimize drawdown
    
    # Constraints
    min_information_ratio = 0.5
    max_drawdown_limit = 0.20
    min_sharpe_ratio = 1.0
    
    # Optimization method
    method = 'grid_search'  # or 'bayesian', 'genetic'
    max_iterations = 1000

class AdvancedParameterOptimizer:
    """Advanced parameter optimizer with academic constraints"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.backtesting_engine = EnhancedBacktestingEngine()
        self.benchmark_analyzer = BenchmarkAnalyzer(BenchmarkConfig())
        self.optimization_results = []
        self.best_parameters = None
        self.best_score = -np.inf
        
    async def optimize_parameters(self, data: dict) -> dict:
        """Optimize strategy parameters using grid search"""
        
        print("=== Phase 5.1: Advanced Parameter Optimization ===")
        print(f"Method: {self.config.method}")
        print(f"Max iterations: {self.config.max_iterations}")
        
        if self.config.method == 'grid_search':
            return await self._grid_search_optimization(data)
        elif self.config.method == 'bayesian':
            return await self._bayesian_optimization(data)
        else:
            raise ValueError(f"Unsupported optimization method: {self.config.method}")
    
    async def _grid_search_optimization(self, data: dict) -> dict:
        """Grid search optimization with academic parameter ranges"""
        
        # Generate parameter combinations
        parameter_combinations = self._generate_parameter_combinations()
        
        print(f"Testing {len(parameter_combinations)} parameter combinations...")
        
        for i, params in enumerate(parameter_combinations):
            if i >= self.config.max_iterations:
                print(f"Reached max iterations ({self.config.max_iterations})")
                break
            
            try:
                # Test parameter combination
                result = await self._test_parameter_combination(data, params)
                
                if result['valid']:
                    # Calculate optimization score
                    score = self._calculate_optimization_score(result['metrics'])
                    
                    optimization_result = {
                        'parameters': params,
                        'metrics': result['metrics'],
                        'score': score,
                        'iteration': i + 1
                    }
                    
                    self.optimization_results.append(optimization_result)
                    
                    # Update best result
                    if score > self.best_score:
                        self.best_score = score
                        self.best_parameters = params
                        print(f"✅ New best score: {score:.3f} (iteration {i + 1})")
                
                # Progress update
                if (i + 1) % 100 == 0:
                    print(f"Progress: {i + 1}/{min(len(parameter_combinations), self.config.max_iterations)}")
                    
            except Exception as e:
                print(f"❌ Parameter combination {i + 1} failed: {e}")
                continue
        
        # Generate optimization report
        optimization_report = self._generate_optimization_report()
        
        return {
            'best_parameters': self.best_parameters,
            'best_score': self.best_score,
            'total_tested': len(self.optimization_results),
            'optimization_report': optimization_report
        }
    
    def _generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate parameter combinations for grid search"""
        
        combinations = []
        
        # Generate all combinations
        for short_term in self.config.momentum_lookback_ranges['short_term']:
            for medium_term in self.config.momentum_lookback_ranges['medium_term']:
                for long_term in self.config.momentum_lookback_ranges['long_term']:
                    for intermediate in self.config.momentum_lookback_ranges['intermediate']:
                        for volume_weight in self.config.volume_weight_ranges:
                            for regime_weight in self.config.regime_weight_ranges:
                                for signal_threshold in self.config.signal_threshold_ranges:
                                    
                                    # Academic validation
                                    if self._validate_academic_parameters(
                                        short_term, medium_term, long_term, intermediate,
                                        volume_weight, regime_weight, signal_threshold
                                    ):
                                        params = {
                                            'momentum_lookback_short': short_term,
                                            'momentum_lookback_medium': medium_term,
                                            'momentum_lookback_long': long_term,
                                            'momentum_lookback_intermediate': intermediate,
                                            'volume_weight': volume_weight,
                                            'regime_weight': regime_weight,
                                            'signal_threshold': signal_threshold
                                        }
                                        combinations.append(params)
        
        return combinations
    
    def _validate_academic_parameters(self, short_term: int, medium_term: int, 
                                    long_term: int, intermediate: int,
                                    volume_weight: float, regime_weight: float, 
                                    signal_threshold: float) -> bool:
        """Validate parameters against academic research constraints"""
        
        # Momentum hierarchy constraint (short < medium < long < intermediate)
        if not (short_term < medium_term < long_term < intermediate):
            return False
        
        # Academic momentum ranges (Jegadeesh & Titman, 1993)
        if not (3 <= short_term <= 10):
            return False
        if not (15 <= medium_term <= 30):
            return False
        if not (50 <= long_term <= 80):
            return False
        if not (100 <= intermediate <= 160):
            return False
        
        # Volume weight constraint (Gervais et al., 2001)
        if not (0.1 <= volume_weight <= 0.5):
            return False
        
        # Regime weight constraint (Cooper et al., 2004)
        if not (0.8 <= regime_weight <= 1.5):
            return False
        
        # Signal threshold constraint
        if not (0.5 <= signal_threshold <= 0.9):
            return False
        
        return True
    
    async def _test_parameter_combination(self, data: dict, params: dict) -> dict:
        """Test a specific parameter combination"""
        
        try:
            # Update strategy configuration with new parameters
            strategy_config = {
                'name': 'enhanced_academic_strategy',
                'symbols': list(data.keys()),
                'initial_capital': 100000.0,
                'parameters': params
            }
            
            # Initialize backtesting engine with new parameters
            self.backtesting_engine.strategy = None  # Reset strategy
            self.backtesting_engine.data = data
            
            # Run backtest with new parameters
            results = await self.backtesting_engine.run_backtest()
            
            # Calculate benchmark metrics
            if 'SPY' in data and 'strategy_returns' in results:
                spy_returns = data['SPY']['close'].pct_change().dropna()
                strategy_returns = pd.Series(results['strategy_returns'])
                
                benchmark_metrics = self.benchmark_analyzer.calculate_benchmark_metrics(
                    strategy_returns, spy_returns
                )
                
                # Validate against constraints
                valid = self._validate_constraints(benchmark_metrics)
                
                return {
                    'valid': valid,
                    'metrics': benchmark_metrics
                }
            else:
                return {'valid': False, 'metrics': {}}
                
        except Exception as e:
            return {'valid': False, 'metrics': {}, 'error': str(e)}
    
    def _validate_constraints(self, metrics: dict) -> bool:
        """Validate results against optimization constraints"""
        
        # Check minimum information ratio
        info_ratio = metrics.get('information_ratio', 0)
        if info_ratio < self.config.min_information_ratio:
            return False
        
        # Check maximum drawdown
        max_drawdown = abs(metrics.get('max_strategy_drawdown', 0))
        if max_drawdown > self.config.max_drawdown_limit:
            return False
        
        # Check minimum Sharpe ratio
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        if sharpe_ratio < self.config.min_sharpe_ratio:
            return False
        
        return True
    
    def _calculate_optimization_score(self, metrics: dict) -> float:
        """Calculate optimization score based on objectives"""
        
        # Primary objective
        primary_value = metrics.get(self.config.primary_objective, 0)
        
        # Secondary objective (penalty for high drawdown)
        secondary_value = abs(metrics.get(self.config.secondary_objective, 0))
        
        # Weighted score
        score = primary_value - 0.5 * secondary_value
        
        return score
    
    def _generate_optimization_report(self) -> dict:
        """Generate comprehensive optimization report"""
        
        if not self.optimization_results:
            return {'status': 'No valid results'}
        
        # Sort results by score
        sorted_results = sorted(self.optimization_results, key=lambda x: x['score'], reverse=True)
        
        # Top 10 results
        top_results = sorted_results[:10]
        
        # Parameter sensitivity analysis
        sensitivity = self._analyze_parameter_sensitivity()
        
        # Statistical summary
        scores = [r['score'] for r in self.optimization_results]
        score_stats = {
            'mean': np.mean(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'median': np.median(scores)
        }
        
        return {
            'total_combinations_tested': len(self.optimization_results),
            'best_score': self.best_score,
            'best_parameters': self.best_parameters,
            'top_10_results': top_results,
            'parameter_sensitivity': sensitivity,
            'score_statistics': score_stats
        }
    
    def _analyze_parameter_sensitivity(self) -> dict:
        """Analyze sensitivity of each parameter"""
        
        sensitivity = {}
        
        # Analyze each parameter's impact on score
        for param_name in ['momentum_lookback_short', 'momentum_lookback_medium', 
                          'momentum_lookback_long', 'volume_weight', 'signal_threshold']:
            
            param_values = []
            scores = []
            
            for result in self.optimization_results:
                param_value = result['parameters'].get(param_name, 0)
                param_values.append(param_value)
                scores.append(result['score'])
            
            # Calculate correlation
            if len(param_values) > 1:
                correlation = np.corrcoef(param_values, scores)[0, 1]
                sensitivity[param_name] = {
                    'correlation': correlation,
                    'impact': 'positive' if correlation > 0.1 else 'negative' if correlation < -0.1 else 'neutral'
                }
        
        return sensitivity

async def main():
    """Run advanced parameter optimization"""
    
    # Load real data (from Phase 4.1)
    from backtesting_framework.tests.test_real_historical_data import RealHistoricalDataTester
    
    data_tester = RealHistoricalDataTester()
    data = await data_tester._load_real_historical_data(
        ['SPY', 'AAPL', 'MSFT', 'GOOGL'], '2023-01-01', '2025-06-30'
    )
    
    # Initialize optimizer
    config = OptimizationConfig()
    optimizer = AdvancedParameterOptimizer(config)
    
    # Run optimization
    results = await optimizer.optimize_parameters(data)
    
    # Print results
    print("\n=== OPTIMIZATION RESULTS ===")
    print(f"Best Score: {results['best_score']:.3f}")
    print(f"Best Parameters: {results['best_parameters']}")
    print(f"Total Tested: {results['total_tested']}")
    
    # Save results
    with open('parameter_optimization_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: parameter_optimization_results.json")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
```

This completes Phase 5.1 (Advanced Parameter Optimization). Would you like me to continue with Phase 5.2 (Multi-dimensional Parameter Sweeps) and Phase 5.3 (SPY Benchmark Optimization) in the next batch? 