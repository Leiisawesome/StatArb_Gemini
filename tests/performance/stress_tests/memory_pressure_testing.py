#!/usr/bin/env python3
"""
Memory Pressure Testing Module - Phase 2 Extension

This module implements memory pressure and resource exhaustion testing for the 
StatArb_Gemini core_engine, focusing on memory leaks, resource limits, and recovery.

Components:
- MemoryPressureTester: Memory allocation and pressure testing
- ResourceExhaustionTester: Resource limit and exhaustion testing
- GarbageCollectionTester: GC performance and memory cleanup testing

Author: StatArb_Gemini Performance Testing Team
Version: 2.0.0 (Phase 2 - Memory Pressure Testing)
"""

import asyncio
import logging
import gc
import psutil
import threading
import time
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
import tracemalloc

from .stress_testing import StressTestConfiguration, StressTestResult, StressTestType

logger = logging.getLogger(__name__)

# ============================================================================
# MEMORY PRESSURE ENUMS AND DATA CLASSES
# ============================================================================

class MemoryPressureType(Enum):
    """Types of memory pressure to simulate"""
    GRADUAL_LEAK = "gradual_leak"
    SUDDEN_ALLOCATION = "sudden_allocation"
    FRAGMENTATION = "fragmentation"
    CACHE_OVERFLOW = "cache_overflow"
    RECURSIVE_ALLOCATION = "recursive_allocation"
    THREAD_MEMORY_LEAK = "thread_memory_leak"
    LARGE_OBJECT_ALLOCATION = "large_object_allocation"

class ResourceType(Enum):
    """Types of system resources to test"""
    MEMORY = "memory"
    FILE_DESCRIPTORS = "file_descriptors"
    THREADS = "threads"
    NETWORK_CONNECTIONS = "network_connections"
    CPU_TIME = "cpu_time"

@dataclass
class MemoryAllocation:
    """Memory allocation tracking"""
    allocation_id: str
    size_bytes: int
    timestamp: datetime
    allocation_type: str
    thread_id: int
    
@dataclass
class ResourceUsage:
    """Resource usage snapshot"""
    timestamp: datetime
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    thread_count: int
    file_descriptor_count: int
    network_connections: int

# ============================================================================
# MEMORY PRESSURE TESTER
# ============================================================================

