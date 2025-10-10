"""
Memory Profiler
===============

Track memory usage, leaks, and object allocations.

Features:
1. Memory usage tracking
2. Leak detection
3. Object allocation tracking
4. Memory snapshots and comparisons
"""

import gc
import sys
import psutil
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MemoryProfiler:
    """
    Memory usage profiler with leak detection
    """
    
    def __init__(self, name: str = "memory_profile"):
        self.name = name
        self.process = psutil.Process()
        self.snapshots = []
        self.tracking_enabled = False
        self.start_snapshot = None
    
    def start(self):
        """Start memory tracking"""
        gc.collect()  # Clean up before starting
        tracemalloc.start()
        self.tracking_enabled = True
        self.start_snapshot = tracemalloc.take_snapshot()
    
    def stop(self):
        """Stop memory tracking"""
        if self.tracking_enabled:
            tracemalloc.stop()
            self.tracking_enabled = False
    
    def take_snapshot(self, label: str = None) -> Dict[str, Any]:
        """
        Take a memory snapshot
        
        Args:
            label: Optional label for this snapshot
        
        Returns:
            Snapshot data dictionary
        """
        if not self.tracking_enabled:
            self.start()
        
        # Get process memory info
        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()
        
        # Get tracemalloc snapshot
        snapshot = tracemalloc.take_snapshot()
        
        # Get top memory allocations
        top_stats = snapshot.statistics('lineno')
        
        snapshot_data = {
            'label': label or f"snapshot_{len(self.snapshots)}",
            'timestamp': datetime.now().isoformat(),
            'rss_mb': mem_info.rss / 1024 / 1024,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'percent': mem_percent,
            'top_allocations': [
                {
                    'file': str(stat.traceback[0].filename),
                    'line': stat.traceback[0].lineno,
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }
                for stat in top_stats[:10]
            ]
        }
        
        self.snapshots.append(snapshot_data)
        return snapshot_data
    
    def compare_snapshots(self, snapshot1_idx: int = 0, snapshot2_idx: int = -1) -> Dict[str, Any]:
        """
        Compare two snapshots to detect memory growth
        
        Args:
            snapshot1_idx: Index of first snapshot
            snapshot2_idx: Index of second snapshot
        
        Returns:
            Comparison results
        """
        if len(self.snapshots) < 2:
            return {'error': 'Need at least 2 snapshots to compare'}
        
        snap1 = self.snapshots[snapshot1_idx]
        snap2 = self.snapshots[snapshot2_idx]
        
        comparison = {
            'snapshot1': snap1['label'],
            'snapshot2': snap2['label'],
            'rss_delta_mb': snap2['rss_mb'] - snap1['rss_mb'],
            'vms_delta_mb': snap2['vms_mb'] - snap1['vms_mb'],
            'percent_delta': snap2['percent'] - snap1['percent'],
            'time_delta_seconds': (
                datetime.fromisoformat(snap2['timestamp']) -
                datetime.fromisoformat(snap1['timestamp'])
            ).total_seconds()
        }
        
        return comparison
    
    def detect_leaks(self, threshold_mb: float = 1.0) -> List[Dict[str, Any]]:
        """
        Detect potential memory leaks
        
        Args:
            threshold_mb: Minimum memory growth to flag (MB)
        
        Returns:
            List of potential leaks
        """
        if len(self.snapshots) < 2:
            return []
        
        leaks = []
        
        for i in range(1, len(self.snapshots)):
            comparison = self.compare_snapshots(i-1, i)
            
            if comparison['rss_delta_mb'] > threshold_mb:
                leak = {
                    'from': self.snapshots[i-1]['label'],
                    'to': self.snapshots[i]['label'],
                    'growth_mb': comparison['rss_delta_mb'],
                    'duration_seconds': comparison['time_delta_seconds'],
                    'rate_mb_per_sec': comparison['rss_delta_mb'] / comparison['time_delta_seconds']
                    if comparison['time_delta_seconds'] > 0 else 0
                }
                leaks.append(leak)
        
        return leaks
    
    def get_summary(self) -> Dict[str, Any]:
        """Get memory profiling summary"""
        if not self.snapshots:
            return {'error': 'No snapshots taken'}
        
        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]
        
        total_growth = last_snapshot['rss_mb'] - first_snapshot['rss_mb']
        total_time = (
            datetime.fromisoformat(last_snapshot['timestamp']) -
            datetime.fromisoformat(first_snapshot['timestamp'])
        ).total_seconds()
        
        summary = {
            'name': self.name,
            'snapshots_count': len(self.snapshots),
            'start_memory_mb': first_snapshot['rss_mb'],
            'end_memory_mb': last_snapshot['rss_mb'],
            'total_growth_mb': total_growth,
            'duration_seconds': total_time,
            'avg_growth_rate_mb_per_sec': total_growth / total_time if total_time > 0 else 0,
            'peak_memory_mb': max(s['rss_mb'] for s in self.snapshots),
            'min_memory_mb': min(s['rss_mb'] for s in self.snapshots),
            'leaks_detected': len(self.detect_leaks())
        }
        
        return summary
    
    def print_summary(self):
        """Print memory profiling summary"""
        summary = self.get_summary()
        
        if 'error' in summary:
            print(f"❌ {summary['error']}")
            return
        
        print("\n" + "="*80)
        print(f"MEMORY PROFILE: {summary['name']}")
        print("="*80)
        print(f"\n📊 Overview:")
        print(f"   Snapshots:     {summary['snapshots_count']}")
        print(f"   Duration:      {summary['duration_seconds']:.1f} seconds")
        
        print(f"\n💾 Memory Usage:")
        print(f"   Start:         {summary['start_memory_mb']:.1f} MB")
        print(f"   End:           {summary['end_memory_mb']:.1f} MB")
        print(f"   Peak:          {summary['peak_memory_mb']:.1f} MB")
        print(f"   Min:           {summary['min_memory_mb']:.1f} MB")
        print(f"   Total Growth:  {summary['total_growth_mb']:+.1f} MB")
        print(f"   Growth Rate:   {summary['avg_growth_rate_mb_per_sec']:+.3f} MB/sec")
        
        print(f"\n🔍 Leak Detection:")
        leaks = self.detect_leaks()
        if leaks:
            print(f"   ⚠️  {len(leaks)} potential leak(s) detected!")
            for leak in leaks[:5]:
                print(f"      {leak['from']} → {leak['to']}: +{leak['growth_mb']:.1f} MB ({leak['rate_mb_per_sec']:.3f} MB/s)")
        else:
            print(f"   ✅ No significant leaks detected")
        
        print("\n" + "="*80 + "\n")
    
    def save_results(self, output_dir: Path):
        """Save memory profiling results"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary
        summary_file = output_dir / f"{self.name}_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(self.get_summary(), f, indent=2)
        
        # Save detailed snapshots
        snapshots_file = output_dir / f"{self.name}_snapshots_{timestamp}.json"
        with open(snapshots_file, 'w') as f:
            json.dump(self.snapshots, f, indent=2)
        
        # Save leak report
        leaks = self.detect_leaks()
        if leaks:
            leaks_file = output_dir / f"{self.name}_leaks_{timestamp}.json"
            with open(leaks_file, 'w') as f:
                json.dump(leaks, f, indent=2)
        
        print(f"✅ Memory profile saved to {output_dir}")


def track_memory_growth(func, iterations: int = 10, interval_snapshots: int = 1) -> Dict[str, Any]:
    """
    Track memory growth over multiple function executions
    
    Args:
        func: Function to track
        iterations: Number of iterations
        interval_snapshots: Take snapshot every N iterations
    
    Returns:
        Memory tracking results
    """
    profiler = MemoryProfiler(f"growth_{func.__name__}")
    profiler.start()
    
    # Initial snapshot
    profiler.take_snapshot("start")
    
    # Run function and take snapshots
    for i in range(iterations):
        func()
        
        if (i + 1) % interval_snapshots == 0:
            profiler.take_snapshot(f"iteration_{i+1}")
    
    # Final snapshot
    profiler.take_snapshot("end")
    profiler.stop()
    
    return profiler.get_summary()


def compare_memory_usage(func1, func2, iterations: int = 100) -> Dict[str, Any]:
    """
    Compare memory usage between two functions
    
    Args:
        func1: First function
        func2: Second function
        iterations: Number of iterations for each
    
    Returns:
        Comparison results
    """
    results = {}
    
    # Profile func1
    profiler1 = MemoryProfiler(func1.__name__)
    profiler1.start()
    profiler1.take_snapshot("start")
    
    for _ in range(iterations):
        func1()
    
    profiler1.take_snapshot("end")
    results['func1'] = profiler1.get_summary()
    profiler1.stop()
    
    # Profile func2
    profiler2 = MemoryProfiler(func2.__name__)
    profiler2.start()
    profiler2.take_snapshot("start")
    
    for _ in range(iterations):
        func2()
    
    profiler2.take_snapshot("end")
    results['func2'] = profiler2.get_summary()
    profiler2.stop()
    
    # Compare
    results['comparison'] = {
        'func1_name': func1.__name__,
        'func2_name': func2.__name__,
        'memory_diff_mb': results['func2']['total_growth_mb'] - results['func1']['total_growth_mb'],
        'better_function': func1.__name__ if results['func1']['total_growth_mb'] < results['func2']['total_growth_mb'] else func2.__name__
    }
    
    return results


# Example usage
if __name__ == '__main__':
    print("Testing Memory Profiler\n")
    
    # Test 1: Track memory growth
    def growing_function():
        """Function that allocates memory"""
        data = [i for i in range(100000)]
        return sum(data)
    
    print("Test 1: Tracking memory growth...")
    profiler = MemoryProfiler("growth_test")
    profiler.start()
    
    profiler.take_snapshot("start")
    
    for i in range(5):
        result = growing_function()
        profiler.take_snapshot(f"after_call_{i+1}")
    
    profiler.stop()
    profiler.print_summary()
    
    # Test 2: Memory comparison
    def efficient_sum():
        """Memory efficient sum"""
        return sum(range(100000))
    
    def inefficient_sum():
        """Memory inefficient sum"""
        data = [i for i in range(100000)]
        return sum(data)
    
    print("\nTest 2: Comparing memory usage...")
    comparison = compare_memory_usage(efficient_sum, inefficient_sum, iterations=10)
    
    print(f"\n{comparison['func1_name']}: {comparison['func1']['total_growth_mb']:.3f} MB")
    print(f"{comparison['func2_name']}: {comparison['func2']['total_growth_mb']:.3f} MB")
    print(f"Winner: {comparison['comparison']['better_function']} (diff: {abs(comparison['comparison']['memory_diff_mb']):.3f} MB)")
    
    print("\n✅ Memory profiler tested successfully!")
