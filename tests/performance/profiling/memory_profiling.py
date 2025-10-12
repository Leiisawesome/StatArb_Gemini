"""
Advanced Memory Profiling Framework for Core Engine Components

This module provides comprehensive memory usage analysis, leak detection, and
optimization recommendations for trading system components with focus on
real-time performance and memory efficiency.
"""

import gc
import sys
import time
import psutil
import threading
import tracemalloc
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import asyncio
import weakref
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time"""
    timestamp: datetime
    component_name: str
    operation_name: str
    
    # Process-level memory metrics
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    shared_mb: float  # Shared memory
    
    # Python-specific metrics
    python_objects_count: int
    python_memory_mb: float
    gc_collections: Dict[int, int]  # GC generation -> collection count
    
    # Component-specific metrics
    component_objects: Dict[str, int]  # Object type -> count
    large_objects_mb: float  # Objects > 1MB
    
    # Performance indicators
    cpu_percent: float
    memory_percent: float
    
    # Context information
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryLeak:
    """Detected memory leak information"""
    component_name: str
    object_type: str
    leak_rate_mb_per_sec: float
    total_leaked_mb: float
    detection_confidence: float
    first_detected: datetime
    last_updated: datetime
    stack_trace: List[str]
    recommendations: List[str]

@dataclass
class MemoryAnalysis:
    """Comprehensive memory analysis results"""
    component_name: str
    analysis_period: timedelta
    
    # Memory usage statistics
    peak_memory_mb: float
    average_memory_mb: float
    memory_growth_mb: float
    memory_volatility: float
    
    # Leak detection
    detected_leaks: List[MemoryLeak]
    leak_probability: float
    
    # Optimization opportunities
    optimization_recommendations: List[str]
    memory_efficiency_score: float  # 0-100
    
    # Garbage collection analysis
    gc_pressure: float
    gc_efficiency: float

class MemoryProfiler:
    """Advanced memory profiler for trading system components"""
    
    def __init__(self, snapshot_interval: float = 1.0, max_snapshots: int = 10000):
        self.snapshots: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_snapshots))
        self.active_measurements: Dict[str, datetime] = {}
        self.object_trackers: Dict[str, weakref.WeakSet] = defaultdict(weakref.WeakSet)
        self.lock = threading.Lock()
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        
        # Start tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            
        # Initialize baseline metrics
        self.baseline_memory = self._get_current_memory_usage()
        
    def _get_current_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage metrics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'shared_mb': getattr(memory_info, 'shared', 0) / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent()
        }
    
    def _get_python_memory_stats(self) -> Dict[str, Any]:
        """Get Python-specific memory statistics"""
        # Get object counts by type
        object_counts = defaultdict(int)
        total_objects = 0
        
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            object_counts[obj_type] += 1
            total_objects += 1
            
        # Get GC statistics
        gc_stats = {}
        for i in range(3):  # Python has 3 GC generations
            gc_stats[i] = gc.get_count()[i]
            
        # Get tracemalloc statistics if available
        python_memory_mb = 0.0
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            python_memory_mb = current / 1024 / 1024
            
        return {
            'total_objects': total_objects,
            'object_counts': dict(object_counts),
            'gc_stats': gc_stats,
            'python_memory_mb': python_memory_mb
        }
    
    def _calculate_large_objects_size(self) -> float:
        """Calculate total size of large objects (>1MB)"""
        large_objects_size = 0.0
        
        for obj in gc.get_objects():
            try:
                obj_size = sys.getsizeof(obj)
                if obj_size > 1024 * 1024:  # 1MB threshold
                    large_objects_size += obj_size
            except (TypeError, AttributeError):
                continue
                
        return large_objects_size / 1024 / 1024  # Convert to MB
    
    def take_snapshot(self, component_name: str, operation_name: str, 
                     context: Dict[str, Any] = None) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        timestamp = datetime.now()
        
        # Get system memory metrics
        memory_metrics = self._get_current_memory_usage()
        
        # Get Python memory statistics
        python_stats = self._get_python_memory_stats()
        
        # Calculate large objects size
        large_objects_mb = self._calculate_large_objects_size()
        
        # Create snapshot
        snapshot = MemorySnapshot(
            timestamp=timestamp,
            component_name=component_name,
            operation_name=operation_name,
            rss_mb=memory_metrics['rss_mb'],
            vms_mb=memory_metrics['vms_mb'],
            shared_mb=memory_metrics['shared_mb'],
            python_objects_count=python_stats['total_objects'],
            python_memory_mb=python_stats['python_memory_mb'],
            gc_collections=python_stats['gc_stats'],
            component_objects=python_stats['object_counts'],
            large_objects_mb=large_objects_mb,
            cpu_percent=memory_metrics['cpu_percent'],
            memory_percent=memory_metrics['memory_percent'],
            context=context or {}
        )
        
        # Store snapshot
        key = f"{component_name}::{operation_name}"
        with self.lock:
            self.snapshots[key].append(snapshot)
            
        return snapshot
    
    def start_monitoring(self, component_name: str, operation_name: str) -> str:
        """Start continuous memory monitoring for a component operation"""
        monitoring_id = f"{component_name}::{operation_name}::{time.time()}"
        
        with self.lock:
            self.active_measurements[monitoring_id] = datetime.now()
            
        return monitoring_id
    
    def stop_monitoring(self, monitoring_id: str) -> Optional[List[MemorySnapshot]]:
        """Stop memory monitoring and return collected snapshots"""
        with self.lock:
            start_time = self.active_measurements.pop(monitoring_id, None)
            
        if start_time is None:
            return None
            
        # Parse monitoring ID
        parts = monitoring_id.split("::")
        component_name, operation_name = parts[0], parts[1]
        key = f"{component_name}::{operation_name}"
        
        # Return snapshots from the monitoring period
        with self.lock:
            snapshots = [s for s in self.snapshots[key] if s.timestamp >= start_time]
            
        return snapshots
    
    def detect_memory_leaks(self, component_name: str, operation_name: str, 
                          min_samples: int = 100) -> List[MemoryLeak]:
        """Detect potential memory leaks using statistical analysis"""
        key = f"{component_name}::{operation_name}"
        
        with self.lock:
            snapshots = list(self.snapshots.get(key, []))
            
        if len(snapshots) < min_samples:
            return []
            
        detected_leaks = []
        
        # Analyze RSS memory growth
        rss_values = [s.rss_mb for s in snapshots]
        if len(rss_values) > 10:
            # Calculate linear regression to detect consistent growth
            x = np.arange(len(rss_values))
            slope, intercept = np.polyfit(x, rss_values, 1)
            
            # If slope is positive and significant, it might be a leak
            if slope > 0.1:  # Growing by >0.1 MB per measurement
                correlation = np.corrcoef(x, rss_values)[0, 1]
                
                if correlation > 0.7:  # Strong positive correlation
                    leak = MemoryLeak(
                        component_name=component_name,
                        object_type="RSS_Memory",
                        leak_rate_mb_per_sec=slope * (1.0 / self.snapshot_interval),
                        total_leaked_mb=rss_values[-1] - rss_values[0],
                        detection_confidence=correlation,
                        first_detected=snapshots[0].timestamp,
                        last_updated=snapshots[-1].timestamp,
                        stack_trace=[],
                        recommendations=[
                            "Monitor object creation and destruction",
                            "Check for circular references",
                            "Verify proper cleanup in finally blocks"
                        ]
                    )
                    detected_leaks.append(leak)
        
        # Analyze Python object count growth
        for obj_type in ['dict', 'list', 'DataFrame', 'ndarray']:
            obj_counts = []
            for snapshot in snapshots:
                count = snapshot.component_objects.get(obj_type, 0)
                obj_counts.append(count)
                
            if len(obj_counts) > 10 and max(obj_counts) > 1000:
                x = np.arange(len(obj_counts))
                slope, _ = np.polyfit(x, obj_counts, 1)
                
                if slope > 1.0:  # Growing by >1 object per measurement
                    correlation = np.corrcoef(x, obj_counts)[0, 1]
                    
                    if correlation > 0.6:
                        leak = MemoryLeak(
                            component_name=component_name,
                            object_type=obj_type,
                            leak_rate_mb_per_sec=slope * 0.001,  # Estimate
                            total_leaked_mb=(obj_counts[-1] - obj_counts[0]) * 0.001,
                            detection_confidence=correlation,
                            first_detected=snapshots[0].timestamp,
                            last_updated=snapshots[-1].timestamp,
                            stack_trace=[],
                            recommendations=[
                                f"Check {obj_type} object lifecycle management",
                                f"Verify {obj_type} objects are properly released",
                                f"Consider using weak references for {obj_type} caches"
                            ]
                        )
                        detected_leaks.append(leak)
        
        return detected_leaks
    
    def analyze_memory_usage(self, component_name: str, operation_name: str) -> Optional[MemoryAnalysis]:
        """Perform comprehensive memory usage analysis"""
        key = f"{component_name}::{operation_name}"
        
        with self.lock:
            snapshots = list(self.snapshots.get(key, []))
            
        if len(snapshots) < 10:
            return None
            
        # Calculate basic statistics
        rss_values = [s.rss_mb for s in snapshots]
        peak_memory_mb = max(rss_values)
        average_memory_mb = np.mean(rss_values)
        memory_growth_mb = rss_values[-1] - rss_values[0]
        memory_volatility = np.std(rss_values)
        
        # Detect leaks
        detected_leaks = self.detect_memory_leaks(component_name, operation_name)
        leak_probability = min(len(detected_leaks) * 0.3, 1.0)
        
        # Calculate GC pressure
        gc_counts = [sum(s.gc_collections.values()) for s in snapshots]
        gc_pressure = (gc_counts[-1] - gc_counts[0]) / len(snapshots) if len(gc_counts) > 1 else 0
        
        # Calculate memory efficiency score
        efficiency_factors = []
        
        # Factor 1: Memory stability (lower volatility is better)
        stability_score = max(0, 100 - (memory_volatility * 10))
        efficiency_factors.append(stability_score)
        
        # Factor 2: Leak absence (no leaks is better)
        leak_score = max(0, 100 - (len(detected_leaks) * 20))
        efficiency_factors.append(leak_score)
        
        # Factor 3: GC efficiency (lower pressure is better)
        gc_score = max(0, 100 - (gc_pressure * 5))
        efficiency_factors.append(gc_score)
        
        memory_efficiency_score = np.mean(efficiency_factors)
        
        # Generate optimization recommendations
        recommendations = []
        
        if memory_volatility > 10:
            recommendations.append("High memory volatility detected - consider object pooling")
            
        if len(detected_leaks) > 0:
            recommendations.append("Potential memory leaks detected - review object lifecycle")
            
        if gc_pressure > 5:
            recommendations.append("High GC pressure - optimize object creation patterns")
            
        if peak_memory_mb > average_memory_mb * 2:
            recommendations.append("Memory spikes detected - implement memory budgeting")
            
        # Calculate analysis period
        analysis_period = snapshots[-1].timestamp - snapshots[0].timestamp
        
        return MemoryAnalysis(
            component_name=component_name,
            analysis_period=analysis_period,
            peak_memory_mb=peak_memory_mb,
            average_memory_mb=average_memory_mb,
            memory_growth_mb=memory_growth_mb,
            memory_volatility=memory_volatility,
            detected_leaks=detected_leaks,
            leak_probability=leak_probability,
            optimization_recommendations=recommendations,
            memory_efficiency_score=memory_efficiency_score,
            gc_pressure=gc_pressure,
            gc_efficiency=100 - min(gc_pressure * 10, 100)
        )
    
    def generate_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory usage report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'baseline_memory_mb': self.baseline_memory['rss_mb'],
            'current_memory_mb': self._get_current_memory_usage()['rss_mb'],
            'components': {}
        }
        
        total_leaks = 0
        total_efficiency = []
        
        for key in self.snapshots.keys():
            component_name, operation_name = key.split("::", 1)
            analysis = self.analyze_memory_usage(component_name, operation_name)
            
            if analysis:
                if component_name not in report['components']:
                    report['components'][component_name] = {}
                    
                report['components'][component_name][operation_name] = {
                    'memory_statistics': {
                        'peak_mb': round(analysis.peak_memory_mb, 2),
                        'average_mb': round(analysis.average_memory_mb, 2),
                        'growth_mb': round(analysis.memory_growth_mb, 2),
                        'volatility': round(analysis.memory_volatility, 2)
                    },
                    'leak_detection': {
                        'detected_leaks': len(analysis.detected_leaks),
                        'leak_probability': round(analysis.leak_probability, 2),
                        'leak_details': [
                            {
                                'object_type': leak.object_type,
                                'leak_rate_mb_per_sec': round(leak.leak_rate_mb_per_sec, 4),
                                'confidence': round(leak.detection_confidence, 2)
                            }
                            for leak in analysis.detected_leaks
                        ]
                    },
                    'performance_metrics': {
                        'efficiency_score': round(analysis.memory_efficiency_score, 1),
                        'gc_pressure': round(analysis.gc_pressure, 2),
                        'gc_efficiency': round(analysis.gc_efficiency, 1)
                    },
                    'recommendations': analysis.optimization_recommendations
                }
                
                total_leaks += len(analysis.detected_leaks)
                total_efficiency.append(analysis.memory_efficiency_score)
        
        # Add summary statistics
        report['summary'] = {
            'total_components_analyzed': len(report['components']),
            'total_memory_leaks_detected': total_leaks,
            'average_efficiency_score': round(np.mean(total_efficiency), 1) if total_efficiency else 0,
            'memory_growth_mb': round(report['current_memory_mb'] - report['baseline_memory_mb'], 2)
        }
        
        return report

class ComponentMemoryTester:
    """Specialized memory tester for core engine components"""
    
    def __init__(self, profiler: MemoryProfiler):
        self.profiler = profiler
        
    async def test_data_manager_memory(self, data_manager, symbols: List[str], iterations: int = 100):
        """Test DataManager memory usage patterns"""
        logger.info(f"🧠 Testing DataManager memory usage with {iterations} iterations...")
        
        monitoring_id = self.profiler.start_monitoring("DataManager", "bulk_operations")
        
        try:
            for i in range(iterations):
                # Take snapshot before operations
                self.profiler.take_snapshot("DataManager", "pre_operation", {"iteration": i})
                
                # Perform memory-intensive operations
                for symbol in symbols:
                    data_manager.get_market_data(symbol)
                    # Use proper date parameters for get_historical_data
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)  # 30 days of data
                    data_manager.get_historical_data(symbol, start_date, end_date, "1min")
                    
                # Force garbage collection periodically
                if i % 20 == 0:
                    gc.collect()
                    self.profiler.take_snapshot("DataManager", "post_gc", {"iteration": i})
                    
                if i % 10 == 0:
                    logger.info(f"  Completed {i}/{iterations} DataManager memory tests")
                    
        finally:
            self.profiler.stop_monitoring(monitoring_id)
    
    async def test_strategy_manager_memory(self, strategy_manager, symbols: List[str], iterations: int = 50):
        """Test StrategyManager memory usage during signal generation"""
        logger.info(f"🧠 Testing StrategyManager memory usage with {iterations} iterations...")
        
        monitoring_id = self.profiler.start_monitoring("StrategyManager", "signal_generation")
        
        try:
            for i in range(iterations):
                # Take snapshot before signal generation
                self.profiler.take_snapshot("StrategyManager", "pre_signals", {"iteration": i})
                
                # Generate signals (memory intensive)
                signals = await strategy_manager.generate_signals(symbols)
                
                # Take snapshot after signal generation
                self.profiler.take_snapshot("StrategyManager", "post_signals", {
                    "iteration": i,
                    "signals_generated": len(signals) if signals else 0
                })
                
                # Cleanup signals to test memory release
                del signals
                
                if i % 10 == 0:
                    gc.collect()
                    logger.info(f"  Completed {i}/{iterations} StrategyManager memory tests")
                    
        finally:
            self.profiler.stop_monitoring(monitoring_id)
    
    async def test_portfolio_manager_memory(self, portfolio_manager, iterations: int = 200):
        """Test PortfolioManager memory usage during position updates"""
        logger.info(f"🧠 Testing PortfolioManager memory usage with {iterations} iterations...")
        
        monitoring_id = self.profiler.start_monitoring("PortfolioManager", "position_updates")
        
        try:
            for i in range(iterations):
                # Simulate position updates
                symbol = f"TEST{i % 10}"  # Rotate through 10 test symbols
                
                self.profiler.take_snapshot("PortfolioManager", "pre_update", {"iteration": i})
                
                # Update position (creates internal data structures)
                await portfolio_manager.update_position(symbol, "buy", 100, 150.0)
                
                self.profiler.take_snapshot("PortfolioManager", "post_update", {"iteration": i})
                
                if i % 25 == 0:
                    logger.info(f"  Completed {i}/{iterations} PortfolioManager memory tests")
                    
        finally:
            self.profiler.stop_monitoring(monitoring_id)

# Context manager for memory monitoring
class MemoryMonitoringContext:
    """Context manager for automatic memory monitoring"""
    
    def __init__(self, profiler: MemoryProfiler, component_name: str, operation_name: str):
        self.profiler = profiler
        self.component_name = component_name
        self.operation_name = operation_name
        self.monitoring_id = None
        
    def __enter__(self):
        self.monitoring_id = self.profiler.start_monitoring(
            self.component_name, self.operation_name
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.monitoring_id:
            self.profiler.stop_monitoring(self.monitoring_id)

if __name__ == "__main__":
    # Example usage
    async def example_memory_test():
        profiler = MemoryProfiler()
        
        # Simulate memory usage
        data_list = []
        
        with MemoryMonitoringContext(profiler, "TestComponent", "memory_growth"):
            for i in range(1000):
                # Simulate memory allocation
                data_list.append(np.random.random(1000))
                
                if i % 100 == 0:
                    profiler.take_snapshot("TestComponent", "allocation", {"iteration": i})
                    
        # Analyze memory usage
        analysis = profiler.analyze_memory_usage("TestComponent", "memory_growth")
        if analysis:
            print(f"Peak memory: {analysis.peak_memory_mb:.2f} MB")
            print(f"Memory growth: {analysis.memory_growth_mb:.2f} MB")
            print(f"Efficiency score: {analysis.memory_efficiency_score:.1f}")
            print(f"Detected leaks: {len(analysis.detected_leaks)}")
    
    asyncio.run(example_memory_test())