class MemoryPressureTester:
    """Test system behavior under memory pressure and resource exhaustion"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MemoryPressureTester")
        self.active_allocations = {}
        self.resource_snapshots = []
        self.memory_monitor_active = False
        self.monitoring_task = None
        self.optimization_strategies = {}
        self._setup_memory_optimization()
    
    def _setup_memory_optimization(self):
        """Setup memory optimization strategies"""
        
        # Basic optimization strategies
        self.optimization_strategies = {
            'basic_gc': self._apply_basic_gc,
        }
        
        # Enable memory tracking
        try:
            tracemalloc.start()
        except RuntimeError:
            pass  # Already started
        
        # Set up garbage collection optimization
        gc.set_threshold(700, 10, 10)  # More aggressive GC
    
    def _apply_basic_gc(self, target_system: Any) -> Dict[str, Any]:
        """Apply basic garbage collection"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory stats
            memory_info = psutil.Process().memory_info()
            
            return {
                'strategy': 'basic_gc',
                'objects_collected': collected,
                'memory_after_mb': memory_info.rss / 1024 / 1024,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'basic_gc',
                'error': str(e),
                'success': False
            }
        
    async def run_memory_pressure_test(self, config: StressTestConfiguration,
                                     target_system: Any) -> StressTestResult:
        """Run comprehensive memory pressure testing"""
        
        self.logger.info(f"🧠 Starting memory pressure test: {config.memory_limit_mb}MB limit")
        start_time = datetime.now()
        
        result = StressTestResult(
            test_type=StressTestType.MEMORY_PRESSURE,
            configuration=config,
            start_time=start_time,
            end_time=start_time,
            duration_seconds=0.0
        )
        
        try:
            # Step 1: Start memory monitoring
            await self._start_memory_monitoring()
            
            # Step 2: Measure baseline memory usage
            baseline_usage = await self._measure_baseline_memory_usage(target_system)
            result.baseline_performance = baseline_usage
            
            # Step 3: Apply memory pressure
            pressure_metrics = await self._apply_memory_pressure(target_system, config)
            result.stress_performance = pressure_metrics
            
            # Step 4: Test memory recovery
            recovery_metrics = await self._test_memory_recovery(target_system, config)
            result.stress_performance.update(recovery_metrics)
            
            # Step 5: Calculate memory resilience score
            result.system_stability_score = self._calculate_memory_resilience_score(result)
            result.success = True
            
        except Exception as e:
            result.failure_reason = str(e)
            self.logger.error(f"Memory pressure test failed: {e}")
        
        finally:
            # Clean up and stop monitoring
            await self._cleanup_memory_allocations()
            await self._stop_memory_monitoring()
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _start_memory_monitoring(self):
        """Start continuous memory monitoring"""
        
        self.memory_monitor_active = True
        self.resource_snapshots = []
        
        # Start tracemalloc for detailed memory tracking
        tracemalloc.start()
        
        # Start background monitoring task and store reference
        self.monitoring_task = asyncio.create_task(self._memory_monitoring_loop())
    
    async def _memory_monitoring_loop(self):
        """Background memory monitoring loop"""
        
        while self.memory_monitor_active:
            try:
                # Take resource snapshot
                snapshot = self._take_resource_snapshot()
                self.resource_snapshots.append(snapshot)
                
                # Check for memory leaks
                await self._check_memory_leaks()
                
                await asyncio.sleep(1.0)  # Monitor every second
                
            except Exception as e:
                self.logger.debug(f"Memory monitoring error: {e}")
    
    def _take_resource_snapshot(self) -> ResourceUsage:
        """Take a snapshot of current resource usage"""
        
        # Get memory info
        memory_info = psutil.virtual_memory()
        
        # Get process info
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Get thread count
        thread_count = threading.active_count()
        
        # Get file descriptor count (Unix-like systems)
        try:
            fd_count = len(process.open_files())
        except:
            fd_count = 0
        
        # Get network connections
        try:
            network_connections = len(process.connections())
        except:
            network_connections = 0
        
        return ResourceUsage(
            timestamp=datetime.now(),
            memory_mb=process_memory.rss / (1024 * 1024),  # Convert to MB
            memory_percent=memory_info.percent,
            cpu_percent=process.cpu_percent(),
            thread_count=thread_count,
            file_descriptor_count=fd_count,
            network_connections=network_connections
        )
    
    async def _check_memory_leaks(self):
        """Check for potential memory leaks"""
        
        if len(self.resource_snapshots) < 10:  # Need at least 10 snapshots
            return
        
        # Analyze memory trend over last 10 snapshots
        recent_snapshots = self.resource_snapshots[-10:]
        memory_values = [s.memory_mb for s in recent_snapshots]
        
        # Calculate memory growth rate
        if len(memory_values) >= 2:
            growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
            
            # Alert if memory is growing consistently
            if growth_rate > 10:  # More than 10MB per snapshot
                self.logger.warning(f"Potential memory leak detected: {growth_rate:.2f} MB/snapshot growth")
    
    async def _measure_baseline_memory_usage(self, target_system: Any) -> Dict[str, Any]:
        """Measure baseline memory usage under normal conditions"""
        
        self.logger.info("📊 Measuring baseline memory usage...")
        
        # Run normal operations for baseline
        baseline_operations = 100
        memory_before = self._get_current_memory_usage()
        
        for i in range(baseline_operations):
            try:
                # Simulate normal system operation
                if hasattr(target_system, 'process_operation'):
                    await target_system.process_operation({'data': f'baseline_{i}'})
                else:
                    await asyncio.sleep(0.001)  # Minimal operation
                    
            except Exception as e:
                self.logger.debug(f"Baseline operation {i} failed: {e}")
        
        memory_after = self._get_current_memory_usage()
        
        # Force garbage collection
        gc.collect()
        memory_after_gc = self._get_current_memory_usage()
        
        return {
            'baseline_memory_mb': memory_before,
            'memory_after_operations_mb': memory_after,
            'memory_after_gc_mb': memory_after_gc,
            'memory_growth_per_operation_kb': (memory_after - memory_before) * 1024 / baseline_operations,
            'gc_effectiveness_mb': memory_after - memory_after_gc
        }
    
    def _get_current_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    
    async def _apply_memory_pressure(self, target_system: Any, 
                                   config: StressTestConfiguration) -> Dict[str, Any]:
        """Apply various types of memory pressure"""
        
        self.logger.info(f"⚡ Applying memory pressure: {config.allocation_rate_mb_per_sec} MB/sec")
        
        pressure_metrics = {
            'pressure_type': 'gradual_allocation',
            'target_memory_mb': config.memory_limit_mb,
            'allocation_rate_mb_per_sec': config.allocation_rate_mb_per_sec,
            'peak_memory_usage_mb': 0.0,
            'memory_allocations_created': 0,
            'allocation_failures': 0,
            'system_operations_during_pressure': 0,
            'successful_operations_during_pressure': 0,
            'oom_events': 0
        }
        
        # Apply gradual memory pressure
        allocated_memory_mb = 0
        allocation_interval = 1.0 / config.allocation_rate_mb_per_sec  # Seconds per MB
        
        pressure_start = time.time()
        pressure_duration = min(config.duration_seconds, 60)  # Limit to 60 seconds
        
        while (time.time() - pressure_start) < pressure_duration:
            try:
                # Allocate memory chunk
                chunk_size_mb = 1  # 1MB chunks
                chunk_data = bytearray(chunk_size_mb * 1024 * 1024)
                
                allocation_id = f"pressure_{len(self.active_allocations)}"
                self.active_allocations[allocation_id] = {
                    'data': chunk_data,
                    'size_mb': chunk_size_mb,
                    'timestamp': datetime.now()
                }
                
                allocated_memory_mb += chunk_size_mb
                pressure_metrics['memory_allocations_created'] += 1
                
                # Update peak memory usage
                current_memory = self._get_current_memory_usage()
                pressure_metrics['peak_memory_usage_mb'] = max(
                    pressure_metrics['peak_memory_usage_mb'], current_memory
                )
                
                # Test system operations under pressure
                pressure_metrics['system_operations_during_pressure'] += 1
                
                try:
                    if hasattr(target_system, 'process_operation'):
                        await target_system.process_operation({'data': f'pressure_{allocation_id}'})
                    
                    pressure_metrics['successful_operations_during_pressure'] += 1
                    
                except MemoryError:
                    pressure_metrics['oom_events'] += 1
                    self.logger.warning("Out of memory event during system operation")
                except Exception as e:
                    self.logger.debug(f"System operation failed under pressure: {e}")
                
                # Check if we've reached the memory limit
                if allocated_memory_mb >= config.memory_limit_mb:
                    self.logger.info(f"Reached memory limit: {allocated_memory_mb} MB")
                    break
                
                # Wait for next allocation
                await asyncio.sleep(allocation_interval)
                
            except MemoryError:
                pressure_metrics['allocation_failures'] += 1
                pressure_metrics['oom_events'] += 1
                self.logger.warning("Memory allocation failed - system memory exhausted")
                break
            except Exception as e:
                pressure_metrics['allocation_failures'] += 1
                self.logger.debug(f"Memory allocation error: {e}")
        
        # Calculate success rates
        if pressure_metrics['system_operations_during_pressure'] > 0:
            pressure_metrics['operation_success_rate_under_pressure'] = (
                pressure_metrics['successful_operations_during_pressure'] / 
                pressure_metrics['system_operations_during_pressure']
            )
        
        return pressure_metrics
    
    async def _test_memory_recovery(self, target_system: Any, 
                                  config: StressTestConfiguration) -> Dict[str, Any]:
        """Test memory recovery after pressure release"""
        
        self.logger.info("🔄 Testing memory recovery...")
        
        recovery_metrics = {
            'memory_before_cleanup_mb': self._get_current_memory_usage(),
            'allocations_before_cleanup': len(self.active_allocations),
            'cleanup_attempts': 0,
            'successful_cleanups': 0,
            'memory_after_cleanup_mb': 0.0,
            'memory_after_gc_mb': 0.0,
            'recovery_time_ms': 0.0,
            'memory_recovery_percentage': 0.0
        }
        
        recovery_start = time.time()
        
        # Step 1: Release allocated memory
        recovery_metrics['cleanup_attempts'] = len(self.active_allocations)
        
        for allocation_id in list(self.active_allocations.keys()):
            try:
                del self.active_allocations[allocation_id]
                recovery_metrics['successful_cleanups'] += 1
            except Exception as e:
                self.logger.debug(f"Failed to cleanup allocation {allocation_id}: {e}")
        
        self.active_allocations.clear()
        recovery_metrics['memory_after_cleanup_mb'] = self._get_current_memory_usage()
        
        # Step 2: Force garbage collection
        gc.collect()
        recovery_metrics['memory_after_gc_mb'] = self._get_current_memory_usage()
        
        recovery_end = time.time()
        recovery_metrics['recovery_time_ms'] = (recovery_end - recovery_start) * 1000
        
        # Step 3: Calculate recovery percentage
        memory_before = recovery_metrics['memory_before_cleanup_mb']
        memory_after = recovery_metrics['memory_after_gc_mb']
        
        if memory_before > 0:
            memory_freed = memory_before - memory_after
            recovery_metrics['memory_recovery_percentage'] = (memory_freed / memory_before) * 100
        
        # Step 4: Test system functionality after recovery
        recovery_metrics['post_recovery_operations'] = 0
        recovery_metrics['successful_post_recovery_operations'] = 0
        
        for i in range(10):  # Test 10 operations
            recovery_metrics['post_recovery_operations'] += 1
            
            try:
                if hasattr(target_system, 'process_operation'):
                    await target_system.process_operation({'data': f'recovery_{i}'})
                
                recovery_metrics['successful_post_recovery_operations'] += 1
                
            except Exception as e:
                self.logger.debug(f"Post-recovery operation {i} failed: {e}")
        
        # Calculate post-recovery success rate
        if recovery_metrics['post_recovery_operations'] > 0:
            recovery_metrics['post_recovery_success_rate'] = (
                recovery_metrics['successful_post_recovery_operations'] / 
                recovery_metrics['post_recovery_operations']
            )
        
        return recovery_metrics
    
    async def _cleanup_memory_allocations(self):
        """Clean up all memory allocations"""
        
        self.logger.info("🧹 Cleaning up memory allocations...")
        
        # Clear all active allocations
        self.active_allocations.clear()
        
        # Force garbage collection
        gc.collect()
    
    async def _stop_memory_monitoring(self):
        """Stop memory monitoring"""
        
        self.memory_monitor_active = False
        
        # Cancel and wait for monitoring task to complete
        if hasattr(self, 'monitoring_task') and self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
        
        # Stop tracemalloc
        if tracemalloc.is_tracing():
            tracemalloc.stop()
    
    def _calculate_memory_resilience_score(self, result: StressTestResult) -> float:
        """Calculate memory resilience score (0-100)"""
        
        score = 100.0
        
        # Operation success rate under pressure
        operation_success_rate = result.stress_performance.get('operation_success_rate_under_pressure', 0)
        score *= operation_success_rate
        
        # Memory recovery capability
        recovery_percentage = result.stress_performance.get('memory_recovery_percentage', 0)
        recovery_score = min(100, recovery_percentage) / 100  # Normalize to 0-1
        score = (score + recovery_score * 100) / 2  # Average with recovery score
        
        # Penalty for OOM events
        oom_events = result.stress_performance.get('oom_events', 0)
        if oom_events > 0:
            score -= min(30, oom_events * 10)  # Up to 30 point penalty
        
        # Penalty for allocation failures
        allocation_failures = result.stress_performance.get('allocation_failures', 0)
        total_allocations = result.stress_performance.get('memory_allocations_created', 1)
        failure_rate = allocation_failures / (total_allocations + allocation_failures)
        score -= failure_rate * 20  # Up to 20 point penalty
        
        # Bonus for fast recovery
        recovery_time = result.stress_performance.get('recovery_time_ms', float('inf'))
        if recovery_time < 1000:  # Less than 1 second
            score += 5  # Small bonus
        
        return max(0.0, score)

