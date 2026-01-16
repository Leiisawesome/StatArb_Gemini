"""
High-performance ID generation utilities.
Optimized for the low-latency critical path in StatArb trading.
"""

import time
import threading

class FastIDGenerator:
    """
    Thread-safe, high-speed ID generator.
    Alternative to uuid.uuid4() for high-frequency operations.
    """
    def __init__(self):
        self._counter = 0
        self._last_ts = 0
        self._lock = threading.Lock()
        
    def generate(self) -> str:
        """
        Generate a unique ID based on timestamp and counter.
        Format: <hex_timestamp>-<hex_counter>
        """
        with self._lock:
            ts = int(time.time() * 1000) # Millisecond precision
            if ts == self._last_ts:
                self._counter += 1
            else:
                self._last_ts = ts
                self._counter = 0
            
            return f"{ts:x}-{self._counter:x}"

_generator = FastIDGenerator()

def get_fast_id() -> str:
    """Convenience function for fast ID generation"""
    return _generator.generate()
