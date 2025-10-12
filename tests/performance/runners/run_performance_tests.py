#!/usr/bin/env python3
"""
Performance Test Runner for StatArb_Gemini Core Engine

This script runs comprehensive performance tests on the core engine components
and generates detailed performance reports with optimization recommendations.

Usage:
    python tests/performance/run_performance_tests.py [options]
    
Options:
    --quick         Run quick performance tests (reduced iterations)
    --component     Test specific component only (data_manager, risk_manager, etc.)
    --output-dir    Specify output directory for results (default: tests/performance/results)
    --verbose       Enable verbose logging
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.performance.performance_test_suite import run_performance_tests
from tests.performance.latency_testing import LatencyProfiler, ComponentLatencyTester
from tests.performance.memory_profiling import MemoryProfiler, ComponentMemoryTester  
from tests.performance.throughput_benchmarking import ThroughputBenchmarker, ComponentThroughputTester

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tests/performance/performance_tests.log')
        ]
    )
    
    # Reduce noise from some modules
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

async def run_quick_tests():
    """Run quick performance tests with reduced iterations"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Running Quick Performance Tests")
    
    try:
        # Initialize profilers
        latency_profiler = LatencyProfiler(max_samples=1000)
        memory_profiler = MemoryProfiler(max_snapshots=500)
        throughput_benchmarker = ThroughputBenchmarker(max_measurements=100)
        
        # Run quick latency test
        logger.info("📊 Quick Latency Test...")
        
        async def sample_operation():
            await asyncio.sleep(0.001)  # 1ms operation
            return "result"
        
        # Test latency measurement
        for i in range(100):
            _, measurement = await latency_profiler.measure_async_operation(
                "QuickTest", "sample_operation", sample_operation
            )
        
        # Get statistics
        stats = latency_profiler.get_statistics("QuickTest", "sample_operation")
        if stats:
            logger.info(f"   Mean latency: {stats.mean_us:.2f} μs")
            logger.info(f"   P99 latency: {stats.p99_us:.2f} μs")
            logger.info(f"   Throughput: {stats.throughput_ops_per_sec:.1f} ops/sec")
        
        # Run quick memory test
        logger.info("🧠 Quick Memory Test...")
        
        data_list = []
        monitoring_id = memory_profiler.start_monitoring("QuickTest", "memory_allocation")
        
        for i in range(100):
            data_list.append([i] * 1000)  # Allocate some memory
            if i % 20 == 0:
                memory_profiler.take_snapshot("QuickTest", "allocation", {"iteration": i})
        
        memory_profiler.stop_monitoring(monitoring_id)
        
        # Analyze memory usage
        analysis = memory_profiler.analyze_memory_usage("QuickTest", "memory_allocation")
        if analysis:
            logger.info(f"   Peak memory: {analysis.peak_memory_mb:.2f} MB")
            logger.info(f"   Memory efficiency: {analysis.memory_efficiency_score:.1f}%")
            logger.info(f"   Detected leaks: {len(analysis.detected_leaks)}")
        
        logger.info("✅ Quick performance tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Quick tests failed: {e}", exc_info=True)
        raise

async def run_component_tests(component_name: str):
    """Run performance tests for a specific component"""
    logger = logging.getLogger(__name__)
    logger.info(f"🎯 Running Performance Tests for {component_name}")
    
    try:
        from core_engine.system.integration_manager import SystemIntegrationManager, create_production_config
        
        # Initialize core engine
        config = create_production_config()
        integration_manager = SystemIntegrationManager(config)
        
        await integration_manager.initialize()
        await integration_manager.start()
        
        # Initialize testers
        latency_profiler = LatencyProfiler()
        memory_profiler = MemoryProfiler()
        throughput_benchmarker = ThroughputBenchmarker()
        
        latency_tester = ComponentLatencyTester(latency_profiler)
        memory_tester = ComponentMemoryTester(memory_profiler)
        throughput_tester = ComponentThroughputTester(throughput_benchmarker)
        
        test_symbols = ["AAPL", "MSFT", "GOOGL"]
        
        # Run component-specific tests
        if component_name.lower() == 'data_manager':
            data_manager = integration_manager.get_component('data_manager')
            if data_manager:
                logger.info("Testing DataManager performance...")
                await latency_tester.test_data_manager_latency(data_manager, test_symbols, 200)
                await memory_tester.test_data_manager_memory(data_manager, test_symbols, 20)
                await throughput_tester.test_data_manager_throughput(data_manager, test_symbols)
            
        elif component_name.lower() == 'risk_manager':
            risk_manager = integration_manager.get_component('central_risk_manager')
            if risk_manager:
                logger.info("Testing RiskManager performance...")
                await latency_tester.test_risk_manager_latency(risk_manager, 500)
                await throughput_tester.test_risk_manager_throughput(risk_manager)
            
        elif component_name.lower() == 'strategy_manager':
            strategy_manager = integration_manager.get_component('strategy_manager')
            if strategy_manager:
                logger.info("Testing StrategyManager performance...")
                await latency_tester.test_strategy_manager_latency(strategy_manager, test_symbols, 100)
                await memory_tester.test_strategy_manager_memory(strategy_manager, test_symbols, 15)
                await throughput_tester.test_strategy_manager_throughput(strategy_manager, test_symbols)
        
        else:
            logger.error(f"Unknown component: {component_name}")
            return
        
        # Generate reports
        latency_report = latency_profiler.generate_performance_report()
        memory_profiler.generate_memory_report()
        throughput_benchmarker.generate_throughput_report()
        
        logger.info(f"✅ {component_name} performance tests completed")
        logger.info(f"📊 Latency measurements: {latency_report.get('total_measurements', 0)}")
        logger.info(f"🧠 Memory snapshots: {len(memory_profiler.snapshots)}")
        logger.info(f"🚀 Throughput tests: {len(throughput_benchmarker.measurements)}")
        
        # Cleanup
        await integration_manager.stop()
        
    except Exception as e:
        logger.error(f"❌ Component tests failed: {e}", exc_info=True)
        raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run performance tests for StatArb_Gemini core engine")
    
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick performance tests with reduced iterations')
    parser.add_argument('--component', type=str, 
                       help='Test specific component (data_manager, risk_manager, strategy_manager)')
    parser.add_argument('--output-dir', type=str, default='tests/performance/results',
                       help='Output directory for test results')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if args.quick:
            # Run quick tests
            asyncio.run(run_quick_tests())
            
        elif args.component:
            # Run component-specific tests
            asyncio.run(run_component_tests(args.component))
            
        else:
            # Run comprehensive tests
            logger.info("🎯 Running Comprehensive Performance Tests")
            asyncio.run(run_performance_tests())
            
    except KeyboardInterrupt:
        logger.info("⏹️ Performance tests interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Performance tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
