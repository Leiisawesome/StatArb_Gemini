"""
Bottleneck Analysis
===================

Comprehensive analysis of trading system performance bottlenecks.

Analysis:
1. Component-level profiling
2. Integration overhead analysis
3. Async operation overhead
4. Hot path identification
5. Optimization recommendations
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance.profiler import PerformanceProfiler, benchmark_function
from tests.performance.memory_profiler import MemoryProfiler


@dataclass
class BottleneckReport:
    """Bottleneck analysis report"""
    component: str
    avg_latency_ms: float
    p99_latency_ms: float
    ops_per_second: float
    memory_delta_mb: float
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    recommendation: str
    estimated_improvement: str


class BottleneckAnalyzer:
    """
    Analyze performance bottlenecks in the trading system
    """
    
    def __init__(self):
        self.reports: List[BottleneckReport] = []
        self.baseline = {
            'latency_target_ms': 70,
            'throughput_target_ops': 32,
            'memory_target_mb': 30
        }
    
    def add_report(self, report: BottleneckReport):
        """Add a bottleneck report"""
        self.reports.append(report)
    
    def analyze_component(self, name: str, func, iterations: int = 1000) -> BottleneckReport:
        """
        Analyze a single component
        
        Args:
            name: Component name
            func: Function to analyze
            iterations: Number of iterations
        
        Returns:
            BottleneckReport
        """
        # Benchmark
        results = benchmark_function(func, iterations=iterations)
        
        # Determine severity
        if results['avg_time_ms'] > 50:
            severity = 'CRITICAL'
            recommendation = f"URGENT: {name} is very slow ({results['avg_time_ms']:.1f}ms). Immediate optimization required."
            estimated_improvement = "50-70% reduction possible"
        elif results['avg_time_ms'] > 10:
            severity = 'HIGH'
            recommendation = f"High priority: {name} contributes significantly to latency. Should optimize."
            estimated_improvement = "30-50% reduction possible"
        elif results['avg_time_ms'] > 1:
            severity = 'MEDIUM'
            recommendation = f"Medium priority: {name} has moderate overhead. Optimize if time permits."
            estimated_improvement = "20-30% reduction possible"
        else:
            severity = 'LOW'
            recommendation = f"Low priority: {name} is already fast. No immediate action needed."
            estimated_improvement = "Minimal improvement expected"
        
        report = BottleneckReport(
            component=name,
            avg_latency_ms=results['avg_time_ms'],
            p99_latency_ms=results['p99_time_ms'],
            ops_per_second=results['ops_per_second'],
            memory_delta_mb=results.get('avg_memory_delta_mb', 0),
            severity=severity,
            recommendation=recommendation,
            estimated_improvement=estimated_improvement
        )
        
        self.add_report(report)
        return report
    
    async def analyze_async_component(self, name: str, func, iterations: int = 100) -> BottleneckReport:
        """
        Analyze an async component
        
        Args:
            name: Component name
            func: Async function to analyze
            iterations: Number of iterations
        
        Returns:
            BottleneckReport
        """
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            end = time.perf_counter()
            times.append(end - start)
        
        times_sorted = sorted(times)
        n = len(times_sorted)
        
        avg_ms = sum(times) / n * 1000
        p99_ms = times_sorted[int(n * 0.99)] * 1000
        ops_per_sec = n / sum(times) if sum(times) > 0 else 0
        
        # Determine severity
        if avg_ms > 50:
            severity = 'CRITICAL'
            recommendation = f"URGENT: {name} has severe async overhead ({avg_ms:.1f}ms). Consider sync alternative or optimize async handling."
            estimated_improvement = "60-80% reduction with proper optimization"
        elif avg_ms > 10:
            severity = 'HIGH'
            recommendation = f"High priority: {name} has significant async overhead. Optimize async patterns."
            estimated_improvement = "40-60% reduction possible"
        elif avg_ms > 1:
            severity = 'MEDIUM'
            recommendation = f"Medium priority: {name} has moderate async overhead. Review async usage."
            estimated_improvement = "20-40% reduction possible"
        else:
            severity = 'LOW'
            recommendation = f"Low priority: {name} async overhead is acceptable."
            estimated_improvement = "Minimal improvement expected"
        
        report = BottleneckReport(
            component=name,
            avg_latency_ms=avg_ms,
            p99_latency_ms=p99_ms,
            ops_per_second=ops_per_sec,
            memory_delta_mb=0,
            severity=severity,
            recommendation=recommendation,
            estimated_improvement=estimated_improvement
        )
        
        self.add_report(report)
        return report
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary"""
        critical = [r for r in self.reports if r.severity == 'CRITICAL']
        high = [r for r in self.reports if r.severity == 'HIGH']
        medium = [r for r in self.reports if r.severity == 'MEDIUM']
        low = [r for r in self.reports if r.severity == 'LOW']
        
        total_latency = sum(r.avg_latency_ms for r in self.reports)
        
        summary = {
            'total_components': len(self.reports),
            'critical_issues': len(critical),
            'high_priority': len(high),
            'medium_priority': len(medium),
            'low_priority': len(low),
            'total_latency_ms': total_latency,
            'target_latency_ms': self.baseline['latency_target_ms'],
            'gap_to_target_ms': total_latency - self.baseline['latency_target_ms'],
            'requires_optimization': total_latency > self.baseline['latency_target_ms'],
            'critical_components': [r.component for r in critical],
            'high_priority_components': [r.component for r in high]
        }
        
        return summary
    
    def print_report(self):
        """Print comprehensive bottleneck report"""
        print("\n" + "="*80)
        print("BOTTLENECK ANALYSIS REPORT")
        print("="*80)
        print(f"\nGenerated: {datetime.now().isoformat()}")
        
        summary = self.generate_summary()
        
        print(f"\n📊 SUMMARY")
        print("-"*80)
        print(f"Total Components Analyzed:  {summary['total_components']}")
        print(f"Total Latency:              {summary['total_latency_ms']:.2f} ms")
        print(f"Target Latency:             {summary['target_latency_ms']:.2f} ms")
        print(f"Gap to Target:              {summary['gap_to_target_ms']:+.2f} ms")
        print()
        print(f"🔴 Critical Issues:         {summary['critical_issues']}")
        print(f"🟠 High Priority:           {summary['high_priority']}")
        print(f"🟡 Medium Priority:         {summary['medium_priority']}")
        print(f"🟢 Low Priority:            {summary['low_priority']}")
        
        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        sorted_reports = sorted(self.reports, key=lambda r: (severity_order[r.severity], -r.avg_latency_ms))
        
        print(f"\n📋 DETAILED FINDINGS")
        print("-"*80)
        
        for i, report in enumerate(sorted_reports, 1):
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }
            
            print(f"\n{i}. {severity_emoji[report.severity]} {report.component.upper()}")
            print(f"   Severity:     {report.severity}")
            print(f"   Avg Latency:  {report.avg_latency_ms:.3f} ms")
            print(f"   P99 Latency:  {report.p99_latency_ms:.3f} ms")
            print(f"   Throughput:   {report.ops_per_second:.1f} ops/sec")
            print(f"   Memory:       {report.memory_delta_mb:+.3f} MB")
            print(f"   📝 Recommendation: {report.recommendation}")
            print(f"   📈 Potential Gain: {report.estimated_improvement}")
        
        print(f"\n🎯 OPTIMIZATION PRIORITY")
        print("-"*80)
        
        if summary['critical_issues'] > 0:
            print(f"\n⚠️  CRITICAL: Address {summary['critical_issues']} critical issue(s) immediately:")
            for comp in summary['critical_components']:
                report = next(r for r in self.reports if r.component == comp)
                print(f"   • {comp}: {report.avg_latency_ms:.1f}ms → Target: <10ms")
        
        if summary['high_priority'] > 0:
            print(f"\n🔶 HIGH: Optimize {summary['high_priority']} high-priority component(s):")
            for comp in summary['high_priority_components']:
                report = next(r for r in self.reports if r.component == comp)
                print(f"   • {comp}: {report.avg_latency_ms:.1f}ms → Target: <5ms")
        
        print(f"\n💡 KEY INSIGHTS")
        print("-"*80)
        
        # Calculate potential improvement
        critical_high_latency = sum(
            r.avg_latency_ms for r in self.reports 
            if r.severity in ['CRITICAL', 'HIGH']
        )
        
        if critical_high_latency > 0:
            potential_reduction = critical_high_latency * 0.5  # Assume 50% reduction
            new_latency = summary['total_latency_ms'] - potential_reduction
            
            print(f"   • Current Total Latency: {summary['total_latency_ms']:.1f}ms")
            print(f"   • Critical+High Latency: {critical_high_latency:.1f}ms")
            print(f"   • Potential Reduction:   {potential_reduction:.1f}ms (50% of Critical+High)")
            print(f"   • Projected Latency:     {new_latency:.1f}ms")
            print(f"   • Target Achievement:    {'✅ YES' if new_latency <= self.baseline['latency_target_ms'] else '❌ NEED MORE OPTIMIZATION'}")
        
        print("\n" + "="*80 + "\n")
    
    def save_report(self, output_dir: Path):
        """Save bottleneck report"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        report_file = output_dir / f"bottleneck_analysis_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': self.generate_summary(),
                'reports': [asdict(r) for r in self.reports]
            }, f, indent=2)
        
        print(f"✅ Report saved to {report_file}")


def run_bottleneck_analysis():
    """Run comprehensive bottleneck analysis"""
    
    print("\n" + "="*80)
    print("STARTING COMPREHENSIVE BOTTLENECK ANALYSIS")
    print("="*80)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Target: 70ms average latency")
    
    analyzer = BottleneckAnalyzer()
    
    # Import after setting up path
    from tests.load_testing.mock_trading_system import (
        MockMarketData, MockRiskManager, MockPositionTracker
    )
    from tests.load_testing.order_generator import OrderGenerator, OrderGeneratorConfig, OrderPattern
    
    market_data = MockMarketData()
    risk_manager = MockRiskManager()
    position_tracker = MockPositionTracker()
    
    print("\n📊 Analyzing Components...")
    print("-"*80)
    
    # 1. Market Data
    print("\n1️⃣  Analyzing: Market Data Operations")
    def test_market_data():
        prices = {}
        for symbol in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']:
            prices[symbol] = market_data.get_price(symbol)
        return prices
    
    analyzer.analyze_component("market_data", test_market_data, iterations=1000)
    
    # 2. Order Generation
    print("2️⃣  Analyzing: Order Generation")
    def test_order_generation():
        config = OrderGeneratorConfig(
            symbols=['AAPL', 'GOOGL', 'MSFT'],
            pattern=OrderPattern.RANDOM
        )
        generator = OrderGenerator(config)
        return generator.generate_orders(10)
    
    analyzer.analyze_component("order_generation", test_order_generation, iterations=100)
    
    # 3. Position Tracking
    print("3️⃣  Analyzing: Position Tracking")
    def test_position_tracking():
        for symbol in ['AAPL', 'GOOGL', 'MSFT']:
            position_tracker.update_position(symbol, 100, market_data.get_price(symbol))
        return position_tracker.get_summary()
    
    analyzer.analyze_component("position_tracking", test_position_tracking, iterations=500)
    
    # 4. Async Risk Check (This is where overhead likely exists)
    print("4️⃣  Analyzing: Async Risk Management")
    async def test_risk_check():
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'price': market_data.get_price('AAPL'),
            'order_type': 'LIMIT'
        }
        return await risk_manager.check_order(order, current_position=0, total_exposure=0.0)
    
    asyncio.run(analyzer.analyze_async_component("async_risk_check", test_risk_check, iterations=200))
    
    # 5. Sleep Simulation (Common in async code)
    print("5️⃣  Analyzing: Async Sleep Overhead")
    async def test_async_sleep():
        await asyncio.sleep(0.001)  # 1ms sleep
        return True
    
    asyncio.run(analyzer.analyze_async_component("async_sleep_1ms", test_async_sleep, iterations=100))
    
    # 6. Integration Overhead (Multiple async calls)
    print("6️⃣  Analyzing: Integration Overhead")
    async def test_integration():
        # Simulate multiple async operations
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'price': market_data.get_price('AAPL'),
            'order_type': 'LIMIT'
        }
        
        # Multiple async calls (simulating order pipeline)
        await risk_manager.check_order(order, 0, 0.0)
        await asyncio.sleep(0.002)  # Simulate routing delay
        await asyncio.sleep(0.005)  # Simulate execution delay
        
        return True
    
    asyncio.run(analyzer.analyze_async_component("integration_overhead", test_integration, iterations=100))
    
    print("\n✅ Analysis Complete!")
    
    # Generate and print report
    analyzer.print_report()
    
    # Save report
    output_dir = Path(__file__).parent.parent.parent / "benchmark_results"
    analyzer.save_report(output_dir)
    
    return analyzer


if __name__ == '__main__':
    analyzer = run_bottleneck_analysis()
    
    print("\n🎯 NEXT STEPS:")
    summary = analyzer.generate_summary()
    
    if summary['critical_issues'] > 0:
        print(f"   1. Address {summary['critical_issues']} CRITICAL bottleneck(s) immediately")
    if summary['high_priority'] > 0:
        print(f"   2. Optimize {summary['high_priority']} HIGH-priority component(s)")
    if summary['requires_optimization']:
        print(f"   3. Continue optimization until target <{analyzer.baseline['latency_target_ms']}ms achieved")
    else:
        print("   ✅ System meets performance targets!")
    
    print("\n" + "="*80)
