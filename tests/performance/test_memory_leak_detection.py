"""
Memory Profiling and Leak Detection Suite - Week 3
Tests for memory usage patterns and leak detection
"""

import pytest
import asyncio
import gc
import tracemalloc
import sys
from pathlib import Path
from typing import Dict, List, Any
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.trading.strategies.manager import StrategyManager


class MemoryProfiler:
    """Advanced memory profiling utilities"""
    
    def __init__(self):
        self.snapshots = []
        self.baseline_memory = 0
    
    def start_profiling(self):
        """Start memory profiling"""
        gc.collect()  # Clear any existing garbage
        tracemalloc.start()
        self.baseline_memory = self.get_current_memory()
    
    def take_snapshot(self):
        """Take a memory snapshot"""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append(snapshot)
        return self.get_current_memory()
    
    def get_current_memory(self) -> float:
        """Get current memory usage in MB"""
        current, peak = tracemalloc.get_traced_memory()
        return current / (1024 * 1024)  # Convert to MB
    
    def stop_profiling(self):
        """Stop memory profiling"""
        tracemalloc.stop()
    
    def analyze_growth(self) -> Dict[str, Any]:
        """Analyze memory growth over time"""
        if len(self.snapshots) < 2:
            return {"error": "Not enough snapshots for analysis"}
        
        # Compare first and last snapshot
        stats = self.snapshots[-1].compare_to(self.snapshots[0], 'lineno')
        
        # Get top memory increases
        top_increases = []
        for stat in stats[:10]:  # Top 10
            top_increases.append({
                "file": stat.traceback.format()[0],
                "size_diff_kb": stat.size_diff / 1024,
                "count_diff": stat.count_diff
            })
        
        return {
            "top_increases": top_increases,
            "total_snapshots": len(self.snapshots)
        }
    
    def detect_leak(self, threshold_mb: float = 10.0) -> bool:
        """Detect potential memory leak based on growth pattern"""
        if not self.snapshots:
            return False
        
        # Get memory at each snapshot
        memories = []
        for snapshot in self.snapshots:
            size = sum(stat.size for stat in snapshot.statistics('lineno'))
            memories.append(size / (1024 * 1024))  # Convert to MB
        
        if len(memories) < 3:
            return False
        
        # Check if memory is consistently increasing
        growth = memories[-1] - memories[0]
        return growth > threshold_mb


