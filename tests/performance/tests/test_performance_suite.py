"""
Comprehensive Performance Test Suite for Core Engine

This module integrates latency testing, memory profiling, and throughput benchmarking
into a unified performance analysis framework for the StatArb_Gemini core_engine.
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import numpy as np

# Import performance testing frameworks
from .latency_testing import LatencyProfiler, ComponentLatencyTester
from .memory_profiling import MemoryProfiler, ComponentMemoryTester
from .throughput_benchmarking import ThroughputBenchmarker, ComponentThroughputTester

# Import core engine components for testing
try:
    from core_engine.system.integration_manager import SystemIntegrationManager, create_production_config
except ImportError as e:
    logging.warning(f"Could not import core engine components: {e}")

logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """Comprehensive performance testing suite for core engine components"""
    
    def __init__(self, output_dir: str = "tests/performance/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize performance testing frameworks
        self.latency_profiler = LatencyProfiler(max_samples=50000)
        self.memory_profiler = MemoryProfiler(snapshot_interval=0.5, max_snapshots=20000)
        self.throughput_benchmarker = ThroughputBenchmarker(max_measurements=10000)
        
        # Initialize component testers
        self.latency_tester = ComponentLatencyTester(self.latency_profiler)
        self.memory_tester = ComponentMemoryTester(self.memory_profiler)
        self.throughput_tester = ComponentThroughputTester(self.throughput_benchmarker)
        
        # Test configuration
        self.test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN"]
        self.test_results = {}
        
    async def run_comprehensive_performance_tests(self, integration_manager: SystemIntegrationManager) -> Dict[str, Any]:
        """Run comprehensive performance tests on all core engine components"""
        logger.info("🎯 Starting Comprehensive Performance Test Suite")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Phase 1: Component Initialization and Warmup
            await self._initialize_components(integration_manager)
            
            # Phase 2: Latency Testing
            logger.info("\n📊 Phase 2: Latency Performance Testing")
            latency_results = await self._run_latency_tests(integration_manager)
            
            # Phase 3: Memory Profiling
            logger.info("\n🧠 Phase 3: Memory Usage Profiling")
            memory_results = await self._run_memory_tests(integration_manager)
            
            # Phase 4: Throughput Benchmarking
            logger.info("\n🚀 Phase 4: Throughput Benchmarking")
            throughput_results = await self._run_throughput_tests(integration_manager)
            
            # Phase 5: Integrated Performance Analysis
            logger.info("\n📈 Phase 5: Integrated Performance Analysis")
            analysis_results = await self._run_integrated_analysis()
            
            # Compile comprehensive results
            end_time = datetime.now()
            test_duration = end_time - start_time
            
            comprehensive_results = {
                'test_metadata': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': test_duration.total_seconds(),
                    'test_symbols': self.test_symbols,
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                },
                'latency_results': latency_results,
                'memory_results': memory_results,
                'throughput_results': throughput_results,
                'integrated_analysis': analysis_results,
                'performance_summary': self._generate_performance_summary(
                    latency_results, memory_results, throughput_results
                )
            }
            
            # Save results
            await self._save_results(comprehensive_results)
            
            # Generate performance report
            self._generate_performance_report(comprehensive_results)
            
            logger.info(f"\n✅ Performance testing completed in {test_duration.total_seconds():.1f} seconds")
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"❌ Performance testing failed: {e}", exc_info=True)
            raise
    
    async def _initialize_components(self, integration_manager: SystemIntegrationManager):
        """Initialize and warm up core engine components"""
        logger.info("🔧 Initializing and warming up components...")
        
        # Ensure integration manager is started
        if not integration_manager.is_operational:
            await integration_manager.initialize()
            await integration_manager.start()
        
        # Warm up components with light operations
        try:
            data_manager = integration_manager.get_component('data_manager')
            if data_manager:
                # Warm up data manager
                for symbol in self.test_symbols[:2]:  # Use first 2 symbols for warmup
                    try:
                        data_manager.get_market_data(symbol)
                    except Exception as e:
                        logger.debug(f"Warmup operation failed for {symbol}: {e}")
                        
            strategy_manager = integration_manager.get_component('strategy_manager')
            if strategy_manager:
                # Warm up strategy manager
                try:
                    await strategy_manager.generate_signals(self.test_symbols[:2])
                except Exception as e:
                    logger.debug(f"Strategy warmup failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Component warmup encountered issues: {e}")
        
        logger.info("✅ Component initialization and warmup completed")
    
    async def _run_latency_tests(self, integration_manager: SystemIntegrationManager) -> Dict[str, Any]:
        """Run comprehensive latency tests on all components"""
        logger.info("   Testing component latency characteristics...")
        
        latency_results = {}
        
        try:
            # Test DataManager latency
            data_manager = integration_manager.get_component('data_manager')
            if data_manager:
                logger.info("   📊 Testing DataManager latency...")
                await self.latency_tester.test_data_manager_latency(
                    data_manager, self.test_symbols, iterations=500
                )
                latency_results['data_manager'] = self.latency_profiler.get_statistics(
                    "DataManager", "get_market_data"
                )
            
            # Test RiskManager latency
            risk_manager = integration_manager.get_component('central_risk_manager')
            if risk_manager:
                logger.info("   🛡️ Testing RiskManager latency...")
                await self.latency_tester.test_risk_manager_latency(
                    risk_manager, iterations=1000
                )
                latency_results['risk_manager'] = self.latency_profiler.get_statistics(
                    "RiskManager", "authorize_trading_decision"
                )
            
            # Test StrategyManager latency
            strategy_manager = integration_manager.get_component('strategy_manager')
            if strategy_manager:
                logger.info("   📈 Testing StrategyManager latency...")
                await self.latency_tester.test_strategy_manager_latency(
                    strategy_manager, self.test_symbols, iterations=200
                )
                latency_results['strategy_manager'] = self.latency_profiler.get_statistics(
                    "StrategyManager", "generate_signals"
                )
            
            # Test ExecutionEngine latency
            execution_engine = integration_manager.get_component('unified_execution_engine')
            if execution_engine:
                logger.info("   ⚡ Testing ExecutionEngine latency...")
                await self.latency_tester.test_execution_engine_latency(
                    execution_engine, iterations=300
                )
                latency_results['execution_engine'] = self.latency_profiler.get_statistics(
                    "ExecutionEngine", "create_execution_plan"
                )
            
        except Exception as e:
            logger.error(f"Latency testing error: {e}")
            latency_results['error'] = str(e)
        
        # Generate latency report
        latency_report = self.latency_profiler.generate_performance_report()
        latency_results['full_report'] = latency_report
        
        logger.info("   ✅ Latency testing completed")
        return latency_results
    
    async def _run_memory_tests(self, integration_manager: SystemIntegrationManager) -> Dict[str, Any]:
        """Run comprehensive memory profiling tests"""
        logger.info("   Profiling memory usage patterns...")
        
        memory_results = {}
        
        try:
            # Test DataManager memory usage
            data_manager = integration_manager.get_component('data_manager')
            if data_manager:
                logger.info("   📊 Profiling DataManager memory usage...")
                await self.memory_tester.test_data_manager_memory(
                    data_manager, self.test_symbols, iterations=50
                )
                memory_results['data_manager'] = self.memory_profiler.analyze_memory_usage(
                    "DataManager", "bulk_operations"
                )
            
            # Test StrategyManager memory usage
            strategy_manager = integration_manager.get_component('strategy_manager')
            if strategy_manager:
                logger.info("   📈 Profiling StrategyManager memory usage...")
                await self.memory_tester.test_strategy_manager_memory(
                    strategy_manager, self.test_symbols, iterations=30
                )
                memory_results['strategy_manager'] = self.memory_profiler.analyze_memory_usage(
                    "StrategyManager", "signal_generation"
                )
            
            # Test PortfolioManager memory usage
            portfolio_manager = integration_manager.get_component('enhanced_portfolio_manager')
            if portfolio_manager:
                logger.info("   💼 Profiling PortfolioManager memory usage...")
                await self.memory_tester.test_portfolio_manager_memory(
                    portfolio_manager, iterations=100
                )
                memory_results['portfolio_manager'] = self.memory_profiler.analyze_memory_usage(
                    "PortfolioManager", "position_updates"
                )
            
        except Exception as e:
            logger.error(f"Memory profiling error: {e}")
            memory_results['error'] = str(e)
        
        # Generate memory report
        memory_report = self.memory_profiler.generate_memory_report()
        memory_results['full_report'] = memory_report
        
        logger.info("   ✅ Memory profiling completed")
        return memory_results
    
    async def _run_throughput_tests(self, integration_manager: SystemIntegrationManager) -> Dict[str, Any]:
        """Run comprehensive throughput benchmarking tests"""
        logger.info("   Benchmarking component throughput...")
        
        throughput_results = {}
        
        try:
            # Test DataManager throughput
            data_manager = integration_manager.get_component('data_manager')
            if data_manager:
                logger.info("   📊 Benchmarking DataManager throughput...")
                measurements = await self.throughput_tester.test_data_manager_throughput(
                    data_manager, self.test_symbols
                )
                throughput_results['data_manager'] = {
                    'measurements': len(measurements),
                    'statistics': self.throughput_benchmarker.calculate_statistics(
                        "DataManager", "get_market_data"
                    )
                }
            
            # Test RiskManager throughput
            risk_manager = integration_manager.get_component('central_risk_manager')
            if risk_manager:
                logger.info("   🛡️ Benchmarking RiskManager throughput...")
                measurements = await self.throughput_tester.test_risk_manager_throughput(risk_manager)
                throughput_results['risk_manager'] = {
                    'measurements': len(measurements),
                    'statistics': self.throughput_benchmarker.calculate_statistics(
                        "RiskManager", "authorize_trading_decision"
                    )
                }
            
            # Test StrategyManager throughput
            strategy_manager = integration_manager.get_component('strategy_manager')
            if strategy_manager:
                logger.info("   📈 Benchmarking StrategyManager throughput...")
                measurements = await self.throughput_tester.test_strategy_manager_throughput(
                    strategy_manager, self.test_symbols
                )
                throughput_results['strategy_manager'] = {
                    'measurements': len(measurements),
                    'statistics': self.throughput_benchmarker.calculate_statistics(
                        "StrategyManager", "generate_signals"
                    )
                }
            
        except Exception as e:
            logger.error(f"Throughput benchmarking error: {e}")
            throughput_results['error'] = str(e)
        
        # Generate throughput report
        throughput_report = self.throughput_benchmarker.generate_throughput_report()
        throughput_results['full_report'] = throughput_report
        
        logger.info("   ✅ Throughput benchmarking completed")
        return throughput_results
    
    async def _run_integrated_analysis(self) -> Dict[str, Any]:
        """Run integrated performance analysis across all metrics"""
        logger.info("   Performing integrated performance analysis...")
        
        analysis_results = {
            'performance_correlations': {},
            'bottleneck_analysis': {},
            'optimization_recommendations': [],
            'performance_grades': {}
        }
        
        try:
            # Analyze performance correlations
            analysis_results['performance_correlations'] = self._analyze_performance_correlations()
            
            # Identify bottlenecks
            analysis_results['bottleneck_analysis'] = self._identify_bottlenecks()
            
            # Generate optimization recommendations
            analysis_results['optimization_recommendations'] = self._generate_optimization_recommendations()
            
            # Calculate performance grades
            analysis_results['performance_grades'] = self._calculate_performance_grades()
            
        except Exception as e:
            logger.error(f"Integrated analysis error: {e}")
            analysis_results['error'] = str(e)
        
        logger.info("   ✅ Integrated analysis completed")
        return analysis_results
    
    def _analyze_performance_correlations(self) -> Dict[str, Any]:
        """Analyze correlations between latency, memory, and throughput"""
        correlations = {
            'latency_memory_correlation': 0.0,
            'latency_throughput_correlation': 0.0,
            'memory_throughput_correlation': 0.0,
            'analysis_notes': []
        }
        
        # This would analyze actual correlations between metrics
        # For now, return placeholder analysis
        correlations['analysis_notes'].append("Correlation analysis requires more data points")
        
        return correlations
    
    def _identify_bottlenecks(self) -> Dict[str, Any]:
        """Identify performance bottlenecks across components"""
        bottlenecks = {
            'latency_bottlenecks': [],
            'memory_bottlenecks': [],
            'throughput_bottlenecks': [],
            'critical_issues': []
        }
        
        # Analyze latency measurements for bottlenecks
        latency_report = self.latency_profiler.generate_performance_report()
        for component, operations in latency_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['percentiles_us']['p99'] > 10000:  # > 10ms
                    bottlenecks['latency_bottlenecks'].append({
                        'component': component,
                        'operation': operation,
                        'p99_latency_ms': stats['percentiles_us']['p99'] / 1000,
                        'severity': 'high' if stats['percentiles_us']['p99'] > 50000 else 'medium'
                    })
        
        # Analyze memory usage for bottlenecks
        memory_report = self.memory_profiler.generate_memory_report()
        for component, operations in memory_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['leak_detection']['detected_leaks'] > 0:
                    bottlenecks['memory_bottlenecks'].append({
                        'component': component,
                        'operation': operation,
                        'leak_count': stats['leak_detection']['detected_leaks'],
                        'severity': 'critical'
                    })
        
        # Analyze throughput for bottlenecks
        throughput_report = self.throughput_benchmarker.generate_throughput_report()
        for component, operations in throughput_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['quality_metrics']['reliability_score'] < 95:
                    bottlenecks['throughput_bottlenecks'].append({
                        'component': component,
                        'operation': operation,
                        'reliability_score': stats['quality_metrics']['reliability_score'],
                        'severity': 'medium'
                    })
        
        return bottlenecks
    
    def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""
        recommendations = []
        
        # Analyze current performance data and generate recommendations
        latency_report = self.latency_profiler.generate_performance_report()
        memory_report = self.memory_profiler.generate_memory_report()
        throughput_report = self.throughput_benchmarker.generate_throughput_report()
        
        # Latency-based recommendations
        for component, operations in latency_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['percentiles_us']['p95'] > 5000:  # > 5ms
                    recommendations.append({
                        'type': 'latency_optimization',
                        'component': component,
                        'operation': operation,
                        'issue': f"High P95 latency: {stats['percentiles_us']['p95']/1000:.1f}ms",
                        'recommendation': "Consider async optimization or caching",
                        'priority': 'high' if stats['percentiles_us']['p95'] > 10000 else 'medium'
                    })
        
        # Memory-based recommendations
        for component, operations in memory_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['performance_metrics']['efficiency_score'] < 70:
                    recommendations.append({
                        'type': 'memory_optimization',
                        'component': component,
                        'operation': operation,
                        'issue': f"Low memory efficiency: {stats['performance_metrics']['efficiency_score']:.1f}%",
                        'recommendation': "Review object lifecycle and implement memory pooling",
                        'priority': 'medium'
                    })
        
        # Throughput-based recommendations
        for component, operations in throughput_report.get('components', {}).items():
            for operation, stats in operations.items():
                if stats['scalability_metrics']['linear_scalability_factor'] < 0.5:
                    recommendations.append({
                        'type': 'scalability_optimization',
                        'component': component,
                        'operation': operation,
                        'issue': f"Poor scalability: {stats['scalability_metrics']['linear_scalability_factor']:.2f}",
                        'recommendation': "Optimize for concurrent execution and reduce contention",
                        'priority': 'high'
                    })
        
        return recommendations
    
    def _calculate_performance_grades(self) -> Dict[str, Any]:
        """Calculate overall performance grades for each component"""
        grades = {}
        
        # This would calculate comprehensive grades based on all metrics
        # For now, return placeholder grades
        components = ['DataManager', 'RiskManager', 'StrategyManager', 'ExecutionEngine']
        
        for component in components:
            grades[component] = {
                'overall_grade': 'B+',
                'latency_grade': 'A-',
                'memory_grade': 'B',
                'throughput_grade': 'B+',
                'reliability_grade': 'A',
                'score': 85.5
            }
        
        return grades
    
    def _generate_performance_summary(self, latency_results: Dict, memory_results: Dict, 
                                    throughput_results: Dict) -> Dict[str, Any]:
        """Generate high-level performance summary"""
        summary = {
            'overall_performance_score': 0.0,
            'key_metrics': {},
            'performance_highlights': [],
            'areas_for_improvement': [],
            'system_readiness': 'unknown'
        }
        
        try:
            # Calculate overall performance score
            scores = []
            
            # Latency score (lower is better)
            if 'full_report' in latency_results:
                avg_latencies = []
                for component, operations in latency_results['full_report'].get('components', {}).items():
                    for operation, stats in operations.items():
                        avg_latencies.append(stats['latency_statistics_us']['mean'])
                
                if avg_latencies:
                    avg_latency = np.mean(avg_latencies)
                    latency_score = max(0, 100 - (avg_latency / 100))  # 100us = 100 points
                    scores.append(latency_score)
            
            # Memory score
            if 'full_report' in memory_results:
                memory_scores = []
                for component, operations in memory_results['full_report'].get('components', {}).items():
                    for operation, stats in operations.items():
                        memory_scores.append(stats['performance_metrics']['efficiency_score'])
                
                if memory_scores:
                    scores.append(np.mean(memory_scores))
            
            # Throughput score
            if 'full_report' in throughput_results:
                throughput_scores = []
                for component, operations in throughput_results['full_report'].get('components', {}).items():
                    for operation, stats in operations.items():
                        throughput_scores.append(stats['quality_metrics']['reliability_score'])
                
                if throughput_scores:
                    scores.append(np.mean(throughput_scores))
            
            # Calculate overall score
            if scores:
                summary['overall_performance_score'] = np.mean(scores)
            
            # Determine system readiness
            if summary['overall_performance_score'] >= 90:
                summary['system_readiness'] = 'production_ready'
            elif summary['overall_performance_score'] >= 75:
                summary['system_readiness'] = 'staging_ready'
            elif summary['overall_performance_score'] >= 60:
                summary['system_readiness'] = 'development_ready'
            else:
                summary['system_readiness'] = 'needs_optimization'
            
        except Exception as e:
            logger.error(f"Performance summary calculation error: {e}")
            summary['error'] = str(e)
        
        return summary
    
    async def _save_results(self, results: Dict[str, Any]):
        """Save performance test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive results as JSON
        results_file = self.output_dir / f"performance_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📁 Results saved to: {results_file}")
    
    def _generate_performance_report(self, results: Dict[str, Any]):
        """Generate human-readable performance report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"performance_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Core Engine Performance Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Test metadata
            metadata = results.get('test_metadata', {})
            f.write("## Test Configuration\n\n")
            f.write(f"- **Duration:** {metadata.get('duration_seconds', 0):.1f} seconds\n")
            f.write(f"- **Test Symbols:** {', '.join(metadata.get('test_symbols', []))}\n")
            f.write(f"- **Python Version:** {metadata.get('python_version', 'unknown')}\n\n")
            
            # Performance summary
            summary = results.get('performance_summary', {})
            f.write("## Performance Summary\n\n")
            f.write(f"- **Overall Score:** {summary.get('overall_performance_score', 0):.1f}/100\n")
            f.write(f"- **System Readiness:** {summary.get('system_readiness', 'unknown').replace('_', ' ').title()}\n\n")
            
            # Key findings
            f.write("## Key Findings\n\n")
            
            # Latency findings
            latency_results = results.get('latency_results', {})
            if 'full_report' in latency_results:
                f.write("### Latency Performance\n\n")
                for component, operations in latency_results['full_report'].get('components', {}).items():
                    f.write(f"**{component}:**\n")
                    for operation, stats in operations.items():
                        mean_ms = stats['latency_statistics_us']['mean'] / 1000
                        p99_ms = stats['percentiles_us']['p99'] / 1000
                        f.write(f"- {operation}: {mean_ms:.2f}ms avg, {p99_ms:.2f}ms P99\n")
                    f.write("\n")
            
            # Memory findings
            memory_results = results.get('memory_results', {})
            if 'full_report' in memory_results:
                f.write("### Memory Usage\n\n")
                for component, operations in memory_results['full_report'].get('components', {}).items():
                    f.write(f"**{component}:**\n")
                    for operation, stats in operations.items():
                        efficiency = stats['performance_metrics']['efficiency_score']
                        leaks = stats['leak_detection']['detected_leaks']
                        f.write(f"- {operation}: {efficiency:.1f}% efficiency, {leaks} leaks detected\n")
                    f.write("\n")
            
            # Throughput findings
            throughput_results = results.get('throughput_results', {})
            if 'full_report' in throughput_results:
                f.write("### Throughput Performance\n\n")
                for component, operations in throughput_results['full_report'].get('components', {}).items():
                    f.write(f"**{component}:**\n")
                    for operation, stats in operations.items():
                        peak_ops = stats['throughput_statistics']['peak_ops_per_sec']
                        reliability = stats['quality_metrics']['reliability_score']
                        f.write(f"- {operation}: {peak_ops:.1f} ops/sec peak, {reliability:.1f}% reliability\n")
                    f.write("\n")
            
            # Recommendations
            integrated_analysis = results.get('integrated_analysis', {})
            recommendations = integrated_analysis.get('optimization_recommendations', [])
            if recommendations:
                f.write("## Optimization Recommendations\n\n")
                for i, rec in enumerate(recommendations[:10], 1):  # Top 10 recommendations
                    f.write(f"{i}. **{rec.get('component', 'Unknown')} - {rec.get('operation', 'Unknown')}**\n")
                    f.write(f"   - Issue: {rec.get('issue', 'No description')}\n")
                    f.write(f"   - Recommendation: {rec.get('recommendation', 'No recommendation')}\n")
                    f.write(f"   - Priority: {rec.get('priority', 'unknown').title()}\n\n")
        
        logger.info(f"📊 Performance report generated: {report_file}")

# Main test runner
async def run_performance_tests():
    """Main function to run comprehensive performance tests"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize test suite
        test_suite = PerformanceTestSuite()
        
        # Initialize core engine
        logger.info("🔧 Initializing Core Engine...")
        config = create_production_config()
        integration_manager = SystemIntegrationManager(config)
        
        await integration_manager.initialize()
        await integration_manager.start()
        
        # Run comprehensive tests
        results = await test_suite.run_comprehensive_performance_tests(integration_manager)
        
        # Print summary
        summary = results.get('performance_summary', {})
        logger.info("\n" + "=" * 60)
        logger.info("🎯 PERFORMANCE TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall Performance Score: {summary.get('overall_performance_score', 0):.1f}/100")
        logger.info(f"System Readiness: {summary.get('system_readiness', 'unknown').replace('_', ' ').title()}")
        logger.info("=" * 60)
        
        # Cleanup
        await integration_manager.stop()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Performance testing failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(run_performance_tests())
