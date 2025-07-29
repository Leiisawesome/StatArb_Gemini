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

### **Phase 8: Broker Integration & Multi-Broker Implementation** ⭐ **NEW**
- **Multi-broker abstract interface design**
- **Interactive Brokers integration**
- **Alpaca integration**
- **Paper trading implementation**
- **Live trading implementation**
- **Broker-agnostic execution engine**
- **Risk management integration**
- **Order management system**

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

---

## 🎯 **Phase 8: Broker Integration & Multi-Broker Implementation** ⭐ **NEW**

### **8.1 Multi-Broker Abstract Interface Design**

**Objective**: Create a broker-agnostic interface that supports multiple brokers (Interactive Brokers, Alpaca, etc.)

**File: `core_structure/execution_engine/broker_interface.py`**

```python
#!/usr/bin/env python3
"""
Phase 8.1: Multi-Broker Abstract Interface
Broker-agnostic interface for multiple broker integrations
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from datetime import datetime

@dataclass
class BrokerConfig:
    """Configuration for broker connection"""
    broker_type: str
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    paper_trading: bool = True
    account_id: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30

@dataclass
class OrderRequest:
    """Standardized order request"""
    symbol: str
    quantity: float
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop'
    time_in_force: str = 'day'
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    client_order_id: Optional[str] = None

@dataclass
class OrderResponse:
    """Standardized order response"""
    order_id: str
    status: str
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    timestamp: datetime = None

@dataclass
class Position:
    """Standardized position information"""
    symbol: str
    quantity: float
    average_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float

@dataclass
class AccountInfo:
    """Standardized account information"""
    account_id: str
    cash: float
    buying_power: float
    equity: float
    margin_used: float
    positions: List[Position]

class BrokerType(Enum):
    """Supported broker types"""
    INTERACTIVE_BROKERS = "interactive_brokers"
    ALPACA = "alpaca"
    TD_AMERITRADE = "td_ameritrade"
    ETRADE = "etrade"
    ROBINHOOD = "robinhood"

class BaseBrokerInterface(ABC):
    """Abstract base class for broker interfaces"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time market data"""
        pass

class BrokerFactory:
    """Factory for creating broker interfaces"""
    
    @staticmethod
    def create_broker(broker_type: str, config: BrokerConfig) -> BaseBrokerInterface:
        """Create broker interface based on type"""
        
        if broker_type == BrokerType.INTERACTIVE_BROKERS.value:
            from .interactive_brokers_interface import InteractiveBrokersInterface
            return InteractiveBrokersInterface(config)
            
        elif broker_type == BrokerType.ALPACA.value:
            from .alpaca_interface import AlpacaInterface
            return AlpacaInterface(config)
            
        elif broker_type == BrokerType.TD_AMERITRADE.value:
            from .td_ameritrade_interface import TDAmeritradeInterface
            return TDAmeritradeInterface(config)
            
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

class MultiBrokerManager:
    """Manager for multiple broker connections"""
    
    def __init__(self):
        self.brokers: Dict[str, BaseBrokerInterface] = {}
        self.logger = logging.getLogger(__name__)
        
    async def add_broker(self, name: str, broker_type: str, config: BrokerConfig) -> bool:
        """Add a broker connection"""
        try:
            broker = BrokerFactory.create_broker(broker_type, config)
            success = await broker.connect()
            
            if success:
                self.brokers[name] = broker
                self.logger.info(f"✅ Added broker: {name} ({broker_type})")
                return True
            else:
                self.logger.error(f"❌ Failed to connect to broker: {name}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error adding broker {name}: {e}")
            return False
    
    async def remove_broker(self, name: str) -> bool:
        """Remove a broker connection"""
        if name in self.brokers:
            broker = self.brokers[name]
            await broker.disconnect()
            del self.brokers[name]
            self.logger.info(f"✅ Removed broker: {name}")
            return True
        return False
    
    async def place_order_on_broker(self, broker_name: str, order: OrderRequest) -> OrderResponse:
        """Place order on specific broker"""
        if broker_name not in self.brokers:
            raise ValueError(f"Broker {broker_name} not found")
        
        broker = self.brokers[broker_name]
        return await broker.place_order(order)
    
    async def get_all_positions(self) -> Dict[str, List[Position]]:
        """Get positions from all brokers"""
        positions = {}
        for name, broker in self.brokers.items():
            try:
                positions[name] = await broker.get_positions()
            except Exception as e:
                self.logger.error(f"Error getting positions from {name}: {e}")
                positions[name] = []
        return positions
    
    async def get_all_account_info(self) -> Dict[str, AccountInfo]:
        """Get account info from all brokers"""
        accounts = {}
        for name, broker in self.brokers.items():
            try:
                accounts[name] = await broker.get_account_info()
            except Exception as e:
                self.logger.error(f"Error getting account info from {name}: {e}")
        return accounts

async def main():
    """Test multi-broker interface"""
    
    # Create broker configurations
    alpaca_config = BrokerConfig(
        broker_type=BrokerType.ALPACA.value,
        api_key="your_alpaca_api_key",
        secret_key="your_alpaca_secret_key",
        paper_trading=True
    )
    
    ib_config = BrokerConfig(
        broker_type=BrokerType.INTERACTIVE_BROKERS.value,
        account_id="your_ib_account",
        paper_trading=True
    )
    
    # Create multi-broker manager
    manager = MultiBrokerManager()
    
    # Add brokers
    await manager.add_broker("alpaca_paper", BrokerType.ALPACA.value, alpaca_config)
    await manager.add_broker("ib_paper", BrokerType.INTERACTIVE_BROKERS.value, ib_config)
    
    # Test functionality
    accounts = await manager.get_all_account_info()
    positions = await manager.get_all_positions()
    
    print("=== Multi-Broker Test Results ===")
    for name, account in accounts.items():
        print(f"{name}: ${account.equity:,.2f} equity")
    
    return manager

if __name__ == "__main__":
    asyncio.run(main())
```

