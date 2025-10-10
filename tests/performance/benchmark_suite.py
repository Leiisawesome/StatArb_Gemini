"""
Benchmark Suite
===============

Comprehensive benchmarking for trading system components.

Benchmarks:
1. Order generation and validation
2. Market data processing
3. Signal generation
4. Risk management checks
5. Position tracking
6. Portfolio calculations
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Callable
import json
from datetime import datetime
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance.profiler import benchmark_function, print_benchmark_results
from tests.performance.memory_profiler import MemoryProfiler


class BenchmarkSuite:
    """
    Comprehensive benchmark suite for trading system
    """
    
    def __init__(self, name: str = "trading_system"):
        self.name = name
        self.results = {}
        self.baseline = None
    
    def add_benchmark(self, name: str, func: Callable, iterations: int = 100, warmup: int = 10):
        """
        Add a benchmark to the suite
        
        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations
        """
        print(f"\n🏃 Running benchmark: {name}...")
        results = benchmark_function(func, iterations=iterations, warmup=warmup)
        self.results[name] = results
        print(f"   ✅ Avg: {results['avg_time_ms']:.3f} ms, P99: {results['p99_time_ms']:.3f} ms")
    
    def run_all(self, benchmarks: List[tuple]):
        """
        Run all benchmarks
        
        Args:
            benchmarks: List of (name, func, iterations, warmup) tuples
        """
        print("\n" + "="*80)
        print(f"RUNNING BENCHMARK SUITE: {self.name}")
        print("="*80)
        
        for benchmark in benchmarks:
            name = benchmark[0]
            func = benchmark[1]
            iterations = benchmark[2] if len(benchmark) > 2 else 100
            warmup = benchmark[3] if len(benchmark) > 3 else 10
            
            self.add_benchmark(name, func, iterations, warmup)
        
        print("\n" + "="*80)
        print("BENCHMARK SUITE COMPLETE")
        print("="*80)
    
    def save_baseline(self, output_dir: Path):
        """Save current results as baseline"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        baseline_file = output_dir / f"{self.name}_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump({
                'name': self.name,
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, indent=2)
        
        print(f"\n✅ Baseline saved to {baseline_file}")
        self.baseline = self.results.copy()
    
    def load_baseline(self, baseline_file: Path):
        """Load baseline for comparison"""
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                self.baseline = data.get('results', {})
            print(f"✅ Loaded baseline from {baseline_file}")
        else:
            print(f"⚠️  Baseline file not found: {baseline_file}")
    
    def compare_to_baseline(self) -> Dict[str, Any]:
        """
        Compare current results to baseline
        
        Returns:
            Comparison results
        """
        if not self.baseline:
            return {'error': 'No baseline loaded'}
        
        comparisons = {}
        
        for name, current in self.results.items():
            if name not in self.baseline:
                continue
            
            baseline = self.baseline[name]
            
            improvement_pct = (
                (baseline['avg_time_ms'] - current['avg_time_ms']) / baseline['avg_time_ms'] * 100
            )
            
            comparisons[name] = {
                'baseline_avg_ms': baseline['avg_time_ms'],
                'current_avg_ms': current['avg_time_ms'],
                'improvement_pct': improvement_pct,
                'baseline_p99_ms': baseline['p99_time_ms'],
                'current_p99_ms': current['p99_time_ms'],
                'p99_improvement_pct': (
                    (baseline['p99_time_ms'] - current['p99_time_ms']) / baseline['p99_time_ms'] * 100
                ),
                'status': '✅ IMPROVED' if improvement_pct > 0 else '❌ REGRESSED' if improvement_pct < -5 else '⚖️  SIMILAR'
            }
        
        return comparisons
    
    def print_comparison(self):
        """Print comparison with baseline"""
        if not self.baseline:
            print("⚠️  No baseline to compare against")
            return
        
        comparisons = self.compare_to_baseline()
        
        print("\n" + "="*80)
        print(f"BENCHMARK COMPARISON: {self.name}")
        print("="*80)
        print(f"\n{'Benchmark':<30} {'Baseline':<12} {'Current':<12} {'Change':<12} {'Status':<15}")
        print("-"*80)
        
        total_improvement = 0
        count = 0
        
        for name, comp in comparisons.items():
            print(f"{name:<30} {comp['baseline_avg_ms']:>10.3f}ms {comp['current_avg_ms']:>10.3f}ms {comp['improvement_pct']:>+10.1f}% {comp['status']:<15}")
            total_improvement += comp['improvement_pct']
            count += 1
        
        print("-"*80)
        avg_improvement = total_improvement / count if count > 0 else 0
        print(f"{'AVERAGE IMPROVEMENT':<30} {'':<12} {'':<12} {avg_improvement:>+10.1f}%")
        print("="*80 + "\n")
    
    def save_results(self, output_dir: Path, label: str = None):
        """Save benchmark results"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        label_str = f"_{label}" if label else ""
        
        results_file = output_dir / f"{self.name}_results{label_str}_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'name': self.name,
                'label': label,
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, indent=2)
        
        print(f"✅ Results saved to {results_file}")
    
    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*80)
        print(f"BENCHMARK SUMMARY: {self.name}")
        print("="*80)
        print(f"\n{'Benchmark':<30} {'Avg (ms)':<12} {'P50 (ms)':<12} {'P99 (ms)':<12} {'Ops/s':<12}")
        print("-"*80)
        
        for name, result in self.results.items():
            print(f"{name:<30} {result['avg_time_ms']:>10.3f} {result['p50_time_ms']:>10.3f} {result['p99_time_ms']:>10.3f} {result['ops_per_second']:>10.1f}")
        
        print("="*80 + "\n")


def create_trading_benchmarks() -> List[tuple]:
    """
    Create standard trading system benchmarks
    
    Returns:
        List of benchmark tuples
    """
    
    # Benchmark 1: Order validation
    def benchmark_order_validation():
        """Simulate order validation"""
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'price': 150.50,
            'order_type': 'LIMIT'
        }
        
        # Validate
        valid = (
            order['quantity'] > 0 and
            order['price'] > 0 and
            order['side'] in ['BUY', 'SELL'] and
            len(order['symbol']) > 0
        )
        
        return valid
    
    # Benchmark 2: Market data processing
    def benchmark_market_data():
        """Simulate market data processing"""
        prices = np.random.randn(100) * 10 + 150
        
        # Calculate indicators
        sma = np.mean(prices)
        std = np.std(prices)
        zscore = (prices[-1] - sma) / std if std > 0 else 0
        
        return zscore
    
    # Benchmark 3: Signal generation
    def benchmark_signal_generation():
        """Simulate signal generation"""
        # Generate price series
        prices_a = np.random.randn(50) * 5 + 100
        prices_b = np.random.randn(50) * 5 + 100
        
        # Calculate spread
        spread = prices_a - prices_b
        zscore = (spread[-1] - np.mean(spread)) / np.std(spread)
        
        # Generate signal
        if zscore > 2:
            signal = 'SELL'
        elif zscore < -2:
            signal = 'BUY'
        else:
            signal = 'HOLD'
        
        return signal
    
    # Benchmark 4: Risk check
    def benchmark_risk_check():
        """Simulate risk check"""
        position = 5000
        price = 150.50
        exposure = position * price
        
        # Risk limits
        max_position = 10000
        max_exposure = 2000000
        
        passed = (
            abs(position) <= max_position and
            abs(exposure) <= max_exposure
        )
        
        return passed
    
    # Benchmark 5: Portfolio calculation
    def benchmark_portfolio_calc():
        """Simulate portfolio calculations"""
        positions = np.array([100, -50, 200, -150, 75])
        prices = np.array([150.50, 200.25, 50.75, 100.00, 175.50])
        
        exposures = positions * prices
        total_long = np.sum(exposures[exposures > 0])
        total_short = np.abs(np.sum(exposures[exposures < 0]))
        net_exposure = np.sum(exposures)
        
        return {
            'long': total_long,
            'short': total_short,
            'net': net_exposure
        }
    
    # Benchmark 6: P&L calculation
    def benchmark_pnl_calc():
        """Simulate P&L calculation"""
        entry_price = 150.00
        current_price = 152.50
        quantity = 1000
        
        realized_pnl = 500.00
        unrealized_pnl = (current_price - entry_price) * quantity
        total_pnl = realized_pnl + unrealized_pnl
        
        return total_pnl
    
    benchmarks = [
        ('order_validation', benchmark_order_validation, 1000, 50),
        ('market_data_processing', benchmark_market_data, 1000, 50),
        ('signal_generation', benchmark_signal_generation, 500, 25),
        ('risk_check', benchmark_risk_check, 1000, 50),
        ('portfolio_calculation', benchmark_portfolio_calc, 500, 25),
        ('pnl_calculation', benchmark_pnl_calc, 1000, 50),
    ]
    
    return benchmarks


def run_standard_benchmarks(save_baseline: bool = False, compare: bool = False, output_dir: Path = None):
    """
    Run standard trading system benchmarks
    
    Args:
        save_baseline: Save results as baseline
        compare: Compare to existing baseline
        output_dir: Directory to save results
    """
    suite = BenchmarkSuite("trading_system")
    
    # Load baseline if comparing
    if compare and output_dir:
        baseline_file = output_dir / "trading_system_baseline.json"
        suite.load_baseline(baseline_file)
    
    # Run benchmarks
    benchmarks = create_trading_benchmarks()
    suite.run_all(benchmarks)
    
    # Print summary
    suite.print_summary()
    
    # Compare to baseline
    if compare and suite.baseline:
        suite.print_comparison()
    
    # Save results
    if output_dir:
        if save_baseline:
            suite.save_baseline(output_dir)
        else:
            suite.save_results(output_dir, label="current")
    
    return suite


# Example usage
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run trading system benchmarks')
    parser.add_argument('--baseline', action='store_true', help='Save as baseline')
    parser.add_argument('--compare', action='store_true', help='Compare to baseline')
    parser.add_argument('--output', type=str, default='benchmark_results', help='Output directory')
    
    args = parser.parse_args()
    
    output_dir = Path(__file__).parent.parent.parent / args.output
    
    print("\n" + "="*80)
    print("TRADING SYSTEM BENCHMARK SUITE")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Save Baseline: {args.baseline}")
    print(f"  Compare:       {args.compare}")
    print(f"  Output Dir:    {output_dir}")
    
    suite = run_standard_benchmarks(
        save_baseline=args.baseline,
        compare=args.compare,
        output_dir=output_dir
    )
    
    print("\n✅ Benchmark suite completed!")
