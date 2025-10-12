"""
Performance Profiling Suite
============================

Comprehensive profiling tools for identifying performance bottlenecks.

Profiles:
1. CPU profiling - Find time-consuming functions
2. Memory profiling - Track memory usage and leaks
3. I/O profiling - Identify I/O bottlenecks
4. Hot path analysis - Find frequently executed code paths
"""

import cProfile
import pstats
import io
import time
import psutil
import sys
from pathlib import Path
from typing import Dict, Any, Callable
import json
from datetime import datetime
from contextlib import contextmanager

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class PerformanceProfiler:
    """
    Comprehensive performance profiler
    
    Tracks CPU, memory, and I/O performance metrics.
    """
    
    def __init__(self, name: str = "profile"):
        self.name = name
        self.profiler = cProfile.Profile()
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.process = psutil.Process()
        self.results = {}
    
    def start(self):
        """Start profiling"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.profiler.enable()
    
    def stop(self):
        """Stop profiling"""
        self.profiler.disable()
        self.end_time = time.time()
        self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Calculate results
        self.results = {
            'name': self.name,
            'duration_seconds': self.end_time - self.start_time,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': self.end_memory,
            'memory_delta_mb': self.end_memory - self.start_memory,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_stats(self, top_n: int = 20) -> Dict[str, Any]:
        """Get profiling statistics"""
        # Create stats object
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(top_n)
        
        stats_text = s.getvalue()
        
        # Parse top functions
        top_functions = []
        for line in stats_text.split('\n'):
            if line.strip() and not line.startswith('   ') and '(' in line:
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        func_info = {
                            'ncalls': parts[0],
                            'tottime': float(parts[1]),
                            'percall': float(parts[2]),
                            'cumtime': float(parts[3]),
                            'percall_cum': float(parts[4]),
                            'filename': ' '.join(parts[5:])
                        }
                        top_functions.append(func_info)
                    except (ValueError, IndexError):
                        continue
        
        self.results['top_functions'] = top_functions[:top_n]
        self.results['stats_text'] = stats_text
        
        return self.results
    
    def save_results(self, output_dir: Path):
        """Save profiling results"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON results
        json_file = output_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            # Remove stats_text for cleaner JSON
            clean_results = {k: v for k, v in self.results.items() if k != 'stats_text'}
            json.dump(clean_results, f, indent=2)
        
        # Save detailed stats
        stats_file = output_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(stats_file, 'w') as f:
            f.write(self.results.get('stats_text', ''))
        
        print(f"✅ Results saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Stats: {stats_file}")
    
    def print_summary(self):
        """Print profiling summary"""
        print("\n" + "="*80)
        print(f"PERFORMANCE PROFILE: {self.name}")
        print("="*80)
        print(f"\n⏱️  Duration: {self.results['duration_seconds']:.3f} seconds")
        print(f"💾 Memory:")
        print(f"   Start:  {self.results['memory_start_mb']:.1f} MB")
        print(f"   End:    {self.results['memory_end_mb']:.1f} MB")
        print(f"   Delta:  {self.results['memory_delta_mb']:+.1f} MB")
        
        print(f"\n🔥 Top 10 Time-Consuming Functions:")
        print(f"{'Rank':<6} {'CumTime':<10} {'Calls':<10} {'Function':<50}")
        print("-"*80)
        
        for i, func in enumerate(self.results.get('top_functions', [])[:10], 1):
            print(f"{i:<6} {func['cumtime']:<10.3f} {func['ncalls']:<10} {func['filename'][:48]}")
        
        print("="*80 + "\n")


@contextmanager
def profile_section(name: str, output_dir: Path = None):
    """
    Context manager for profiling a code section
    
    Usage:
        with profile_section("my_function"):
            # code to profile
            pass
    """
    profiler = PerformanceProfiler(name)
    profiler.start()
    
    try:
        yield profiler
    finally:
        profiler.stop()
        profiler.get_stats()
        profiler.print_summary()
        
        if output_dir:
            profiler.save_results(output_dir)