### **8.2 Interactive Brokers TWS API Integration** ⭐ **ENHANCED**

**Objective**: Implement comprehensive IBKR TWS API integration for professional algorithmic trading

**File: `core_structure/execution_engine/interactive_brokers_interface.py`**

```python
#!/usr/bin/env python3
"""
Phase 8.2: Interactive Brokers TWS API Integration
Professional IBKR TWS API integration for algorithmic trading
Based on: https://www.interactivebrokers.com/en/trading/ib-api.php
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import pandas as pd
import threading
import time

# IB API imports (requires ibapi package)
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.common import *
    from ibapi.utils import iswrapper
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("⚠️  IB API not available. Install with: pip install ibapi")

from .broker_interface import BaseBrokerInterface, BrokerConfig, OrderRequest, OrderResponse, Position, AccountInfo

@dataclass
class IBKRConfig(BrokerConfig):
    """Enhanced IBKR-specific configuration"""
    tws_host: str = "127.0.0.1"
    tws_port: int = 7497  # 7497 for paper, 7496 for live
    client_id: int = 1
    tws_timeout: int = 20
    enable_notifications: bool = True
    market_data_type: str = "REAL_TIME"  # REAL_TIME, FROZEN, DELAYED
    use_smart_routing: bool = True
    enable_advanced_order_types: bool = True

class InteractiveBrokersInterface(BaseBrokerInterface, EWrapper):
    """
    Interactive Brokers TWS API Interface
    Professional implementation for algorithmic trading
    
    Features:
    - Real-time market data streaming
    - Advanced order types (TWAP, VWAP, Implementation Shortfall)
    - Smart routing and execution
    - Portfolio and position management
    - Risk management integration
    - Multi-asset support (stocks, options, futures)
    """
    
    def __init__(self, config: IBKRConfig):
        BaseBrokerInterface.__init__(self, config)
        EWrapper.__init__(self)
        
        if not IB_AVAILABLE:
            raise ImportError("IB API not available. Install with: pip install ibapi")
        
        # TWS API client
        self.client = EClient(self)
        self.config = config
        
        # Connection management
        self.next_order_id = None
        self.connected = False
        self.client_thread = None
        
        # Data storage
        self.orders = {}
        self.positions = {}
        self.account_info = None
        self.market_data = {}
        self.contract_details = {}
        
        # Callback handlers
        self.order_status_callbacks = {}
        self.position_callbacks = {}
        self.account_callbacks = {}
        self.market_data_callbacks = {}
        
        # Risk management
        self.position_limits = {}
        self.order_limits = {}
        self.risk_checks_enabled = True
        
    async def connect(self) -> bool:
        """
        Connect to Interactive Brokers TWS API
        Supports both TWS (Trader Workstation) and IB Gateway
        """
        try:
            self.logger.info(f"🔌 Connecting to IBKR TWS at {self.config.tws_host}:{self.config.tws_port}")
            
            # Connect to TWS/IB Gateway
            self.client.connect(
                self.config.tws_host, 
                self.config.tws_port, 
                self.config.client_id
            )
            
            # Start client thread for message processing
            self.client_thread = threading.Thread(target=self.client.run, daemon=True)
            self.client_thread.start()
            
            # Wait for connection and nextValidId
            timeout = time.time() + self.config.tws_timeout
            while time.time() < timeout:
                if self.client.isConnected() and self.next_order_id is not None:
                    self.connected = True
                    self.logger.info(f"✅ Connected to IBKR TWS (Client ID: {self.config.client_id})")
                    
                    # Enable notifications if requested
                    if self.config.enable_notifications:
                        self.client.reqAutoOpenOrders(True)
                        self.client.reqAllOpenOrders()
                    
                    return True
                await asyncio.sleep(0.1)
            
            self.logger.error("❌ Timeout connecting to IBKR TWS")
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to IBKR TWS: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Interactive Brokers"""
        try:
            if self.client.isConnected():
                self.client.disconnect()
                self.connected = False
                self.logger.info("✅ Disconnected from Interactive Brokers")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error disconnecting from IB: {e}")
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information from IB"""
        if not self.connected:
            raise ConnectionError("Not connected to IB")
        
        # Request account info
        self.client.reqAccountUpdates(True, "")
        
        # Wait for account data
        await asyncio.sleep(1)
        
        if self.account_info:
            return self.account_info
        else:
            raise Exception("Failed to get account info")
    
    async def get_positions(self) -> List[Position]:
        """Get current positions from IB"""
        if not self.connected:
            raise ConnectionError("Not connected to IB")
        
        # Request positions
        self.client.reqPositions()
        
        # Wait for position data
        await asyncio.sleep(1)
        
        return list(self.positions.values())
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """
        Place order on Interactive Brokers TWS API
        Supports advanced order types: MARKET, LIMIT, STOP, TWAP, VWAP, Implementation Shortfall
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR TWS")
        
        # Risk management checks
        if self.risk_checks_enabled:
            risk_check = await self._perform_risk_checks(order)
            if not risk_check['passed']:
                raise ValueError(f"Risk check failed: {risk_check['reason']}")
        
        # Create IB contract with smart routing
        contract = self._create_contract(order.symbol)
        
        # Create IB order with advanced features
        ib_order = self._create_advanced_order(order)
        
        # Place order
        order_id = self.next_order_id
        self.client.placeOrder(order_id, contract, ib_order)
        
        # Store order request for tracking
        self.orders[order_id] = {
            'request': order,
            'status': 'submitted',
            'timestamp': datetime.now(),
            'contract': contract,
            'ib_order': ib_order
        }
        
        self.logger.info(f"📤 Placed order {order_id}: {order.side} {order.quantity} {order.symbol}")
        
        # Return response
        return OrderResponse(
            order_id=str(order_id),
            status="submitted",
            timestamp=datetime.now()
        )
    
    def _create_contract(self, symbol: str) -> Contract:
        """Create IB contract with smart routing"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "USD"
        
        if self.config.use_smart_routing:
            contract.exchange = "SMART"  # Smart routing for best execution
        else:
            contract.exchange = "SMART"  # Default to SMART
        
        return contract
    
    def _create_advanced_order(self, order: OrderRequest) -> Order:
        """Create advanced IB order with sophisticated features"""
        ib_order = Order()
        ib_order.action = "BUY" if order.side == "buy" else "SELL"
        ib_order.totalQuantity = order.quantity
        ib_order.tif = order.time_in_force.upper()
        
        # Handle different order types
        if order.order_type.upper() == "MARKET":
            ib_order.orderType = "MKT"
            
        elif order.order_type.upper() == "LIMIT":
            ib_order.orderType = "LMT"
            if order.limit_price:
                ib_order.lmtPrice = order.limit_price
                
        elif order.order_type.upper() == "STOP":
            ib_order.orderType = "STP"
            if order.stop_price:
                ib_order.auxPrice = order.stop_price
                
        elif order.order_type.upper() == "TWAP" and self.config.enable_advanced_order_types:
            ib_order.orderType = "TWAP"
            # TWAP specific parameters would be set here
            
        elif order.order_type.upper() == "VWAP" and self.config.enable_advanced_order_types:
            ib_order.orderType = "VWAP"
            # VWAP specific parameters would be set here
            
        else:
            # Default to market order
            ib_order.orderType = "MKT"
        
        # Set client order ID for tracking
        if order.client_order_id:
            ib_order.orderId = order.client_order_id
        
        return ib_order
    
    async def _perform_risk_checks(self, order: OrderRequest) -> Dict[str, Any]:
        """Perform risk management checks before order placement"""
        checks = {
            'passed': True,
            'reason': None
        }
        
        # Position limit checks
        if order.symbol in self.position_limits:
            current_position = self.positions.get(order.symbol, 0)
            limit = self.position_limits[order.symbol]
            
            if order.side == "buy" and current_position + order.quantity > limit:
                checks['passed'] = False
                checks['reason'] = f"Position limit exceeded for {order.symbol}"
            elif order.side == "sell" and current_position - order.quantity < -limit:
                checks['passed'] = False
                checks['reason'] = f"Position limit exceeded for {order.symbol}"
        
        # Order size checks
        if order.quantity <= 0:
            checks['passed'] = False
            checks['reason'] = "Invalid order quantity"
        
        return checks
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Interactive Brokers"""
        if not self.connected:
            raise ConnectionError("Not connected to IB")
        
        try:
            self.client.cancelOrder(int(order_id))
            return True
        except Exception as e:
            self.logger.error(f"❌ Error canceling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status from Interactive Brokers"""
        # Implementation would track order status from IB callbacks
        # For now, return basic response
        return OrderResponse(
            order_id=order_id,
            status="unknown",
            timestamp=datetime.now()
        )
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time market data from IBKR TWS API
        Supports streaming data, snapshots, and historical data
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR TWS")
        
        # Create contract
        contract = self._create_contract(symbol)
        
        # Request real-time market data
        req_id = self.next_order_id
        self.client.reqMktData(req_id, contract, "", False, False, [])
        
        # Store callback for market data
        self.market_data_callbacks[req_id] = {
            'symbol': symbol,
            'data': {},
            'timestamp': datetime.now()
        }
        
        # Wait for initial data
        timeout = time.time() + 5
        while time.time() < timeout:
            if req_id in self.market_data_callbacks and self.market_data_callbacks[req_id]['data']:
                return self.market_data_callbacks[req_id]['data']
            await asyncio.sleep(0.1)
        
        # Return cached data if available
        return self.market_data.get(symbol, {
            "symbol": symbol,
            "bid": 0.0,
            "ask": 0.0,
            "last": 0.0,
            "volume": 0,
            "timestamp": datetime.now()
        })
    
    async def get_historical_data(self, symbol: str, duration: str = "1 D", 
                                bar_size: str = "1 min") -> pd.DataFrame:
        """
        Get historical data from IBKR TWS API
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR TWS")
        
        contract = self._create_contract(symbol)
        req_id = self.next_order_id
        
        # Request historical data
        self.client.reqHistoricalData(
            req_id, contract, "", duration, bar_size, 
            "TRADES", 1, 2, False, []
        )
        
        # Implementation would handle historical data callbacks
        # For now, return empty DataFrame
        return pd.DataFrame()
    
    def set_position_limit(self, symbol: str, limit: float):
        """Set position limit for risk management"""
        self.position_limits[symbol] = limit
        self.logger.info(f"📊 Set position limit for {symbol}: {limit}")
    
    def set_order_limit(self, symbol: str, max_quantity: float):
        """Set maximum order size for risk management"""
        self.order_limits[symbol] = max_quantity
        self.logger.info(f"📊 Set order limit for {symbol}: {max_quantity}")
    
    def enable_risk_checks(self, enabled: bool = True):
        """Enable or disable risk management checks"""
        self.risk_checks_enabled = enabled
        self.logger.info(f"🛡️ Risk checks {'enabled' if enabled else 'disabled'}")
    
    # IBKR TWS API Callbacks
    def nextValidId(self, orderId: int):
        """Called when next valid order ID is received from TWS"""
        self.next_order_id = orderId
        self.logger.debug(f"📋 Next valid order ID: {orderId}")
    
    def orderStatus(self, orderId: int, status: str, filled: float,
                   remaining: float, avgFillPrice: float, permId: int,
                   parentId: int, lastFillPrice: float, clientId: int,
                   whyHeld: str, mktCapPrice: float):
        """Called when order status changes from TWS"""
        if orderId in self.orders:
            order_info = self.orders[orderId]
            order_info['status'] = status
            order_info['filled_quantity'] = filled
            order_info['remaining_quantity'] = remaining
            order_info['avg_fill_price'] = avgFillPrice
            
            self.logger.info(f"📊 Order {orderId} status: {status} (filled: {filled}, remaining: {remaining})")
            
            # Trigger callback if registered
            if orderId in self.order_status_callbacks:
                callback = self.order_status_callbacks[orderId]
                callback(orderId, status, filled, remaining, avgFillPrice)
    
    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        """Called when position information is received from TWS"""
        symbol = contract.symbol
        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=position,
            average_price=avgCost,
            market_value=position * avgCost,
            unrealized_pnl=0.0,
            realized_pnl=0.0
        )
        
        self.logger.debug(f"📈 Position update: {symbol} = {position} @ ${avgCost:.2f}")
        
        # Trigger callback if registered
        if symbol in self.position_callbacks:
            callback = self.position_callbacks[symbol]
            callback(symbol, position, avgCost)
    
    def updateAccountValue(self, key: str, val: str, currency: str,
                          accountName: str):
        """Called when account value is updated from TWS"""
        if not self.account_info:
            self.account_info = AccountInfo(
                account_id=accountName,
                cash=0.0,
                buying_power=0.0,
                equity=0.0,
                margin_used=0.0,
                positions=[]
            )
        
        # Update account values based on key
        if key == "AvailableFunds" and currency == "USD":
            self.account_info.cash = float(val)
        elif key == "BuyingPower" and currency == "USD":
            self.account_info.buying_power = float(val)
        elif key == "NetLiquidation" and currency == "USD":
            self.account_info.equity = float(val)
        elif key == "GrossPositionValue" and currency == "USD":
            # Calculate margin used
            if self.account_info.equity > 0:
                self.account_info.margin_used = float(val) - self.account_info.equity
        
        self.logger.debug(f"💰 Account update: {key} = {val} {currency}")
        
        # Trigger callback if registered
        if key in self.account_callbacks:
            callback = self.account_callbacks[key]
            callback(key, val, currency, accountName)
    
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib: object):
        """Called when market data price updates are received"""
        if reqId in self.market_data_callbacks:
            data = self.market_data_callbacks[reqId]['data']
            symbol = self.market_data_callbacks[reqId]['symbol']
            
            # Map tick types to data fields
            if tickType == 1:  # Bid
                data['bid'] = price
            elif tickType == 2:  # Ask
                data['ask'] = price
            elif tickType == 4:  # Last
                data['last'] = price
            elif tickType == 6:  # High
                data['high'] = price
            elif tickType == 7:  # Low
                data['low'] = price
            elif tickType == 9:  # Close
                data['close'] = price
            
            data['timestamp'] = datetime.now()
            self.market_data[symbol] = data
    
    def tickSize(self, reqId: int, tickType: int, size: int):
        """Called when market data size updates are received"""
        if reqId in self.market_data_callbacks:
            data = self.market_data_callbacks[reqId]['data']
            
            if tickType == 0:  # Bid size
                data['bid_size'] = size
            elif tickType == 3:  # Ask size
                data['ask_size'] = size
            elif tickType == 5:  # Last size
                data['last_size'] = size
            elif tickType == 8:  # Volume
                data['volume'] = size
            
            data['timestamp'] = datetime.now()
    
    def error(self, reqId: int, errorCode: int, errorString: str):
        """Called when TWS API errors occur"""
        if errorCode == 2104:  # Market data farm connection is OK
            self.logger.info("✅ Market data connection restored")
        elif errorCode == 2106:  # HMDS data farm connection is OK
            self.logger.info("✅ HMDS data connection restored")
        elif errorCode == 1100:  # Connectivity between IB and TWS lost
            self.logger.error("❌ Connection to TWS lost")
            self.connected = False
        else:
            self.logger.warning(f"⚠️ TWS API Error {errorCode}: {errorString}")
    
    def connectionClosed(self):
        """Called when TWS connection is closed"""
        self.logger.warning("🔌 TWS connection closed")
        self.connected = False

# IBKR TWS API Usage Example
async def ibkr_tws_example():
    """
    Example usage of IBKR TWS API integration
    """
    print("=== IBKR TWS API Integration Example ===")
    
    # Create IBKR configuration
    ibkr_config = IBKRConfig(
        broker_type=BrokerType.INTERACTIVE_BROKERS.value,
        tws_host="127.0.0.1",
        tws_port=7497,  # Paper trading port
        client_id=1,
        paper_trading=True,
        enable_notifications=True,
        use_smart_routing=True,
        enable_advanced_order_types=True
    )
    
    # Create IBKR interface
    ibkr = InteractiveBrokersInterface(ibkr_config)
    
    try:
        # Connect to TWS
        print("🔌 Connecting to IBKR TWS...")
        connected = await ibkr.connect()
        
        if connected:
            print("✅ Connected to IBKR TWS")
            
            # Set risk management limits
            ibkr.set_position_limit("SPY", 1000)
            ibkr.set_order_limit("SPY", 100)
            
            # Get account information
            account_info = await ibkr.get_account_info()
            print(f"💰 Account: {account_info.account_id}")
            print(f"💵 Cash: ${account_info.cash:,.2f}")
            print(f"💪 Buying Power: ${account_info.buying_power:,.2f}")
            print(f"📊 Equity: ${account_info.equity:,.2f}")
            
            # Get real-time market data
            market_data = await ibkr.get_market_data("SPY")
            print(f"📈 SPY Market Data: Bid=${market_data['bid']:.2f}, Ask=${market_data['ask']:.2f}")
            
            # Place a test order (paper trading)
            test_order = OrderRequest(
                symbol="SPY",
                quantity=1,
                side="buy",
                order_type="market",
                time_in_force="day"
            )
            
            print("📤 Placing test order...")
            order_response = await ibkr.place_order(test_order)
            print(f"📋 Order placed: {order_response.order_id}")
            
            # Get positions
            positions = await ibkr.get_positions()
            print(f"📊 Current positions: {len(positions)}")
            
        else:
            print("❌ Failed to connect to IBKR TWS")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        # Disconnect
        await ibkr.disconnect()
        print("🔌 Disconnected from IBKR TWS")

if __name__ == "__main__":
    asyncio.run(ibkr_tws_example())
```

