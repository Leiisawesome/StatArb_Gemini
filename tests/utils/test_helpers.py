"""
Test utilities for performance monitoring and validation
"""
import time
import psutil
import functools
import numpy as np
from typing import Callable, Any, Dict
from contextlib import contextmanager

class PerformanceMonitor:
    """Monitor and track performance metrics during tests"""
    
    def __init__(self):
        self.metrics = {
            'latency': [],
            'memory': [],
            'cpu': []
        }
    
    def __enter__(self):
        """Enter the context manager"""
        self.start_time = time.perf_counter()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = psutil.Process().cpu_percent()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        end_time = time.perf_counter()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.Process().cpu_percent()
        
        self.metrics['latency'].append((end_time - self.start_time) * 1000)  # ms
        self.metrics['memory'].append(end_memory - self.start_memory)
        self.metrics['cpu'].append(end_cpu - self.start_cpu)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculate statistics for collected metrics"""
        stats = {}
        for metric, values in self.metrics.items():
            if values:
                stats[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'p95': np.percentile(values, 95),
                    'p99': np.percentile(values, 99)
                }
        return stats

def performance_test(latency_threshold_ms: float = 100, memory_threshold_mb: float = 50):
    """Decorator for performance testing"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitor = PerformanceMonitor()
            with monitor.measure('total'):
                result = func(*args, **kwargs)
            
            stats = monitor.get_statistics()
            latency = stats['latency']['mean']
            memory = stats['memory']['mean']
            
            assert latency <= latency_threshold_ms, \
                f"Latency {latency:.2f}ms exceeds threshold {latency_threshold_ms}ms"
            assert memory <= memory_threshold_mb, \
                f"Memory usage {memory:.2f}MB exceeds threshold {memory_threshold_mb}MB"
            
            return result
        return wrapper
    return decorator

class DataValidation:
    """Utilities for validating data structures and results"""
    
    @staticmethod
    def validate_market_data(data: Dict) -> bool:
        """Validate market data structure"""
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        
        for symbol, df in data.items():
            # Check data structure
            assert all(col in df.columns for col in required_columns), \
                f"Missing required columns for {symbol}"
            
            # Check for NaN values
            assert not df.isnull().any().any(), \
                f"Found NaN values in {symbol} data"
            
            # Check price consistency
            assert (df['high'] >= df['low']).all(), \
                f"High price less than low price in {symbol}"
            assert (df['high'] >= df['open']).all(), \
                f"High price less than open price in {symbol}"
            assert (df['high'] >= df['close']).all(), \
                f"High price less than close price in {symbol}"
            
            # Check volume
            assert (df['volume'] >= 0).all(), \
                f"Negative volume in {symbol}"
        
        return True
    
    @staticmethod
    def validate_signal(signal: str) -> bool:
        """Validate trading signal"""
        valid_signals = {'LONG', 'SHORT', 'FLAT'}
        assert signal in valid_signals, f"Invalid signal: {signal}"
        return True
    
    @staticmethod
    def validate_portfolio(portfolio: Dict) -> bool:
        """Validate portfolio structure"""
        required_fields = {'positions', 'cash'}
        assert all(field in portfolio for field in required_fields), \
            "Missing required portfolio fields"
        
        # Validate positions
        for symbol, position in portfolio['positions'].items():
            assert 'quantity' in position, f"Missing quantity for {symbol}"
            assert 'price' in position, f"Missing price for {symbol}"
            
        # Validate cash
        assert portfolio['cash'] >= 0, "Negative cash balance"
        
        return True

def generate_test_data(n_days: int = 252) -> Dict:
    """Generate synthetic market data for testing"""
    import pandas as pd
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq='D')
    symbols = ['TEST1', 'TEST2']
    
    data = {}
    for symbol in symbols:
        # Generate random walk prices
        price = 100 * (1 + np.random.randn(len(dates)).cumsum() * 0.02)
        
        # Add noise to create OHLC
        data[symbol] = pd.DataFrame({
            'open': price * (1 + np.random.randn(len(dates)) * 0.001),
            'high': price * (1 + np.random.randn(len(dates)) * 0.002),
            'low': price * (1 - np.random.randn(len(dates)) * 0.002),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
    
    return data 