@pytest.mark.asyncio
class TestMemoryUsagePatterns:
    """Test memory usage patterns under various conditions"""
    
    async def test_risk_manager_memory_stability(self):
        """Test RiskManager memory usage remains stable over time"""
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        memory_readings = []
        iterations = 1000
        
        # Take baseline
        initial_memory = profiler.take_snapshot()
        memory_readings.append(initial_memory)
        
        print("\n" + "="*60)
        print("RISK MANAGER MEMORY STABILITY TEST")
        print("="*60)
        print(f"Initial Memory: {initial_memory:.2f} MB")
        
        # Perform operations and measure memory
        for i in range(iterations):
            await risk_manager.check_position_risk(
                symbol="AAPL",
                quantity=100,
                side="buy",
                price=150.0
            )
            
            # Take snapshot every 100 iterations
            if (i + 1) % 100 == 0:
                gc.collect()  # Force garbage collection
                memory = profiler.take_snapshot()
                memory_readings.append(memory)
                print(f"Iteration {i+1:4d}: {memory:.2f} MB "
                      f"(Δ {memory - initial_memory:+.2f} MB)")
        
        final_memory = memory_readings[-1]
        memory_growth = final_memory - initial_memory
        
        print(f"\nFinal Memory:   {final_memory:.2f} MB")
        print(f"Memory Growth:  {memory_growth:+.2f} MB")
        print(f"Growth Rate:    {memory_growth/iterations*1000:.4f} MB/1000 ops")
        
        # Check for memory leak
        leak_detected = profiler.detect_leak(threshold_mb=5.0)
        print(f"Leak Detected:  {leak_detected}")
        
        if leak_detected:
            analysis = profiler.analyze_growth()
            print("\nTop Memory Increases:")
            for inc in analysis['top_increases'][:5]:
                print(f"  {inc['file']}: +{inc['size_diff_kb']:.2f} KB")
        
        print("="*60)
        
        # Assertions
        assert not leak_detected, "Memory leak detected in RiskManager"
        assert memory_growth < 10.0, f"Memory growth {memory_growth:.2f} MB exceeds 10 MB"
        
        await risk_manager.shutdown()
        profiler.stop_profiling()
    
    async def test_orchestrator_memory_under_load(self):
        """Test Orchestrator memory usage under sustained load"""
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        orchestrator = HierarchicalSystemOrchestrator()
        await orchestrator.initialize()
        
        initial_memory = profiler.take_snapshot()
        
        print("\n" + "="*60)
        print("ORCHESTRATOR MEMORY UNDER LOAD TEST")
        print("="*60)
        print(f"Initial Memory: {initial_memory:.2f} MB")
        
        # Simulate sustained operations
        operations = 5000
        batch_size = 100
        memory_samples = []
        
        for batch_start in range(0, operations, batch_size):
            # Execute batch
            tasks = []
            for _ in range(batch_size):
                task = orchestrator.get_component("risk_manager")
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sample memory
            if (batch_start + batch_size) % 500 == 0:
                gc.collect()
                memory = profiler.take_snapshot()
                memory_samples.append(memory)
                print(f"Operations {batch_start + batch_size:5d}: "
                      f"{memory:.2f} MB (Δ {memory - initial_memory:+.2f} MB)")
        
        final_memory = memory_samples[-1]
        
        # Calculate memory statistics
        memory_changes = [m - initial_memory for m in memory_samples]
        avg_growth = statistics.mean(memory_changes)
        max_growth = max(memory_changes)
        
        print(f"\nFinal Memory:   {final_memory:.2f} MB")
        print(f"Avg Growth:     {avg_growth:+.2f} MB")
        print(f"Max Growth:     {max_growth:+.2f} MB")
        print(f"Leak Detected:  {profiler.detect_leak(threshold_mb=10.0)}")
        print("="*60)
        
        # Memory should remain stable
        assert not profiler.detect_leak(threshold_mb=10.0)
        assert max_growth < 15.0, f"Max memory growth {max_growth:.2f} MB too high"
        
        await orchestrator.shutdown()
        profiler.stop_profiling()
    
    async def test_memory_recovery_after_stress(self):
        """Test memory is properly recovered after stress period"""
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        # Baseline memory
        gc.collect()
        baseline = profiler.take_snapshot()
        
        print("\n" + "="*60)
        print("MEMORY RECOVERY TEST")
        print("="*60)
        print(f"Baseline Memory: {baseline:.2f} MB")
        
        # Stress phase: Heavy operations
        print("\nStress Phase: 2000 operations...")
        for _ in range(2000):
            await risk_manager.check_position_risk(
                symbol="AAPL",
                quantity=100,
                side="buy",
                price=150.0
            )
        
        stress_memory = profiler.take_snapshot()
        print(f"Peak Memory:     {stress_memory:.2f} MB "
              f"(Δ {stress_memory - baseline:+.2f} MB)")
        
        # Recovery phase: Allow GC to clean up
        print("\nRecovery Phase: Garbage collection...")
        gc.collect()
        await asyncio.sleep(1)  # Allow async cleanup
        gc.collect()
        
        recovered_memory = profiler.take_snapshot()
        recovery_rate = ((stress_memory - recovered_memory) / 
                        (stress_memory - baseline) * 100)
        
        print(f"Recovered Memory: {recovered_memory:.2f} MB "
              f"(Δ {recovered_memory - baseline:+.2f} MB)")
        print(f"Recovery Rate:    {recovery_rate:.2f}%")
        print("="*60)
        
        # Should recover at least 70% of memory
        assert recovery_rate >= 70.0, \
            f"Poor memory recovery: only {recovery_rate:.2f}%"
        
        # Should be close to baseline (within 5 MB)
        assert abs(recovered_memory - baseline) < 5.0, \
            "Memory not returning to baseline"
        
        await risk_manager.shutdown()
        profiler.stop_profiling()