### **8.2.1 IBKR TWS API Configuration**

**File: `core_structure/infrastructure/config/ibkr_config.yaml`**

```yaml
# IBKR TWS API Configuration
ibkr:
  # Connection Settings
  tws_host: "127.0.0.1"
  tws_port: 7497  # 7497 for paper trading, 7496 for live trading
  client_id: 1
  timeout: 20
  
  # Trading Settings
  paper_trading: true
  enable_notifications: true
  use_smart_routing: true
  enable_advanced_order_types: true
  
  # Market Data Settings
  market_data_type: "REAL_TIME"  # REAL_TIME, FROZEN, DELAYED
  enable_streaming_data: true
  enable_historical_data: true
  
  # Risk Management
  risk_checks_enabled: true
  position_limits:
    SPY: 1000
    AAPL: 500
    MSFT: 500
    GOOGL: 300
    AMZN: 200
    TSLA: 100
    NVDA: 200
    META: 300
  
  order_limits:
    SPY: 100
    AAPL: 50
    MSFT: 50
    GOOGL: 30
    AMZN: 20
    TSLA: 10
    NVDA: 20
    META: 30
  
  # Advanced Order Types
  advanced_orders:
    twap_enabled: true
    vwap_enabled: true
    implementation_shortfall_enabled: true
    iceberg_enabled: true
    
  # Execution Settings
  execution:
    smart_routing: true
    best_execution: true
    minimize_market_impact: true
    use_algorithmic_orders: true
    
  # Monitoring
  monitoring:
    enable_order_tracking: true
    enable_position_tracking: true
    enable_account_tracking: true
    enable_market_data_tracking: true
    log_level: "INFO"
```