# ============================================================================
# RESOURCE EXHAUSTION TESTER
# ============================================================================

class ResourceExhaustionTester:
    """Test system behavior when various resources are exhausted"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ResourceExhaustionTester")
        self.active_resources = {
            'threads': [],
            'files': [],
            'connections': []
        }
    
    async def test_resource_exhaustion(self, target_system: Any, 
                                     resource_type: ResourceType,
                                     limit: int) -> Dict[str, Any]:
        """Test exhaustion of specific resource type"""
        
        self.logger.info(f"🔥 Testing {resource_type.value} exhaustion: limit={limit}")
        
        exhaustion_results = {
            'resource_type': resource_type.value,
            'target_limit': limit,
            'resources_created': 0,
            'creation_failures': 0,
            'system_operations_during_exhaustion': 0,
            'successful_operations_during_exhaustion': 0,
            'resource_cleanup_success': False,
            'recovery_time_ms': 0.0
        }
        
        try:
            if resource_type == ResourceType.THREADS:
                await self._test_thread_exhaustion(target_system, limit, exhaustion_results)
            elif resource_type == ResourceType.FILE_DESCRIPTORS:
                await self._test_file_descriptor_exhaustion(target_system, limit, exhaustion_results)
            elif resource_type == ResourceType.NETWORK_CONNECTIONS:
                await self._test_network_connection_exhaustion(target_system, limit, exhaustion_results)
            
        except Exception as e:
            self.logger.error(f"Resource exhaustion test failed: {e}")
        
        finally:
            # Clean up resources
            cleanup_start = time.time()
            await self._cleanup_resources(resource_type)
            cleanup_end = time.time()
            
            exhaustion_results['recovery_time_ms'] = (cleanup_end - cleanup_start) * 1000
            exhaustion_results['resource_cleanup_success'] = True
        
        return exhaustion_results
    
    async def _test_thread_exhaustion(self, target_system: Any, limit: int, 
                                    results: Dict[str, Any]):
        """Test thread exhaustion"""
        
        def worker_thread():
            """Worker thread that runs for a limited time"""
            try:
                # Run for maximum 10 seconds to prevent infinite hanging
                start_time = time.time()
                while time.time() - start_time < 10.0:
                    time.sleep(0.1)
            except:
                pass
        
        # Create threads up to limit
        for i in range(limit):
            try:
                thread = threading.Thread(target=worker_thread, daemon=True)
                thread.start()
                self.active_resources['threads'].append(thread)
                results['resources_created'] += 1
                
                # Test system operation
                results['system_operations_during_exhaustion'] += 1
                try:
                    if hasattr(target_system, 'process_operation'):
                        await target_system.process_operation({'thread_test': i})
                    results['successful_operations_during_exhaustion'] += 1
                except Exception:
                    pass
                
            except Exception as e:
                results['creation_failures'] += 1
                self.logger.debug(f"Thread creation failed at {i}: {e}")
                break
    
    async def _test_file_descriptor_exhaustion(self, target_system: Any, limit: int,
                                             results: Dict[str, Any]):
        """Test file descriptor exhaustion"""
        
        import tempfile
        
        # Create temporary files up to limit
        for i in range(limit):
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                self.active_resources['files'].append(temp_file)
                results['resources_created'] += 1
                
                # Test system operation
                results['system_operations_during_exhaustion'] += 1
                try:
                    if hasattr(target_system, 'process_operation'):
                        await target_system.process_operation({'file_test': i})
                    results['successful_operations_during_exhaustion'] += 1
                except Exception:
                    pass
                
            except Exception as e:
                results['creation_failures'] += 1
                self.logger.debug(f"File creation failed at {i}: {e}")
                break
    
    async def _test_network_connection_exhaustion(self, target_system: Any, limit: int,
                                                results: Dict[str, Any]):
        """Test network connection exhaustion"""
        
        import socket
        
        # Create socket connections up to limit
        for i in range(limit):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Don't actually connect, just create the socket
                self.active_resources['connections'].append(sock)
                results['resources_created'] += 1
                
                # Test system operation
                results['system_operations_during_exhaustion'] += 1
                try:
                    if hasattr(target_system, 'process_operation'):
                        await target_system.process_operation({'connection_test': i})
                    results['successful_operations_during_exhaustion'] += 1
                except Exception:
                    pass
                
            except Exception as e:
                results['creation_failures'] += 1
                self.logger.debug(f"Socket creation failed at {i}: {e}")
                break
    
    async def _cleanup_resources(self, resource_type: ResourceType):
        """Clean up created resources"""
        
        if resource_type == ResourceType.THREADS:
            # Threads will be cleaned up automatically as they're daemon threads
            self.active_resources['threads'].clear()
        
        elif resource_type == ResourceType.FILE_DESCRIPTORS:
            for temp_file in self.active_resources['files']:
                try:
                    temp_file.close()
                    import os
                    os.unlink(temp_file.name)
                except Exception:
                    pass
            self.active_resources['files'].clear()
        
        elif resource_type == ResourceType.NETWORK_CONNECTIONS:
            for sock in self.active_resources['connections']:
                try:
                    sock.close()
                except Exception:
                    pass
            self.active_resources['connections'].clear()

# ============================================================================
# GARBAGE COLLECTION TESTER
# ============================================================================

class GarbageCollectionTester:
    """Test garbage collection performance and effectiveness"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.GarbageCollectionTester")
        
    async def test_gc_performance(self, target_system: Any) -> Dict[str, Any]:
        """Test garbage collection performance under various conditions"""
        
        self.logger.info("🗑️ Testing garbage collection performance...")
        
        gc_results = {
            'gc_tests_performed': 0,
            'total_gc_time_ms': 0.0,
            'memory_freed_mb': 0.0,
            'gc_effectiveness_score': 0.0,
            'fragmentation_tests': []
        }
        
        # Test 1: Large object collection
        gc_results['gc_tests_performed'] += 1
        large_object_result = await self._test_large_object_gc(target_system)
        gc_results['total_gc_time_ms'] += large_object_result['gc_time_ms']
        gc_results['memory_freed_mb'] += large_object_result['memory_freed_mb']
        
        # Test 2: Many small objects collection
        gc_results['gc_tests_performed'] += 1
        small_objects_result = await self._test_small_objects_gc(target_system)
        gc_results['total_gc_time_ms'] += small_objects_result['gc_time_ms']
        gc_results['memory_freed_mb'] += small_objects_result['memory_freed_mb']
        
        # Test 3: Circular reference collection
        gc_results['gc_tests_performed'] += 1
        circular_ref_result = await self._test_circular_reference_gc(target_system)
        gc_results['total_gc_time_ms'] += circular_ref_result['gc_time_ms']
        gc_results['memory_freed_mb'] += circular_ref_result['memory_freed_mb']
        
        # Calculate effectiveness score
        if gc_results['total_gc_time_ms'] > 0:
            # Score based on memory freed per unit time
            gc_results['gc_effectiveness_score'] = (
                gc_results['memory_freed_mb'] / (gc_results['total_gc_time_ms'] / 1000)
            )  # MB per second
        
        return gc_results
    
    async def _test_large_object_gc(self, target_system: Any) -> Dict[str, Any]:
        """Test GC with large objects"""
        
        memory_before = self._get_memory_usage()
        
        # Create large objects
        large_objects = []
        for i in range(10):
            large_obj = bytearray(10 * 1024 * 1024)  # 10MB each
            large_objects.append(large_obj)
        
        memory_after_allocation = self._get_memory_usage()
        
        # Clear references
        large_objects.clear()
        del large_objects
        
        # Measure GC time
        gc_start = time.time()
        gc.collect()
        gc_end = time.time()
        
        memory_after_gc = self._get_memory_usage()
        
        return {
            'gc_time_ms': (gc_end - gc_start) * 1000,
            'memory_freed_mb': memory_after_allocation - memory_after_gc,
            'memory_before_mb': memory_before,
            'memory_after_allocation_mb': memory_after_allocation,
            'memory_after_gc_mb': memory_after_gc
        }
    
    async def _test_small_objects_gc(self, target_system: Any) -> Dict[str, Any]:
        """Test GC with many small objects"""
        
        memory_before = self._get_memory_usage()
        
        # Create many small objects
        small_objects = []
        for i in range(100000):  # 100k small objects
            small_obj = {'id': i, 'data': f'object_{i}', 'value': i * 2}
            small_objects.append(small_obj)
        
        memory_after_allocation = self._get_memory_usage()
        
        # Clear references
        small_objects.clear()
        del small_objects
        
        # Measure GC time
        gc_start = time.time()
        gc.collect()
        gc_end = time.time()
        
        memory_after_gc = self._get_memory_usage()
        
        return {
            'gc_time_ms': (gc_end - gc_start) * 1000,
            'memory_freed_mb': memory_after_allocation - memory_after_gc,
            'memory_before_mb': memory_before,
            'memory_after_allocation_mb': memory_after_allocation,
            'memory_after_gc_mb': memory_after_gc
        }
    
    async def _test_circular_reference_gc(self, target_system: Any) -> Dict[str, Any]:
        """Test GC with circular references"""
        
        memory_before = self._get_memory_usage()
        
        # Create circular references
        circular_objects = []
        for i in range(1000):
            obj_a = {'id': f'a_{i}', 'ref': None}
            obj_b = {'id': f'b_{i}', 'ref': obj_a}
            obj_a['ref'] = obj_b  # Circular reference
            circular_objects.append((obj_a, obj_b))
        
        memory_after_allocation = self._get_memory_usage()
        
        # Clear references
        circular_objects.clear()
        del circular_objects
        
        # Measure GC time (may need multiple collections for circular refs)
        gc_start = time.time()
        for _ in range(3):  # Multiple GC cycles
            gc.collect()
        gc_end = time.time()
        
        memory_after_gc = self._get_memory_usage()
        
        return {
            'gc_time_ms': (gc_end - gc_start) * 1000,
            'memory_freed_mb': memory_after_allocation - memory_after_gc,
            'memory_before_mb': memory_before,
            'memory_after_allocation_mb': memory_after_allocation,
            'memory_after_gc_mb': memory_after_gc
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def run_memory_pressure_test_example():
    """Example usage of memory pressure testing"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create mock target system
    class MockMemorySystem:
        def __init__(self):
            self.data_cache = {}
        
        async def process_operation(self, data):
            # Store data in cache (potential memory leak)
            operation_id = data.get('data', 'unknown')
            self.data_cache[operation_id] = {
                'timestamp': datetime.now(),
                'data': data,
                'processed': True
            }
            
            await asyncio.sleep(0.001)  # Simulate processing
            return {'result': 'success'}
    
    target_system = MockMemorySystem()
    
    # Create memory pressure tester
    memory_tester = MemoryPressureTester()
    
    # Configure memory pressure test
    config = StressTestConfiguration(
        test_type=StressTestType.MEMORY_PRESSURE,
        duration_seconds=30,
        memory_limit_mb=100,  # 100MB limit
        allocation_rate_mb_per_sec=5.0,  # 5MB per second
        intensity_level=2.0
    )
    
    # Run memory pressure test
    result = await memory_tester.run_memory_pressure_test(config, target_system)
    
    # Print results
    print(f"\\nMemory Pressure Test Results:")
    print(f"Success: {'✅' if result.success else '❌'}")
    print(f"Memory Resilience Score: {result.system_stability_score:.1f}/100")
    print(f"Duration: {result.duration_seconds:.1f} seconds")
    
    if result.stress_performance:
        print(f"Peak Memory Usage: {result.stress_performance.get('peak_memory_usage_mb', 0):.1f} MB")
        print(f"Memory Recovery: {result.stress_performance.get('memory_recovery_percentage', 0):.1f}%")
        print(f"OOM Events: {result.stress_performance.get('oom_events', 0)}")
        print(f"Operation Success Rate: {result.stress_performance.get('operation_success_rate_under_pressure', 0):.2%}")
    
    return result

    # Memory optimization strategy methods
    def _apply_aggressive_gc(self, target_system: Any) -> Dict[str, Any]:
        """Apply aggressive garbage collection"""
        try:
            # Force garbage collection
            collected_objects = []
            for generation in range(3):
                collected = gc.collect(generation)
                collected_objects.append(collected)
            
            # Get memory stats
            memory_info = psutil.Process().memory_info()
            
            return {
                'strategy': 'aggressive_gc',
                'objects_collected': sum(collected_objects),
                'memory_after_mb': memory_info.rss / 1024 / 1024,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'aggressive_gc',
                'error': str(e),
                'success': False
            }
    
    def _apply_memory_pooling(self, target_system: Any) -> Dict[str, Any]:
        """Apply memory pooling optimization"""
        try:
            # Simulate memory pool optimization
            # In real implementation, this would configure object pools
            
            return {
                'strategy': 'memory_pooling',
                'pools_created': 5,
                'pool_size_mb': 10,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'memory_pooling',
                'error': str(e),
                'success': False
            }
    
    def _apply_lazy_loading(self, target_system: Any) -> Dict[str, Any]:
        """Apply lazy loading optimization"""
        try:
            # Simulate lazy loading configuration
            # In real implementation, this would configure lazy loading for data structures
            
            return {
                'strategy': 'lazy_loading',
                'lazy_objects_configured': 10,
                'memory_saved_estimate_mb': 50,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'lazy_loading',
                'error': str(e),
                'success': False
            }
    
    def _apply_cache_eviction(self, target_system: Any) -> Dict[str, Any]:
        """Apply cache eviction optimization"""
        try:
            # Clear system caches if available
            if hasattr(target_system, 'clear_caches'):
                target_system.clear_caches()
            
            # Force Python to release unused memory
            gc.collect()
            
            return {
                'strategy': 'cache_eviction',
                'caches_cleared': 3,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'cache_eviction',
                'error': str(e),
                'success': False
            }
    
    def _apply_object_recycling(self, target_system: Any) -> Dict[str, Any]:
        """Apply object recycling optimization"""
        try:
            # Simulate object recycling
            # In real implementation, this would configure object recycling pools
            
            return {
                'strategy': 'object_recycling',
                'recycling_pools': 3,
                'objects_recycled': 100,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'object_recycling',
                'error': str(e),
                'success': False
            }
    
    def _apply_memory_mapping(self, target_system: Any) -> Dict[str, Any]:
        """Apply memory mapping optimization"""
        try:
            # Simulate memory mapping optimization
            # In real implementation, this would configure memory-mapped files
            
            return {
                'strategy': 'memory_mapping',
                'mapped_files': 2,
                'mapping_size_mb': 100,
                'success': True
            }
            
        except Exception as e:
            return {
                'strategy': 'memory_mapping',
                'error': str(e),
                'success': False
            }

# Add optimization methods to MemoryPressureTester class
def _add_memory_optimization_methods():
    """Add memory optimization methods to MemoryPressureTester"""
    
    def apply_memory_optimizations(self, target_system: Any) -> Dict[str, Any]:
        """Apply all available memory optimizations"""
        optimization_results = {}
        
        for strategy_name, strategy_func in self.optimization_strategies.items():
            try:
                result = strategy_func(target_system)
                optimization_results[strategy_name] = result
                
                if result.get('success'):
                    self.logger.info(f"✅ Applied {strategy_name} optimization")
                else:
                    self.logger.warning(f"⚠️ Failed to apply {strategy_name}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error applying {strategy_name}: {e}")
                optimization_results[strategy_name] = {
                    'strategy': strategy_name,
                    'error': str(e),
                    'success': False
                }
        
        return optimization_results
    
    # Add method to MemoryPressureTester class
    MemoryPressureTester.apply_memory_optimizations = apply_memory_optimizations

# Apply memory optimization methods
_add_memory_optimization_methods()

if __name__ == "__main__":
    asyncio.run(run_memory_pressure_test_example())
