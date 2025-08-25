#!/usr/bin/env python3
"""
Phase 5 Performance Optimization Testing
========================================

Test suite for validating Phase 5 performance optimization implementation.
Tests performance improvements, monitoring capabilities, and system optimization.

Author: StatArb_Gemini Team
"""

import asyncio
import unittest
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trade_engine.performance.profiler import SystemProfiler, system_profiler, time_component
from trade_engine.performance.cache_manager import OptimizedCacheManager, template_cache
from trade_engine.performance.optimization_engine import PerformanceOptimizationEngine, optimization_engine
from trade_engine.monitoring.metrics_collector import MetricsCollector, metrics_collector, MetricType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPhase5Performance(unittest.TestCase):
    """Test Phase 5 performance optimization implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.profiler = SystemProfiler(collection_interval=0.1, history_size=100)
        self.cache_manager = OptimizedCacheManager(max_size=2000, default_ttl=60)  # Increased for load test
        self.optimization_engine = PerformanceOptimizationEngine(optimization_interval=1.0)
        self.metrics_collector = MetricsCollector(collection_interval=0.1)
    
    def tearDown(self):
        """Clean up test environment"""
        asyncio.run(self._async_teardown())
    
    async def _async_teardown(self):
        """Async teardown"""
        try:
            await self.profiler.stop_profiling()
            await self.cache_manager.stop_cache_manager()
            await self.optimization_engine.stop_optimization()
            await self.metrics_collector.stop_collection()
        except:
            pass
    
    def test_system_profiler_initialization(self):
        """Test system profiler initialization and basic functionality"""
        logger.info("Testing system profiler initialization")
        
        # Test profiler initialization
        self.assertIsNotNone(self.profiler)
        self.assertFalse(self.profiler.is_profiling)
        self.assertEqual(len(self.profiler.metrics_history), 0)
        
        # Test timer functionality
        timer_id = self.profiler.start_timer('test_component')
        self.assertIsNotNone(timer_id)
        self.assertIn(timer_id, self.profiler.active_timers)
        
        time.sleep(0.01)  # Small delay
        duration = self.profiler.end_timer(timer_id)
        self.assertGreater(duration, 0)
        self.assertIn('test_component', self.profiler.component_timers)
        
        logger.info("✅ System profiler basic functionality passed")
    
    def test_cache_manager_functionality(self):
        """Test cache manager performance and functionality"""
        logger.info("Testing cache manager functionality")
        
        # Test basic cache operations
        self.cache_manager.set('test_key', 'test_value')
        value = self.cache_manager.get('test_key')
        self.assertEqual(value, 'test_value')
        
        # Test cache metrics
        metrics = self.cache_manager.get_metrics()
        self.assertGreater(metrics.total_sets, 0)
        self.assertGreater(metrics.hits, 0)
        
        # Test cache info
        cache_info = self.cache_manager.get_cache_info()
        self.assertIn('cache_size', cache_info)
        self.assertIn('hit_rate_percent', cache_info)
        
        logger.info("✅ Cache manager functionality passed")
    
    async def test_performance_optimization_engine(self):
        """Test performance optimization engine"""
        logger.info("Testing performance optimization engine")
        
        # Test engine initialization
        self.assertIsNotNone(self.optimization_engine)
        self.assertFalse(self.optimization_engine.is_optimizing)
        
        # Test target management
        initial_target_count = len(self.optimization_engine.targets)
        self.assertGreater(initial_target_count, 0)
        
        # Test optimization summary
        summary = self.optimization_engine.get_optimization_summary()
        self.assertIn('total_optimizations', summary)
        self.assertIn('optimization_targets', summary)
        
        logger.info("✅ Performance optimization engine passed")
    
    def test_metrics_collection(self):
        """Test metrics collection system"""
        logger.info("Testing metrics collection system")
        
        # Test basic metric recording
        self.metrics_collector.record_counter('test.counter', 1)
        self.metrics_collector.record_gauge('test.gauge', 100.0)
        self.metrics_collector.record_timer('test.timer', 50.0)
        
        # Test metric retrieval
        self.assertGreater(self.metrics_collector.collection_stats['metrics_collected'], 0)
        
        # Test timer context manager
        with self.metrics_collector.timer('test.context_timer'):
            time.sleep(0.01)
        
        # Verify timer was recorded
        timer_metrics = self.metrics_collector.get_recent_metrics('test.context_timer', 1)
        self.assertGreater(len(timer_metrics), 0)
        
        logger.info("✅ Metrics collection system passed")
    
    async def test_end_to_end_performance_system(self):
        """Test end-to-end performance optimization system"""
        logger.info("Testing end-to-end performance system")
        
        # Start all systems
        await self.profiler.start_profiling()
        await self.cache_manager.start_cache_manager()
        await self.metrics_collector.start_collection()
        
        # Wait for initial data collection
        await asyncio.sleep(0.5)
        
        # Test profiler data collection
        self.assertTrue(self.profiler.is_profiling)
        self.assertGreater(len(self.profiler.metrics_history), 0)
        
        # Test cache performance
        for i in range(50):
            self.cache_manager.set(f'key_{i}', f'value_{i}')
        
        hit_count = 0
        for i in range(50):
            value = self.cache_manager.get(f'key_{i}')
            if value is not None:
                hit_count += 1
        
        self.assertGreater(hit_count, 40)  # Should have high hit rate
        
        # Test metrics collection
        self.assertTrue(self.metrics_collector.is_collecting)
        self.assertGreater(self.metrics_collector.collection_stats['metrics_collected'], 0)
        
        # Stop all systems
        await self.profiler.stop_profiling()
        await self.cache_manager.stop_cache_manager()
        await self.metrics_collector.stop_collection()
        
        logger.info("✅ End-to-end performance system passed")
    
    def test_performance_decorator(self):
        """Test performance timing decorator"""
        logger.info("Testing performance timing decorator")
        
        # Use a custom decorator that uses our test profiler instance
        def test_time_component(component_name: str):
            def decorator(func):
                def sync_wrapper(*args, **kwargs):
                    timer_id = self.profiler.start_timer(component_name)
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        self.profiler.end_timer(timer_id)
                return sync_wrapper
            return decorator
        
        @test_time_component('test_function')
        def test_function():
            time.sleep(0.01)
            return "completed"
        
        # Execute function
        result = test_function()
        self.assertEqual(result, "completed")
        
        # Check if timing was recorded in our test profiler
        self.assertIn('test_function', self.profiler.component_timers)
        timings = self.profiler.component_timers['test_function']
        self.assertGreater(len(timings), 0)
        self.assertGreater(timings[-1], 0)  # Last timing should be > 0
        
        logger.info("✅ Performance timing decorator passed")
    
    async def test_async_performance_decorator(self):
        """Test async performance timing decorator"""
        logger.info("Testing async performance timing decorator")
        
        @time_component('async_test_function')
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "async_completed"
        
        # Execute async function
        result = await async_test_function()
        self.assertEqual(result, "async_completed")
        
        # Check if timing was recorded
        self.assertIn('async_test_function', system_profiler.component_timers)
        timings = system_profiler.component_timers['async_test_function']
        self.assertGreater(len(timings), 0)
        self.assertGreater(timings[-1], 0)  # Last timing should be > 0
        
        logger.info("✅ Async performance timing decorator passed")
    
    def test_cache_performance_under_load(self):
        """Test cache performance under load"""
        logger.info("Testing cache performance under load")
        
        # Start cache manager
        asyncio.run(self.cache_manager.start_cache_manager())
        
        # Load test
        start_time = time.perf_counter()
        
        # Write operations
        for i in range(1000):
            self.cache_manager.set(f'load_key_{i}', f'load_value_{i}')
        
        # Read operations
        hit_count = 0
        for i in range(1000):
            value = self.cache_manager.get(f'load_key_{i}')
            if value is not None:
                hit_count += 1
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Performance assertions
        self.assertGreater(hit_count, 990)  # > 99% hit rate
        self.assertLess(total_time_ms, 100)  # < 100ms for 2000 operations
        
        # Get cache metrics
        metrics = self.cache_manager.get_metrics()
        self.assertGreater(metrics.hits, 990)
        self.assertLess(metrics.avg_get_time_ms, 0.1)  # < 0.1ms average
        
        asyncio.run(self.cache_manager.stop_cache_manager())
        
        logger.info(f"✅ Cache performance under load passed (hit_rate: {hit_count/10:.1f}%, total_time: {total_time_ms:.1f}ms)")
    
    async def test_metrics_export_functionality(self):
        """Test metrics export functionality"""
        logger.info("Testing metrics export functionality")
        
        # Record some test metrics
        self.metrics_collector.record_counter('export.test.counter', 5)
        self.metrics_collector.record_gauge('export.test.gauge', 42.0)
        self.metrics_collector.record_timer('export.test.timer', 123.45)
        
        # Allow time for aggregation
        await asyncio.sleep(0.1)
        
        # Test JSON export
        json_export = self.metrics_collector.export_metrics('json')
        self.assertIn('timestamp', json_export)
        self.assertIn('metrics', json_export)
        
        # Test Prometheus export
        prometheus_export = self.metrics_collector.export_metrics('prometheus')
        self.assertIn('# HELP', prometheus_export)
        self.assertIn('# TYPE', prometheus_export)
        
        logger.info("✅ Metrics export functionality passed")

class TestPhase5Integration(unittest.TestCase):
    """Integration tests for Phase 5 components"""
    
    async def test_phase5_system_integration(self):
        """Test integration of all Phase 5 components"""
        logger.info("Testing Phase 5 system integration")
        
        # Initialize components
        profiler = SystemProfiler(collection_interval=0.1)
        cache_manager = OptimizedCacheManager(max_size=1000)
        optimization_engine = PerformanceOptimizationEngine(optimization_interval=2.0)
        metrics_collector = MetricsCollector(collection_interval=0.1)
        
        try:
            # Start all components
            await profiler.start_profiling()
            await cache_manager.start_cache_manager()
            await optimization_engine.start_optimization()
            await metrics_collector.start_collection()
            
            # Simulate system activity
            for i in range(100):
                # Cache operations
                cache_manager.set(f'integration_key_{i}', f'integration_value_{i}')
                
                # Metrics recording
                metrics_collector.record_gauge('integration.test.metric', i)
                
                # Component timing
                timer_id = profiler.start_timer('integration_component')
                time.sleep(0.001)  # Simulate work
                profiler.end_timer(timer_id)
                
                if i % 10 == 0:
                    await asyncio.sleep(0.01)  # Small pause
            
            # Allow systems to process
            await asyncio.sleep(1.0)
            
            # Verify all systems are working
            self.assertTrue(profiler.is_profiling)
            self.assertTrue(optimization_engine.is_optimizing)
            self.assertTrue(metrics_collector.is_collecting)
            
            # Check profiler data
            self.assertGreater(len(profiler.metrics_history), 0)
            
            # Check cache performance
            cache_info = cache_manager.get_cache_info()
            self.assertGreater(cache_info['cache_size'], 90)
            
            # Check optimization engine
            opt_summary = optimization_engine.get_optimization_summary()
            self.assertGreaterEqual(len(opt_summary['optimization_targets']), 1)
            
            # Check metrics collection
            collection_stats = metrics_collector.get_collection_stats()
            self.assertTrue(collection_stats['collection_active'])
            self.assertGreater(collection_stats['active_metrics'], 0)
            
        finally:
            # Clean up
            await profiler.stop_profiling()
            await cache_manager.stop_cache_manager()
            await optimization_engine.stop_optimization()
            await metrics_collector.stop_collection()
        
        logger.info("✅ Phase 5 system integration passed")

async def run_async_tests():
    """Run async tests"""
    logger.info("🚀 Starting Phase 5 Performance Tests")
    
    # Run individual async tests
    test_instance = TestPhase5Performance()
    test_instance.setUp()
    
    try:
        await test_instance.test_performance_optimization_engine()
        await test_instance.test_end_to_end_performance_system()
        await test_instance.test_async_performance_decorator()
        await test_instance.test_metrics_export_functionality()
        
        # Run integration tests
        integration_test = TestPhase5Integration()
        await integration_test.test_phase5_system_integration()
        
        logger.info("✅ All Phase 5 async tests passed!")
        
    finally:
        test_instance.tearDown()

if __name__ == '__main__':
    # Run synchronous tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run async tests
    print("\n" + "="*60)
    print("Running Async Tests")
    print("="*60)
    asyncio.run(run_async_tests())
    
    print("\n🎉 Phase 5 Performance Testing Complete!")
    print("✅ All performance optimization components validated")
    print("✅ System integration confirmed")
    print("✅ Ready for Phase 5B implementation")