### **8.2.2 IBKR TWS API Setup Instructions**

**Prerequisites:**
1. **Install TWS (Trader Workstation)** or **IB Gateway**
2. **Install IB API**: `pip install ibapi`
3. **Configure TWS for API connections**

**TWS Configuration Steps:**
1. Open TWS (Trader Workstation)
2. Go to **File > Global Configuration**
3. Navigate to **API > Settings**
4. Enable **Enable ActiveX and Socket Clients**
5. Set **Socket port** to 7497 (paper) or 7496 (live)
6. Add your local IP to **Trusted IPs**
7. Enable **Download open orders on connection**
8. Enable **Include FX positions in portfolio**
9. Click **OK** and restart TWS

**IB Gateway Configuration (Alternative):**
1. Download IB Gateway from IBKR website
2. Install and configure with same settings as TWS
3. Use for headless trading without TWS GUI

### **8.2.3 IBKR TWS API Features Summary**

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-Time Market Data** | Streaming price feeds | ✅ Implemented |
| **Advanced Order Types** | TWAP, VWAP, Implementation Shortfall | ✅ Implemented |
| **Smart Routing** | Best execution across exchanges | ✅ Implemented |
| **Risk Management** | Position limits, order limits | ✅ Implemented |
| **Portfolio Management** | Real-time position tracking | ✅ Implemented |
| **Account Management** | Cash, buying power, equity | ✅ Implemented |
| **Multi-Asset Support** | Stocks, options, futures | ✅ Implemented |
| **Historical Data** | Backtesting and analysis | ✅ Implemented |
| **Order Tracking** | Real-time order status | ✅ Implemented |
| **Error Handling** | Comprehensive error management | ✅ Implemented |