@pytest.mark.asyncio
class TestMemoryLeakDetection:
    """Advanced memory leak detection tests"""
    
    async def test_long_running_leak_detection(self):
        """Run long-duration test to detect slow memory leaks"""
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        print("\n" + "="*60)
        print("LONG-RUNNING LEAK DETECTION TEST")
        print("="*60)
        
        # Run for 10 cycles with memory checks
        memory_timeline = []
        cycles = 10
        ops_per_cycle = 500
        
        for cycle in range(cycles):
            # Perform operations
            for _ in range(ops_per_cycle):
                await risk_manager.check_position_risk(
                    symbol="AAPL",
                    quantity=100,
                    side="buy",
                    price=150.0
                )
            
            # Force garbage collection and measure
            gc.collect()
            memory = profiler.take_snapshot()
            memory_timeline.append(memory)
            
            print(f"Cycle {cycle + 1:2d} ({(cycle + 1) * ops_per_cycle:4d} ops): "
                  f"{memory:.2f} MB")
        
        # Analyze trend
        if len(memory_timeline) >= 3:
            # Calculate linear regression slope
            x_values = list(range(len(memory_timeline)))
            mean_x = statistics.mean(x_values)
            mean_y = statistics.mean(memory_timeline)
            
            numerator = sum((x - mean_x) * (y - mean_y) 
                          for x, y in zip(x_values, memory_timeline))
            denominator = sum((x - mean_x) ** 2 for x in x_values)
            
            slope = numerator / denominator if denominator != 0 else 0
            
            print(f"\nMemory Growth Rate: {slope:.4f} MB/cycle")
            
            # Extrapolate to 1000 cycles
            projected_growth = slope * 1000
            print(f"Projected Growth (1000 cycles): {projected_growth:.2f} MB")
            print("="*60)
            
            # Slope should be very small (< 0.1 MB per cycle)
            assert abs(slope) < 0.1, \
                f"Memory leak detected: {slope:.4f} MB/cycle growth"
        
        await risk_manager.shutdown()
        profiler.stop_profiling()
    
    async def test_concurrent_operations_memory(self):
        """Test memory usage with many concurrent operations"""
        profiler = MemoryProfiler()
        profiler.start_profiling()
        
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        baseline = profiler.take_snapshot()
        
        print("\n" + "="*60)
        print("CONCURRENT OPERATIONS MEMORY TEST")
        print("="*60)
        print(f"Baseline: {baseline:.2f} MB")
        
        # Launch many concurrent operations
        concurrent_tasks = 1000
        
        async def operation():
            await risk_manager.check_position_risk(
                symbol="AAPL",
                quantity=100,
                side="buy",
                price=150.0
            )
        
        print(f"\nLaunching {concurrent_tasks} concurrent tasks...")
        tasks = [operation() for _ in range(concurrent_tasks)]
        
        during_memory = profiler.get_current_memory()
        print(f"During Execution: {during_memory:.2f} MB "
              f"(Δ {during_memory - baseline:+.2f} MB)")
        
        await asyncio.gather(*tasks)
        
        after_memory = profiler.take_snapshot()
        print(f"After Completion: {after_memory:.2f} MB "
              f"(Δ {after_memory - baseline:+.2f} MB)")
        
        # Clean up
        gc.collect()
        await asyncio.sleep(0.5)
        gc.collect()
        
        cleaned_memory = profiler.take_snapshot()
        print(f"After Cleanup:    {cleaned_memory:.2f} MB "
              f"(Δ {cleaned_memory - baseline:+.2f} MB)")
        print("="*60)
        
        # Memory should return close to baseline after cleanup
        assert abs(cleaned_memory - baseline) < 3.0, \
            "Memory not properly released after concurrent operations"
        
        await risk_manager.shutdown()
        profiler.stop_profiling()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
