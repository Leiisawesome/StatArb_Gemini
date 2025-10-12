#!/usr/bin/env python3
"""
Core Engine Performance Validation Suite

This script validates the Phase 1 performance testing framework against
actual core_engine components to establish real-world performance baselines
and identify optimization opportunities.
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import performance testing framework
from tests.performance import (
    LatencyProfiler, MemoryProfiler, ThroughputBenchmarker,
    ComponentLatencyTester, ComponentMemoryTester, ComponentThroughputTester,
    LoadTestConfiguration
)

# Import core engine components
try:
    from core_engine.system.integration_manager import SystemIntegrationManager, create_production_config
    from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType
    CORE_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Core engine components not fully available: {e}")
    CORE_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class CoreEnginePerformanceValidator:
    """Validates performance framework with actual core_engine components"""
    
    def __init__(self, output_dir: str = "tests/performance/validation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize performance testing frameworks
        self.latency_profiler = LatencyProfiler(max_samples=10000)
        self.memory_profiler = MemoryProfiler(snapshot_interval=0.5, max_snapshots=5000)
        self.throughput_benchmarker = ThroughputBenchmarker(max_measurements=1000)
        
        # Initialize component testers
        self.latency_tester = ComponentLatencyTester(self.latency_profiler)
        self.memory_tester = ComponentMemoryTester(self.memory_profiler)
        self.throughput_tester = ComponentThroughputTester(self.throughput_benchmarker)
        
        # Test configuration
        self.test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        self.validation_results = {}
        
        # Core engine components
        self.integration_manager: Optional[SystemIntegrationManager] = None
        self.components = {}
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of performance framework with core engine"""
        logger.info("🎯 Starting Core Engine Performance Validation")
        logger.info("=" * 70)
        
        start_time = datetime.now()
        
        try:
            # Phase 1: Initialize Core Engine
            await self._initialize_core_engine()
            
            # Phase 2: Component Discovery and Health Check
            await self._discover_and_validate_components()
            
            # Phase 3: Latency Validation Tests
            logger.info("\n📊 Phase 3: Latency Performance Validation")
            latency_results = await self._validate_latency_performance()
            
            # Phase 4: Memory Usage Validation
            logger.info("\n🧠 Phase 4: Memory Usage Validation")
            memory_results = await self._validate_memory_performance()
            
            # Phase 5: Throughput Validation
            logger.info("\n🚀 Phase 5: Throughput Performance Validation")
            throughput_results = await self._validate_throughput_performance()
            
            # Phase 6: Integrated Analysis
            logger.info("\n📈 Phase 6: Integrated Performance Analysis")
            analysis_results = await self._perform_integrated_analysis()
            
            # Compile validation results
            end_time = datetime.now()
            validation_duration = end_time - start_time
            
            comprehensive_results = {
                'validation_metadata': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': validation_duration.total_seconds(),
                    'test_symbols': self.test_symbols,
                    'components_tested': list(self.components.keys()),
                    'framework_version': '1.0.0'
                },
                'component_discovery': self.validation_results.get('component_discovery', {}),
                'latency_validation': latency_results,
                'memory_validation': memory_results,
                'throughput_validation': throughput_results,
                'integrated_analysis': analysis_results,
                'performance_baseline': self._establish_performance_baseline(
                    latency_results, memory_results, throughput_results
                ),
                'optimization_opportunities': self._identify_optimization_opportunities(
                    latency_results, memory_results, throughput_results
                )
            }
            
            # Save validation results
            await self._save_validation_results(comprehensive_results)
            
            # Generate validation report
            self._generate_validation_report(comprehensive_results)
            
            logger.info(f"\n✅ Core engine validation completed in {validation_duration.total_seconds():.1f} seconds")
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"❌ Core engine validation failed: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if self.integration_manager:
                await self.integration_manager.stop()
    
    async def _initialize_core_engine(self):
        """Initialize core engine with production configuration"""
        logger.info("🔧 Initializing Core Engine...")
        
        if not CORE_ENGINE_AVAILABLE:
            raise RuntimeError("Core engine components not available for testing")
        
        # Create production configuration
        config = create_production_config()
        
        # Initialize integration manager
        self.integration_manager = SystemIntegrationManager(config)
        
        # Initialize and start the system
        init_success = await self.integration_manager.initialize()
        if not init_success:
            raise RuntimeError("Failed to initialize core engine")
        
        start_success = await self.integration_manager.start()
        if not start_success:
            raise RuntimeError("Failed to start core engine")
        
        logger.info("✅ Core engine initialized successfully")
    
    async def _discover_and_validate_components(self):
        """Discover available components and validate their health"""
        logger.info("🔍 Discovering and validating core engine components...")
        
        # Component discovery (using actual component names from integration manager)
        component_names = [
            'data_manager',
            'risk_manager',  # Note: stored as 'risk_manager' not 'central_risk_manager'
            'strategy_manager',
            'portfolio_manager',  # Note: stored as 'portfolio_manager' not 'enhanced_portfolio_manager'
            'execution_engine',  # Note: stored as 'execution_engine' not 'unified_execution_engine'
            'regime_engine',  # Note: stored as 'regime_engine' not 'enhanced_regime_engine'
            'indicators_engine',  # Note: stored as 'indicators_engine' not 'enhanced_technical_indicators'
            'analytics_manager'  # Note: stored as 'analytics_manager' not 'enhanced_analytics_manager'
        ]
        
        discovered_components = {}
        healthy_components = {}
        
        for component_name in component_names:
            try:
                component = self.integration_manager.components.get(component_name)
                if component:
                    discovered_components[component_name] = {
                        'available': True,
                        'type': type(component).__name__,
                        'module': type(component).__module__
                    }
                    
                    # Perform health check if available
                    try:
                        if hasattr(component, 'health_check'):
                            health_status = await component.health_check()
                            discovered_components[component_name]['health_status'] = health_status
                            
                            if health_status.get('healthy', False):
                                healthy_components[component_name] = component
                                logger.info(f"   ✅ {component_name}: Healthy")
                            else:
                                logger.warning(f"   ⚠️ {component_name}: Unhealthy - {health_status}")
                        else:
                            # Assume healthy if no health check method
                            healthy_components[component_name] = component
                            discovered_components[component_name]['health_status'] = {'healthy': True, 'note': 'No health_check method'}
                            logger.info(f"   ✅ {component_name}: Available (no health check)")
                            
                    except Exception as e:
                        logger.warning(f"   ⚠️ {component_name}: Health check failed - {e}")
                        discovered_components[component_name]['health_error'] = str(e)
                else:
                    discovered_components[component_name] = {'available': False}
                    logger.info(f"   ❌ {component_name}: Not available")
                    
            except Exception as e:
                logger.warning(f"   ❌ {component_name}: Discovery failed - {e}")
                discovered_components[component_name] = {'available': False, 'error': str(e)}
        
        self.components = healthy_components
        self.validation_results['component_discovery'] = {
            'total_components_checked': len(component_names),
            'components_discovered': len([c for c in discovered_components.values() if c.get('available', False)]),
            'components_healthy': len(healthy_components),
            'component_details': discovered_components
        }
        
        logger.info(f"✅ Component discovery complete: {len(healthy_components)}/{len(component_names)} components healthy")
    
    async def _validate_latency_performance(self) -> Dict[str, Any]:
        """Validate latency performance testing with actual components"""
        logger.info("   Testing latency performance with real components...")
        
        latency_results = {}
        
        # Test DataManager latency
        if 'data_manager' in self.components:
            logger.info("   📊 Testing DataManager latency...")
            try:
                data_manager = self.components['data_manager']
                
                # Test market data retrieval latency
                for i, symbol in enumerate(self.test_symbols[:3]):  # Test first 3 symbols
                    try:
                        _, measurement = self.latency_profiler.measure_sync_operation(
                            "DataManager", f"get_market_data_{symbol}",
                            data_manager.get_market_data, symbol
                        )
                        
                        if i == 0:  # Log first measurement for validation
                            logger.info(f"      Sample measurement: {measurement.latency_ns/1000:.2f} μs")
                            
                    except Exception as e:
                        logger.warning(f"      Failed to test {symbol}: {e}")
                
                # Get statistics
                stats = self.latency_profiler.get_statistics("DataManager", f"get_market_data_{self.test_symbols[0]}")
                if stats:
                    latency_results['data_manager'] = {
                        'component_type': 'DataManager',
                        'operation_tested': 'get_market_data',
                        'sample_count': stats.sample_count,
                        'mean_latency_us': stats.mean_us,
                        'p95_latency_us': stats.p95_us,
                        'p99_latency_us': stats.p99_us,
                        'throughput_ops_per_sec': stats.throughput_ops_per_sec,
                        'validation_status': 'success'
                    }
                    logger.info(f"      Mean latency: {stats.mean_us:.2f} μs, P99: {stats.p99_us:.2f} μs")
                
            except Exception as e:
                logger.error(f"      DataManager latency test failed: {e}")
                latency_results['data_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Test RiskManager latency
        if 'risk_manager' in self.components:
            logger.info("   🛡️ Testing RiskManager latency...")
            try:
                risk_manager = self.components['risk_manager']
                
                # Test authorization latency
                for i in range(10):  # Test 10 authorization requests
                    request = TradingDecisionRequest(
                        decision_type=TradingDecisionType.POSITION_ENTRY,
                        symbol=self.test_symbols[i % len(self.test_symbols)],
                        side="buy",
                        quantity=100,
                        strategy_id="validation_test",
                        confidence=0.8
                    )
                    
                    try:
                        _, measurement = await self.latency_profiler.measure_async_operation(
                            "RiskManager", "authorize_trading_decision",
                            risk_manager.authorize_trading_decision, request
                        )
                        
                        if i == 0:  # Log first measurement
                            logger.info(f"      Sample measurement: {measurement.latency_ns/1000:.2f} μs")
                            
                    except Exception as e:
                        logger.warning(f"      Authorization test {i} failed: {e}")
                
                # Get statistics
                stats = self.latency_profiler.get_statistics("RiskManager", "authorize_trading_decision")
                if stats:
                    latency_results['risk_manager'] = {
                        'component_type': 'CentralRiskManager',
                        'operation_tested': 'authorize_trading_decision',
                        'sample_count': stats.sample_count,
                        'mean_latency_us': stats.mean_us,
                        'p95_latency_us': stats.p95_us,
                        'p99_latency_us': stats.p99_us,
                        'throughput_ops_per_sec': stats.throughput_ops_per_sec,
                        'validation_status': 'success'
                    }
                    logger.info(f"      Mean latency: {stats.mean_us:.2f} μs, P99: {stats.p99_us:.2f} μs")
                
            except Exception as e:
                logger.error(f"      RiskManager latency test failed: {e}")
                latency_results['risk_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Test StrategyManager latency
        if 'strategy_manager' in self.components:
            logger.info("   📈 Testing StrategyManager latency...")
            try:
                strategy_manager = self.components['strategy_manager']
                
                # Test signal generation latency
                for i in range(5):  # Test 5 signal generation calls
                    try:
                        _, measurement = await self.latency_profiler.measure_async_operation(
                            "StrategyManager", "generate_signals",
                            strategy_manager.generate_signals, self.test_symbols[:2]  # Use first 2 symbols
                        )
                        
                        if i == 0:  # Log first measurement
                            logger.info(f"      Sample measurement: {measurement.latency_ns/1000:.2f} μs")
                            
                    except Exception as e:
                        logger.warning(f"      Signal generation test {i} failed: {e}")
                
                # Get statistics
                stats = self.latency_profiler.get_statistics("StrategyManager", "generate_signals")
                if stats:
                    latency_results['strategy_manager'] = {
                        'component_type': 'StrategyManager',
                        'operation_tested': 'generate_signals',
                        'sample_count': stats.sample_count,
                        'mean_latency_us': stats.mean_us,
                        'p95_latency_us': stats.p95_us,
                        'p99_latency_us': stats.p99_us,
                        'throughput_ops_per_sec': stats.throughput_ops_per_sec,
                        'validation_status': 'success'
                    }
                    logger.info(f"      Mean latency: {stats.mean_us:.2f} μs, P99: {stats.p99_us:.2f} μs")
                
            except Exception as e:
                logger.error(f"      StrategyManager latency test failed: {e}")
                latency_results['strategy_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Generate comprehensive latency report
        latency_report = self.latency_profiler.generate_performance_report()
        latency_results['comprehensive_report'] = latency_report
        
        successful_tests = len([r for r in latency_results.values() if isinstance(r, dict) and r.get('validation_status') == 'success'])
        logger.info(f"   ✅ Latency validation complete: {successful_tests} components tested successfully")
        
        return latency_results
    
    async def _validate_memory_performance(self) -> Dict[str, Any]:
        """Validate memory performance testing with actual components"""
        logger.info("   Testing memory performance with real components...")
        
        memory_results = {}
        
        # Test DataManager memory usage
        if 'data_manager' in self.components:
            logger.info("   📊 Testing DataManager memory usage...")
            try:
                data_manager = self.components['data_manager']
                
                # Start memory monitoring
                monitoring_id = self.memory_profiler.start_monitoring("DataManager", "bulk_data_operations")
                
                # Perform memory-intensive operations
                for i in range(20):  # Reduced iterations for validation
                    symbol = self.test_symbols[i % len(self.test_symbols)]
                    
                    try:
                        # Take snapshot before operation
                        self.memory_profiler.take_snapshot("DataManager", "pre_operation", {"iteration": i, "symbol": symbol})
                        
                        # Perform data operation
                        data_manager.get_market_data(symbol)
                        
                        # Take snapshot after operation
                        self.memory_profiler.take_snapshot("DataManager", "post_operation", {"iteration": i, "symbol": symbol})
                        
                        if i % 5 == 0:
                            logger.info(f"      Completed {i+1}/20 memory test operations")
                            
                    except Exception as e:
                        logger.warning(f"      Memory test operation {i} failed: {e}")
                
                # Stop monitoring
                self.memory_profiler.stop_monitoring(monitoring_id)
                
                # Analyze memory usage
                analysis = self.memory_profiler.analyze_memory_usage("DataManager", "bulk_data_operations")
                if analysis:
                    memory_results['data_manager'] = {
                        'component_type': 'DataManager',
                        'operation_tested': 'bulk_data_operations',
                        'peak_memory_mb': analysis.peak_memory_mb,
                        'average_memory_mb': analysis.average_memory_mb,
                        'memory_growth_mb': analysis.memory_growth_mb,
                        'memory_efficiency_score': analysis.memory_efficiency_score,
                        'detected_leaks': len(analysis.detected_leaks),
                        'validation_status': 'success'
                    }
                    logger.info(f"      Peak memory: {analysis.peak_memory_mb:.2f} MB, Efficiency: {analysis.memory_efficiency_score:.1f}%")
                
            except Exception as e:
                logger.error(f"      DataManager memory test failed: {e}")
                memory_results['data_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Test StrategyManager memory usage
        if 'strategy_manager' in self.components:
            logger.info("   📈 Testing StrategyManager memory usage...")
            try:
                strategy_manager = self.components['strategy_manager']
                
                # Start memory monitoring
                monitoring_id = self.memory_profiler.start_monitoring("StrategyManager", "signal_generation_memory")
                
                # Perform signal generation operations
                for i in range(10):  # Reduced iterations for validation
                    try:
                        # Take snapshot before operation
                        self.memory_profiler.take_snapshot("StrategyManager", "pre_signals", {"iteration": i})
                        
                        # Generate signals
                        signals = await strategy_manager.generate_signals(self.test_symbols[:3])  # Use first 3 symbols
                        
                        # Take snapshot after operation
                        self.memory_profiler.take_snapshot("StrategyManager", "post_signals", {
                            "iteration": i,
                            "signals_count": len(signals) if signals else 0
                        })
                        
                        if i % 3 == 0:
                            logger.info(f"      Completed {i+1}/10 signal generation memory tests")
                            
                    except Exception as e:
                        logger.warning(f"      Signal generation memory test {i} failed: {e}")
                
                # Stop monitoring
                self.memory_profiler.stop_monitoring(monitoring_id)
                
                # Analyze memory usage
                analysis = self.memory_profiler.analyze_memory_usage("StrategyManager", "signal_generation_memory")
                if analysis:
                    memory_results['strategy_manager'] = {
                        'component_type': 'StrategyManager',
                        'operation_tested': 'signal_generation_memory',
                        'peak_memory_mb': analysis.peak_memory_mb,
                        'average_memory_mb': analysis.average_memory_mb,
                        'memory_growth_mb': analysis.memory_growth_mb,
                        'memory_efficiency_score': analysis.memory_efficiency_score,
                        'detected_leaks': len(analysis.detected_leaks),
                        'validation_status': 'success'
                    }
                    logger.info(f"      Peak memory: {analysis.peak_memory_mb:.2f} MB, Efficiency: {analysis.memory_efficiency_score:.1f}%")
                
            except Exception as e:
                logger.error(f"      StrategyManager memory test failed: {e}")
                memory_results['strategy_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Generate comprehensive memory report
        memory_report = self.memory_profiler.generate_memory_report()
        memory_results['comprehensive_report'] = memory_report
        
        successful_tests = len([r for r in memory_results.values() if isinstance(r, dict) and r.get('validation_status') == 'success'])
        logger.info(f"   ✅ Memory validation complete: {successful_tests} components tested successfully")
        
        return memory_results
    
    async def _validate_throughput_performance(self) -> Dict[str, Any]:
        """Validate throughput performance testing with actual components"""
        logger.info("   Testing throughput performance with real components...")
        
        throughput_results = {}
        
        # Test DataManager throughput (reduced scale for validation)
        if 'data_manager' in self.components:
            logger.info("   📊 Testing DataManager throughput...")
            try:
                data_manager = self.components['data_manager']
                
                # Configure reduced load test for validation
                def generate_test_symbol():
                    import random
                    return random.choice(self.test_symbols)
                
                def get_market_data_operation(symbol):
                    return data_manager.get_market_data(symbol)
                
                config = LoadTestConfiguration(
                    component_name="DataManager",
                    operation_name="get_market_data_validation",
                    target_operations=100,  # Reduced for validation
                    concurrent_workers=[1, 2, 4],  # Reduced concurrency levels
                    duration_seconds=15,  # Reduced duration
                    ramp_up_seconds=2,
                    test_data_generator=generate_test_symbol,
                    operation_function=get_market_data_operation,
                    enable_warmup=True,
                    warmup_operations=10
                )
                
                self.throughput_benchmarker.benchmark_sync_operation(config)
                
                # Get statistics
                stats = self.throughput_benchmarker.calculate_statistics("DataManager", "get_market_data_validation")
                if stats:
                    throughput_results['data_manager'] = {
                        'component_type': 'DataManager',
                        'operation_tested': 'get_market_data_validation',
                        'peak_throughput_ops_per_sec': stats.peak_throughput_ops_per_sec,
                        'average_throughput_ops_per_sec': stats.average_throughput_ops_per_sec,
                        'optimal_worker_count': stats.optimal_worker_count,
                        'scalability_factor': stats.linear_scalability_factor,
                        'reliability_score': stats.reliability_score,
                        'measurement_count': stats.measurement_count,
                        'validation_status': 'success'
                    }
                    logger.info(f"      Peak throughput: {stats.peak_throughput_ops_per_sec:.1f} ops/sec")
                    logger.info(f"      Optimal workers: {stats.optimal_worker_count}, Reliability: {stats.reliability_score:.1f}%")
                
            except Exception as e:
                logger.error(f"      DataManager throughput test failed: {e}")
                throughput_results['data_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Test RiskManager throughput (reduced scale for validation)
        if 'risk_manager' in self.components:
            logger.info("   🛡️ Testing RiskManager throughput...")
            try:
                risk_manager = self.components['risk_manager']
                
                def generate_test_request():
                    import random
                    return TradingDecisionRequest(
                        decision_type=TradingDecisionType.POSITION_ENTRY,
                        symbol=random.choice(self.test_symbols),
                        side=random.choice(["buy", "sell"]),
                        quantity=random.randint(100, 500),
                        strategy_id="validation_throughput_test",
                        confidence=random.uniform(0.6, 0.9)
                    )
                
                async def authorize_operation(request):
                    return await risk_manager.authorize_trading_decision(request)
                
                config = LoadTestConfiguration(
                    component_name="RiskManager",
                    operation_name="authorize_validation",
                    target_operations=200,  # Reduced for validation
                    concurrent_workers=[1, 2],  # Reduced concurrency
                    duration_seconds=10,  # Reduced duration
                    ramp_up_seconds=1,
                    test_data_generator=generate_test_request,
                    operation_function=authorize_operation,
                    enable_warmup=True,
                    warmup_operations=5
                )
                
                await self.throughput_benchmarker.benchmark_async_operation(config)
                
                # Get statistics
                stats = self.throughput_benchmarker.calculate_statistics("RiskManager", "authorize_validation")
                if stats:
                    throughput_results['risk_manager'] = {
                        'component_type': 'CentralRiskManager',
                        'operation_tested': 'authorize_validation',
                        'peak_throughput_ops_per_sec': stats.peak_throughput_ops_per_sec,
                        'average_throughput_ops_per_sec': stats.average_throughput_ops_per_sec,
                        'optimal_worker_count': stats.optimal_worker_count,
                        'scalability_factor': stats.linear_scalability_factor,
                        'reliability_score': stats.reliability_score,
                        'measurement_count': stats.measurement_count,
                        'validation_status': 'success'
                    }
                    logger.info(f"      Peak throughput: {stats.peak_throughput_ops_per_sec:.1f} ops/sec")
                    logger.info(f"      Optimal workers: {stats.optimal_worker_count}, Reliability: {stats.reliability_score:.1f}%")
                
            except Exception as e:
                logger.error(f"      RiskManager throughput test failed: {e}")
                throughput_results['risk_manager'] = {'validation_status': 'failed', 'error': str(e)}
        
        # Generate comprehensive throughput report
        throughput_report = self.throughput_benchmarker.generate_throughput_report()
        throughput_results['comprehensive_report'] = throughput_report
        
        successful_tests = len([r for r in throughput_results.values() if isinstance(r, dict) and r.get('validation_status') == 'success'])
        logger.info(f"   ✅ Throughput validation complete: {successful_tests} components tested successfully")
        
        return throughput_results
    
    async def _perform_integrated_analysis(self) -> Dict[str, Any]:
        """Perform integrated analysis across all performance metrics"""
        logger.info("   Performing integrated performance analysis...")
        
        analysis_results = {
            'framework_validation': {},
            'component_performance_summary': {},
            'cross_metric_correlations': {},
            'performance_bottlenecks': [],
            'validation_success_rate': 0.0
        }
        
        try:
            # Framework validation summary
            latency_measurements = self.latency_profiler.generate_performance_report()
            memory_measurements = self.memory_profiler.generate_memory_report()
            self.throughput_benchmarker.generate_throughput_report()
            
            analysis_results['framework_validation'] = {
                'latency_framework': {
                    'total_measurements': latency_measurements.get('total_measurements', 0),
                    'components_tested': len(latency_measurements.get('components', {})),
                    'measurement_precision': 'nanosecond',
                    'statistical_analysis': 'percentiles_and_outliers'
                },
                'memory_framework': {
                    'total_snapshots': sum(len(snapshots) for snapshots in self.memory_profiler.snapshots.values()),
                    'components_analyzed': memory_measurements['summary']['total_components_analyzed'],
                    'leak_detection': 'statistical_regression',
                    'efficiency_scoring': '0-100_scale'
                },
                'throughput_framework': {
                    'total_measurements': sum(len(measurements) for measurements in self.throughput_benchmarker.measurements.values()),
                    'scalability_analysis': 'linear_regression',
                    'concurrency_testing': 'multi_worker',
                    'reliability_scoring': '0-100_scale'
                }
            }
            
            # Calculate validation success rate
            total_tests = 0
            successful_tests = 0
            
            for result_set in [self.validation_results.get('latency_validation', {}),
                             self.validation_results.get('memory_validation', {}),
                             self.validation_results.get('throughput_validation', {})]:
                for component, result in result_set.items():
                    if isinstance(result, dict) and 'validation_status' in result:
                        total_tests += 1
                        if result['validation_status'] == 'success':
                            successful_tests += 1
            
            analysis_results['validation_success_rate'] = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            logger.info(f"   Framework validation success rate: {analysis_results['validation_success_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"   Integrated analysis failed: {e}")
            analysis_results['error'] = str(e)
        
        return analysis_results
    
    def _establish_performance_baseline(self, latency_results: Dict, memory_results: Dict, throughput_results: Dict) -> Dict[str, Any]:
        """Establish performance baselines for core engine components"""
        baseline = {
            'baseline_timestamp': datetime.now().isoformat(),
            'component_baselines': {},
            'system_baseline': {}
        }
        
        # Component-specific baselines
        for component_name in self.components.keys():
            component_baseline = {}
            
            # Latency baseline
            if component_name in latency_results and latency_results[component_name].get('validation_status') == 'success':
                component_baseline['latency'] = {
                    'mean_latency_us': latency_results[component_name]['mean_latency_us'],
                    'p95_latency_us': latency_results[component_name]['p95_latency_us'],
                    'p99_latency_us': latency_results[component_name]['p99_latency_us'],
                    'throughput_ops_per_sec': latency_results[component_name]['throughput_ops_per_sec']
                }
            
            # Memory baseline
            if component_name in memory_results and memory_results[component_name].get('validation_status') == 'success':
                component_baseline['memory'] = {
                    'peak_memory_mb': memory_results[component_name]['peak_memory_mb'],
                    'average_memory_mb': memory_results[component_name]['average_memory_mb'],
                    'memory_efficiency_score': memory_results[component_name]['memory_efficiency_score'],
                    'detected_leaks': memory_results[component_name]['detected_leaks']
                }
            
            # Throughput baseline
            if component_name in throughput_results and throughput_results[component_name].get('validation_status') == 'success':
                component_baseline['throughput'] = {
                    'peak_throughput_ops_per_sec': throughput_results[component_name]['peak_throughput_ops_per_sec'],
                    'optimal_worker_count': throughput_results[component_name]['optimal_worker_count'],
                    'scalability_factor': throughput_results[component_name]['scalability_factor'],
                    'reliability_score': throughput_results[component_name]['reliability_score']
                }
            
            if component_baseline:
                baseline['component_baselines'][component_name] = component_baseline
        
        return baseline
    
    def _identify_optimization_opportunities(self, latency_results: Dict, memory_results: Dict, throughput_results: Dict) -> List[Dict[str, Any]]:
        """Identify optimization opportunities based on validation results"""
        opportunities = []
        
        # Analyze latency results for optimization opportunities
        for component_name, result in latency_results.items():
            if isinstance(result, dict) and result.get('validation_status') == 'success':
                # High latency opportunity
                if result.get('p99_latency_us', 0) > 10000:  # > 10ms
                    opportunities.append({
                        'type': 'latency_optimization',
                        'component': component_name,
                        'issue': f"High P99 latency: {result['p99_latency_us']/1000:.1f}ms",
                        'recommendation': "Consider async optimization, caching, or algorithm improvements",
                        'priority': 'high' if result['p99_latency_us'] > 50000 else 'medium',
                        'baseline_value': result['p99_latency_us']
                    })
                
                # Low throughput opportunity
                if result.get('throughput_ops_per_sec', 0) < 100:  # < 100 ops/sec
                    opportunities.append({
                        'type': 'throughput_optimization',
                        'component': component_name,
                        'issue': f"Low throughput: {result['throughput_ops_per_sec']:.1f} ops/sec",
                        'recommendation': "Optimize for higher concurrency or reduce per-operation overhead",
                        'priority': 'medium',
                        'baseline_value': result['throughput_ops_per_sec']
                    })
        
        # Analyze memory results for optimization opportunities
        for component_name, result in memory_results.items():
            if isinstance(result, dict) and result.get('validation_status') == 'success':
                # Memory efficiency opportunity
                if result.get('memory_efficiency_score', 100) < 70:
                    opportunities.append({
                        'type': 'memory_optimization',
                        'component': component_name,
                        'issue': f"Low memory efficiency: {result['memory_efficiency_score']:.1f}%",
                        'recommendation': "Review object lifecycle, implement memory pooling, or optimize data structures",
                        'priority': 'medium',
                        'baseline_value': result['memory_efficiency_score']
                    })
                
                # Memory leak opportunity
                if result.get('detected_leaks', 0) > 0:
                    opportunities.append({
                        'type': 'memory_leak_fix',
                        'component': component_name,
                        'issue': f"Memory leaks detected: {result['detected_leaks']} leaks",
                        'recommendation': "Investigate and fix memory leaks to prevent long-term degradation",
                        'priority': 'high',
                        'baseline_value': result['detected_leaks']
                    })
        
        # Analyze throughput results for optimization opportunities
        for component_name, result in throughput_results.items():
            if isinstance(result, dict) and result.get('validation_status') == 'success':
                # Poor scalability opportunity
                if result.get('scalability_factor', 1.0) < 0.5:
                    opportunities.append({
                        'type': 'scalability_optimization',
                        'component': component_name,
                        'issue': f"Poor scalability: {result['scalability_factor']:.2f} factor",
                        'recommendation': "Reduce contention, optimize for concurrent execution, or redesign for parallelism",
                        'priority': 'high',
                        'baseline_value': result['scalability_factor']
                    })
                
                # Low reliability opportunity
                if result.get('reliability_score', 100) < 95:
                    opportunities.append({
                        'type': 'reliability_improvement',
                        'component': component_name,
                        'issue': f"Low reliability: {result['reliability_score']:.1f}%",
                        'recommendation': "Improve error handling, add retries, or fix underlying stability issues",
                        'priority': 'high',
                        'baseline_value': result['reliability_score']
                    })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        opportunities.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return opportunities
    
    async def _save_validation_results(self, results: Dict[str, Any]):
        """Save validation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive results as JSON
        results_file = self.output_dir / f"core_engine_validation_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📁 Validation results saved to: {results_file}")
    
    def _generate_validation_report(self, results: Dict[str, Any]):
        """Generate human-readable validation report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"core_engine_validation_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Core Engine Performance Framework Validation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Validation metadata
            metadata = results.get('validation_metadata', {})
            f.write("## Validation Summary\n\n")
            f.write(f"- **Duration:** {metadata.get('duration_seconds', 0):.1f} seconds\n")
            f.write(f"- **Components Tested:** {len(metadata.get('components_tested', []))}\n")
            f.write(f"- **Test Symbols:** {', '.join(metadata.get('test_symbols', []))}\n")
            f.write(f"- **Framework Version:** {metadata.get('framework_version', 'unknown')}\n\n")
            
            # Component discovery results
            discovery = results.get('component_discovery', {})
            f.write("## Component Discovery\n\n")
            f.write(f"- **Total Components Checked:** {discovery.get('total_components_checked', 0)}\n")
            f.write(f"- **Components Discovered:** {discovery.get('components_discovered', 0)}\n")
            f.write(f"- **Components Healthy:** {discovery.get('components_healthy', 0)}\n\n")
            
            # Validation success rate
            integrated_analysis = results.get('integrated_analysis', {})
            success_rate = integrated_analysis.get('validation_success_rate', 0)
            f.write(f"## Overall Validation Success Rate: {success_rate:.1f}%\n\n")
            
            # Performance baselines
            baseline = results.get('performance_baseline', {})
            if 'component_baselines' in baseline:
                f.write("## Performance Baselines Established\n\n")
                for component, baseline_data in baseline['component_baselines'].items():
                    f.write(f"### {component.replace('_', ' ').title()}\n\n")
                    
                    if 'latency' in baseline_data:
                        latency = baseline_data['latency']
                        f.write(f"**Latency Performance:**\n")
                        f.write(f"- Mean: {latency['mean_latency_us']:.2f} μs\n")
                        f.write(f"- P95: {latency['p95_latency_us']:.2f} μs\n")
                        f.write(f"- P99: {latency['p99_latency_us']:.2f} μs\n")
                        f.write(f"- Throughput: {latency['throughput_ops_per_sec']:.1f} ops/sec\n\n")
                    
                    if 'memory' in baseline_data:
                        memory = baseline_data['memory']
                        f.write(f"**Memory Performance:**\n")
                        f.write(f"- Peak Memory: {memory['peak_memory_mb']:.2f} MB\n")
                        f.write(f"- Average Memory: {memory['average_memory_mb']:.2f} MB\n")
                        f.write(f"- Efficiency Score: {memory['memory_efficiency_score']:.1f}%\n")
                        f.write(f"- Detected Leaks: {memory['detected_leaks']}\n\n")
                    
                    if 'throughput' in baseline_data:
                        throughput = baseline_data['throughput']
                        f.write(f"**Throughput Performance:**\n")
                        f.write(f"- Peak Throughput: {throughput['peak_throughput_ops_per_sec']:.1f} ops/sec\n")
                        f.write(f"- Optimal Workers: {throughput['optimal_worker_count']}\n")
                        f.write(f"- Scalability Factor: {throughput['scalability_factor']:.2f}\n")
                        f.write(f"- Reliability Score: {throughput['reliability_score']:.1f}%\n\n")
            
            # Optimization opportunities
            opportunities = results.get('optimization_opportunities', [])
            if opportunities:
                f.write("## Optimization Opportunities\n\n")
                for i, opp in enumerate(opportunities[:10], 1):  # Top 10 opportunities
                    f.write(f"{i}. **{opp.get('component', 'Unknown').replace('_', ' ').title()} - {opp.get('type', 'Unknown').replace('_', ' ').title()}**\n")
                    f.write(f"   - Issue: {opp.get('issue', 'No description')}\n")
                    f.write(f"   - Recommendation: {opp.get('recommendation', 'No recommendation')}\n")
                    f.write(f"   - Priority: {opp.get('priority', 'unknown').title()}\n")
                    f.write(f"   - Baseline Value: {opp.get('baseline_value', 'N/A')}\n\n")
            
            # Framework validation summary
            framework_validation = integrated_analysis.get('framework_validation', {})
            if framework_validation:
                f.write("## Framework Validation Summary\n\n")
                
                latency_fw = framework_validation.get('latency_framework', {})
                f.write(f"**Latency Framework:**\n")
                f.write(f"- Total Measurements: {latency_fw.get('total_measurements', 0)}\n")
                f.write(f"- Components Tested: {latency_fw.get('components_tested', 0)}\n")
                f.write(f"- Precision: {latency_fw.get('measurement_precision', 'unknown')}\n\n")
                
                memory_fw = framework_validation.get('memory_framework', {})
                f.write(f"**Memory Framework:**\n")
                f.write(f"- Total Snapshots: {memory_fw.get('total_snapshots', 0)}\n")
                f.write(f"- Components Analyzed: {memory_fw.get('components_analyzed', 0)}\n")
                f.write(f"- Leak Detection: {memory_fw.get('leak_detection', 'unknown')}\n\n")
                
                throughput_fw = framework_validation.get('throughput_framework', {})
                f.write(f"**Throughput Framework:**\n")
                f.write(f"- Total Measurements: {throughput_fw.get('total_measurements', 0)}\n")
                f.write(f"- Scalability Analysis: {throughput_fw.get('scalability_analysis', 'unknown')}\n")
                f.write(f"- Concurrency Testing: {throughput_fw.get('concurrency_testing', 'unknown')}\n\n")
        
        logger.info(f"📊 Validation report generated: {report_file}")

async def main():
    """Main validation function"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tests/performance/core_engine_validation.log')
        ]
    )
    
    try:
        # Initialize validator
        validator = CoreEnginePerformanceValidator()
        
        # Run comprehensive validation
        results = await validator.run_comprehensive_validation()
        
        # Print summary
        metadata = results.get('validation_metadata', {})
        integrated_analysis = results.get('integrated_analysis', {})
        baseline = results.get('performance_baseline', {})
        opportunities = results.get('optimization_opportunities', [])
        
        logger.info("\n" + "=" * 70)
        logger.info("🎯 CORE ENGINE PERFORMANCE VALIDATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Validation Duration: {metadata.get('duration_seconds', 0):.1f} seconds")
        logger.info(f"Components Tested: {len(metadata.get('components_tested', []))}")
        logger.info(f"Validation Success Rate: {integrated_analysis.get('validation_success_rate', 0):.1f}%")
        logger.info(f"Performance Baselines Established: {len(baseline.get('component_baselines', {}))}")
        logger.info(f"Optimization Opportunities Identified: {len(opportunities)}")
        logger.info("=" * 70)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Core engine validation failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