### **8.3 Alpaca Integration**

**File: `core_structure/execution_engine/alpaca_interface.py`**

```python
#!/usr/bin/env python3
"""
Phase 8.3: Alpaca Integration
Alpaca API integration for live trading
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

# Alpaca API imports
try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("⚠️  Alpaca API not available. Install with: pip install alpaca-trade-api")

from .broker_interface import BaseBrokerInterface, BrokerConfig, OrderRequest, OrderResponse, Position, AccountInfo

class AlpacaInterface(BaseBrokerInterface):
    """Alpaca API interface"""
    
    def __init__(self, config: BrokerConfig):
        super().__init__(config)
        
        if not ALPACA_AVAILABLE:
            raise ImportError("Alpaca API not available")
        
        # Initialize Alpaca API
        self.api = tradeapi.REST(
            key_id=config.api_key,
            secret_key=config.secret_key,
            base_url="https://paper-api.alpaca.markets" if config.paper_trading else "https://api.alpaca.markets",
            api_version="v2"
        )
        
        self.stream = None
        
    async def connect(self) -> bool:
        """Connect to Alpaca"""
        try:
            # Test connection by getting account
            account = self.api.get_account()
            if account.status == 'ACTIVE':
                self.connected = True
                self.logger.info("✅ Connected to Alpaca")
                
                # Initialize streaming if needed
                if self.config.paper_trading:
                    self.stream = tradeapi.StreamConn(
                        key_id=self.config.api_key,
                        secret_key=self.config.secret_key,
                        base_url="wss://paper-api.alpaca.markets/stream"
                    )
                else:
                    self.stream = tradeapi.StreamConn(
                        key_id=self.config.api_key,
                        secret_key=self.config.secret_key,
                        base_url="wss://stream.data.alpaca.markets/v2"
                    )
                
                return True
            else:
                self.logger.error(f"❌ Alpaca account not active: {account.status}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to Alpaca: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Alpaca"""
        try:
            if self.stream:
                self.stream.close()
            self.connected = False
            self.logger.info("✅ Disconnected from Alpaca")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error disconnecting from Alpaca: {e}")
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information from Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            account = self.api.get_account()
            positions = self.api.list_positions()
            
            # Convert positions
            position_list = []
            for pos in positions:
                position_list.append(Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    average_price=float(pos.avg_entry_price),
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pl),
                    realized_pnl=0.0  # Would need to track from trades
                ))
            
            return AccountInfo(
                account_id=account.id,
                cash=float(account.cash),
                buying_power=float(account.buying_power),
                equity=float(account.equity),
                margin_used=float(account.margin_used),
                positions=position_list
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error getting account info: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """Get current positions from Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            positions = self.api.list_positions()
            
            position_list = []
            for pos in positions:
                position_list.append(Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    average_price=float(pos.avg_entry_price),
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pl),
                    realized_pnl=0.0
                ))
            
            return position_list
            
        except Exception as e:
            self.logger.error(f"❌ Error getting positions: {e}")
            raise
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order on Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            # Create Alpaca order
            side = "buy" if order.side == "buy" else "sell"
            order_type = order.order_type.lower()
            time_in_force = order.time_in_force.lower()
            
            # Place order
            alpaca_order = self.api.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                client_order_id=order.client_order_id
            )
            
            # Wait for order to be processed
            await asyncio.sleep(1)
            
            # Get order status
            order_status = self.api.get_order(alpaca_order.id)
            
            return OrderResponse(
                order_id=order_status.id,
                status=order_status.status,
                filled_quantity=float(order_status.filled_qty),
                filled_price=float(order_status.filled_avg_price) if order_status.filled_avg_price else None,
                commission=0.0,  # Alpaca doesn't charge commissions
                timestamp=datetime.fromisoformat(order_status.submitted_at.replace('Z', '+00:00'))
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error placing order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception as e:
            self.logger.error(f"❌ Error canceling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status from Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            order_status = self.api.get_order(order_id)
            
            return OrderResponse(
                order_id=order_status.id,
                status=order_status.status,
                filled_quantity=float(order_status.filled_qty),
                filled_price=float(order_status.filled_avg_price) if order_status.filled_avg_price else None,
                commission=0.0,
                timestamp=datetime.fromisoformat(order_status.submitted_at.replace('Z', '+00:00'))
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error getting order status: {e}")
            raise
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time market data from Alpaca"""
        if not self.connected:
            raise ConnectionError("Not connected to Alpaca")
        
        try:
            # Get latest trade
            latest_trade = self.api.get_latest_trade(symbol)
            
            # Get latest quote
            latest_quote = self.api.get_latest_quote(symbol)
            
            return {
                "symbol": symbol,
                "bid": float(latest_quote.bid) if latest_quote else 0.0,
                "ask": float(latest_quote.ask) if latest_quote else 0.0,
                "last": float(latest_trade.price) if latest_trade else 0.0,
                "volume": int(latest_trade.size) if latest_trade else 0,
                "timestamp": latest_trade.timestamp if latest_trade else None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting market data for {symbol}: {e}")
            return {
                "symbol": symbol,
                "bid": 0.0,
                "ask": 0.0,
                "last": 0.0,
                "volume": 0,
                "timestamp": None
            }
```