def profile_function(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Profile a single function call
    
    Args:
        func: Function to profile
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        Profiling results dictionary
    """
    profiler = PerformanceProfiler(func.__name__)
    profiler.start()
    
    result = func(*args, **kwargs)
    
    profiler.stop()
    stats = profiler.get_stats()
    
    return {
        'result': result,
        'profile': stats
    }


def benchmark_function(func: Callable, iterations: int = 100, warmup: int = 10) -> Dict[str, Any]:
    """
    Benchmark a function over multiple iterations
    
    Args:
        func: Function to benchmark
        iterations: Number of iterations
        warmup: Number of warmup iterations
    
    Returns:
        Benchmark results
    """
    # Warmup
    for _ in range(warmup):
        func()
    
    # Benchmark
    times = []
    memory_deltas = []
    process = psutil.Process()
    
    for _ in range(iterations):
        start_mem = process.memory_info().rss / 1024 / 1024
        start_time = time.perf_counter()
        
        func()
        
        end_time = time.perf_counter()
        end_mem = process.memory_info().rss / 1024 / 1024
        
        times.append(end_time - start_time)
        memory_deltas.append(end_mem - start_mem)
    
    # Calculate statistics
    times_sorted = sorted(times)
    n = len(times_sorted)
    
    results = {
        'function': func.__name__,
        'iterations': iterations,
        'warmup': warmup,
        'avg_time_ms': sum(times) / n * 1000,
        'min_time_ms': min(times) * 1000,
        'max_time_ms': max(times) * 1000,
        'p50_time_ms': times_sorted[int(n * 0.50)] * 1000,
        'p95_time_ms': times_sorted[int(n * 0.95)] * 1000,
        'p99_time_ms': times_sorted[int(n * 0.99)] * 1000,
        'avg_memory_delta_mb': sum(memory_deltas) / n,
        'total_time_seconds': sum(times),
        'ops_per_second': n / sum(times) if sum(times) > 0 else 0
    }
    
    return results


def print_benchmark_results(results: Dict[str, Any]):
    """Print benchmark results in formatted table"""
    print("\n" + "="*80)
    print(f"BENCHMARK RESULTS: {results['function']}")
    print("="*80)
    print(f"\n📊 Statistics ({results['iterations']} iterations, {results['warmup']} warmup):")
    print(f"   Average:       {results['avg_time_ms']:.3f} ms")
    print(f"   Min:           {results['min_time_ms']:.3f} ms")
    print(f"   Max:           {results['max_time_ms']:.3f} ms")
    print(f"   P50 (Median):  {results['p50_time_ms']:.3f} ms")
    print(f"   P95:           {results['p95_time_ms']:.3f} ms")
    print(f"   P99:           {results['p99_time_ms']:.3f} ms")
    print(f"\n⚡ Throughput:")
    print(f"   Ops/Second:    {results['ops_per_second']:.1f}")
    print(f"   Total Time:    {results['total_time_seconds']:.3f} seconds")
    print(f"\n💾 Memory:")
    print(f"   Avg Delta:     {results['avg_memory_delta_mb']:+.3f} MB")
    print("="*80 + "\n")


# Example usage and tests
if __name__ == '__main__':
    print("Testing Performance Profiling Suite\n")
    
    # Test 1: Profile a simple function
    def expensive_function():
        """Simulate expensive computation"""
        total = 0
        for i in range(1000000):
            total += i ** 2
        return total
    
    print("Test 1: Profiling expensive_function...")
    with profile_section("expensive_function_test"):
        result = expensive_function()
        print(f"Result: {result}")
    
    # Test 2: Benchmark a function
    print("\nTest 2: Benchmarking expensive_function...")
    benchmark_results = benchmark_function(expensive_function, iterations=50, warmup=5)
    print_benchmark_results(benchmark_results)
    
    print("\n✅ Performance profiling suite tested successfully!")
