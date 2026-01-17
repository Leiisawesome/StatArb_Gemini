"""
High-performance ID generation utilities.
Optimized for the low-latency critical path in StatArb trading.
"""

import time
import threading
import itertools

class FastIDGenerator:
    """
    Thread-safe, lock-free (CPython) high-speed ID generator.
    Alternative to uuid.uuid4() for high-frequency operations.
    """
    def __init__(self):
        self._iterator = itertools.count()
        
    def generate(self) -> str:
        """
        Generate a unique ID based on timestamp and counter.
        Format: <hex_timestamp>-<hex_counter>
        Uses nanosecond precision and atomic counter.
        """
        return f"{time.time_ns():x}-{next(self._iterator):x}"

_generator = FastIDGenerator()

def get_fast_id() -> str:
    """Convenience function for fast ID generation"""
    return _generator.generate()