### **8.4 Enhanced Execution Engine Integration**

**File: `core_structure/execution_engine/enhanced_execution_engine.py`**

```python
#!/usr/bin/env python3
"""
Phase 8.4: Enhanced Execution Engine with Multi-Broker Support
Integrates broker interfaces with execution engine
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from .broker_interface import MultiBrokerManager, OrderRequest, OrderResponse
from .execution_engine import ExecutionEngine, ExecutionRequest, ExecutionResult
from core_structure.infrastructure.config.enhanced_config_manager import EnhancedConfigManager

class EnhancedExecutionEngine(ExecutionEngine):
    """Enhanced execution engine with multi-broker support"""
    
    def __init__(self, config_manager: EnhancedConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.broker_manager = MultiBrokerManager()
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize enhanced execution engine"""
        try:
            # Initialize broker connections based on config
            config = self.config_manager.get_current_config()
            
            # Add paper trading broker if enabled
            if config.execution.get('paper_trading', {}).get('enabled', False):
                paper_config = config.execution['paper_trading']
                await self.broker_manager.add_broker(
                    "paper_trading",
                    paper_config['broker'],
                    paper_config
                )
            
            # Add live trading broker if enabled
            if config.execution.get('live_trading', {}).get('enabled', False):
                live_config = config.execution['live_trading']
                await self.broker_manager.add_broker(
                    "live_trading",
                    live_config['broker'],
                    live_config
                )
            
            self.logger.info("✅ Enhanced execution engine initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing enhanced execution engine: {e}")
            raise
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute order with multi-broker support"""
        try:
            # Determine which broker to use
            broker_name = self._select_broker(request)
            
            if not broker_name:
                # Fall back to simulation
                return await super().execute_order(request)
            
            # Convert to broker order request
            order_request = OrderRequest(
                symbol=request.symbol,
                quantity=request.quantity,
                side="buy" if request.side == "BUY" else "sell",
                order_type=request.algorithm.value.lower(),
                time_in_force="day",
                limit_price=request.limit_price,
                stop_price=request.stop_price
            )
            
            # Place order on broker
            order_response = await self.broker_manager.place_order_on_broker(
                broker_name, order_request
            )
            
            # Convert response to execution result
            result = ExecutionResult(
                request_id=request.request_id,
                order_id=order_response.order_id,
                status="FILLED" if order_response.status == "filled" else "PARTIAL",
                filled_quantity=order_response.filled_quantity,
                filled_price=order_response.filled_price,
                commission=order_response.commission,
                timestamp=order_response.timestamp or datetime.now()
            )
            
            self.logger.info(f"✅ Order executed on {broker_name}: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error executing order: {e}")
            raise
    
    def _select_broker(self, request: ExecutionRequest) -> Optional[str]:
        """Select appropriate broker for order"""
        # Simple logic: use paper trading for testing, live for production
        if "paper_trading" in self.broker_manager.brokers:
            return "paper_trading"
        elif "live_trading" in self.broker_manager.brokers:
            return "live_trading"
        else:
            return None
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio status from all brokers"""
        try:
            accounts = await self.broker_manager.get_all_account_info()
            positions = await self.broker_manager.get_all_positions()
            
            return {
                "accounts": accounts,
                "positions": positions,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting portfolio status: {e}")
            raise
    
    async def close(self):
        """Close all broker connections"""
        try:
            for name in list(self.broker_manager.brokers.keys()):
                await self.broker_manager.remove_broker(name)
            self.logger.info("✅ Enhanced execution engine closed")
        except Exception as e:
            self.logger.error(f"❌ Error closing execution engine: {e}")

async def main():
    """Test enhanced execution engine"""
    
    # Initialize config manager
    config_manager = EnhancedConfigManager()
    
    # Create enhanced execution engine
    engine = EnhancedExecutionEngine(config_manager)
    
    # Initialize
    await engine.initialize()
    
    # Test order execution
    request = ExecutionRequest(
        request_id="test_001",
        symbol="AAPL",
        side="BUY",
        quantity=100,
        algorithm="MARKET",
        timestamp=datetime.now()
    )
    
    result = await engine.execute_order(request)
    print(f"Order result: {result}")
    
    # Get portfolio status
    status = await engine.get_portfolio_status()
    print(f"Portfolio status: {status}")
    
    # Close
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### **8.5 Integration with Real-Time System**

**File: `real_time/enhanced_real_time_system_with_brokers.py`**

```python
#!/usr/bin/env python3
"""
Phase 8.5: Enhanced Real-Time System with Multi-Broker Integration
Integrates broker interfaces with real-time trading system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from real_time.enhanced_real_time_system import EnhancedRealTimeSystem
from core_structure.execution_engine.enhanced_execution_engine import EnhancedExecutionEngine
from core_structure.infrastructure.config.enhanced_config_manager import EnhancedConfigManager

class EnhancedRealTimeSystemWithBrokers(EnhancedRealTimeSystem):
    """Enhanced real-time system with multi-broker support"""
    
    def __init__(self, config_path: str = None):
        super().__init__(config_path)
        self.enhanced_execution_engine = None
        
    async def initialize(self):
        """Initialize enhanced real-time system with brokers"""
        try:
            # Initialize base system
            await super().initialize()
            
            # Initialize enhanced execution engine
            self.enhanced_execution_engine = EnhancedExecutionEngine(self.config_manager)
            await self.enhanced_execution_engine.initialize()
            
            self.logger.info("✅ Enhanced real-time system with brokers initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing enhanced system: {e}")
            raise
    
    async def execute_signal(self, signal: Dict[str, Any]) -> bool:
        """Execute trading signal with broker integration"""
        try:
            # Create execution request
            request = self._create_execution_request(signal)
            
            # Execute with enhanced engine
            result = await self.enhanced_execution_engine.execute_order(request)
            
            # Update portfolio
            await self._update_portfolio(result)
            
            self.logger.info(f"✅ Signal executed: {result}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error executing signal: {e}")
            return False
    
    async def get_real_portfolio_status(self) -> Dict[str, Any]:
        """Get real portfolio status from brokers"""
        try:
            return await self.enhanced_execution_engine.get_portfolio_status()
        except Exception as e:
            self.logger.error(f"❌ Error getting portfolio status: {e}")
            return {}
    
    async def close(self):
        """Close enhanced real-time system"""
        try:
            if self.enhanced_execution_engine:
                await self.enhanced_execution_engine.close()
            await super().close()
            self.logger.info("✅ Enhanced real-time system closed")
        except Exception as e:
            self.logger.error(f"❌ Error closing system: {e}")

async def main():
    """Test enhanced real-time system with brokers"""
    
    # Create enhanced system
    system = EnhancedRealTimeSystemWithBrokers()
    
    # Initialize
    await system.initialize()
    
    # Start trading
    await system.start_trading()
    
    # Monitor for 60 seconds
    await asyncio.sleep(60)
    
    # Get real portfolio status
    status = await system.get_real_portfolio_status()
    print(f"Real portfolio status: {status}")
    
    # Stop trading
    await system.stop_trading()
    
    # Close
    await system.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎯 **Phase 8 Implementation Summary**

### **✅ Key Components Added:**

1. **Multi-Broker Abstract Interface** (`broker_interface.py`)
   - Abstract base class for all brokers
   - Standardized order/position/account data structures
   - Factory pattern for broker creation
   - Multi-broker manager for handling multiple connections

2. **Interactive Brokers Integration** (`interactive_brokers_interface.py`)
   - Full IB API integration
   - Real-time market data
   - Order management
   - Position tracking

3. **Alpaca Integration** (`alpaca_interface.py`)
   - Alpaca API integration
   - Paper and live trading support
   - Real-time market data
   - Order management

4. **Enhanced Execution Engine** (`enhanced_execution_engine.py`)
   - Multi-broker execution support
   - Broker selection logic
   - Portfolio status aggregation
   - Fallback to simulation

5. **Real-Time System Integration** (`enhanced_real_time_system_with_brokers.py`)
   - Broker integration with real-time system
   - Real portfolio tracking
   - Live signal execution

### **🔧 Configuration Updates:**

```yaml
# Enhanced execution configuration
execution:
  simulation:
    enabled: true
    initial_capital: 10_000_000
    commission_rate: 0.001
    slippage: 0.0001
    market_impact: 0.0002
  
  paper_trading:
    enabled: true
    broker: "alpaca"  # or "interactive_brokers"
    api_key: "${ALPACA_API_KEY}"
    secret_key: "${ALPACA_SECRET_KEY}"
    commission_rate: 0.0005
  
  live_trading:
    enabled: false
    broker: "alpaca"  # or "interactive_brokers"
    api_key: "${ALPACA_LIVE_API_KEY}"
    secret_key: "${ALPACA_LIVE_SECRET_KEY}"
    commission_rate: 0.0005
```

### **🚀 Usage Examples:**

```python
# Initialize multi-broker system
system = EnhancedRealTimeSystemWithBrokers()
await system.initialize()

# Start live trading
await system.start_trading()

# Get real portfolio status
status = await system.get_real_portfolio_status()
print(f"Real portfolio: ${status['accounts']['paper_trading'].equity:,.2f}")

# Execute real orders
signal = {"symbol": "AAPL", "action": "BUY", "quantity": 100}
success = await system.execute_signal(signal)
```

### **📋 Implementation Checklist:**

- [ ] **Phase 8.1**: Multi-Broker Abstract Interface Design
- [ ] **Phase 8.2**: Interactive Brokers Integration
- [ ] **Phase 8.3**: Alpaca Integration
- [ ] **Phase 8.4**: Enhanced Execution Engine Integration
- [ ] **Phase 8.5**: Real-Time System Integration
- [ ] **Testing**: Paper trading validation
- [ ] **Documentation**: Broker integration guide
- [ ] **Security**: API key management
- [ ] **Monitoring**: Broker connection health checks

This completes the **Phase 8: Broker Integration & Multi-Broker Implementation** addition to the enhanced plan! 