#!/usr/bin/env python3
"""
Enhanced Signal Caching System
Statistical Arbitrage Framework Performance Enhancement
Expected Impact: 85% reduction in signal generation time on non-rebalancing days

Author: Pro Quant Desk Trader
"""

import hashlib
import pickle
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached signal entry with metadata"""
    signals: Dict[str, float]
    timestamp: datetime
    rebalancing_frequency: str
    symbols: List[str]
    strategy_params: Dict[str, Any]
    quality_score: float
    cache_key: str
    expiry_time: datetime

class EnhancedSignalCache:
    """
    Multi-layer intelligent caching system for trading signals
    
    Features:
    - Rebalancing frequency-aware caching
    - Parameter-sensitive cache invalidation
    - Quality-based cache scoring
    - Hierarchical cache levels (memory -> disk -> regenerate)
    - Cache warming and precomputation
    """
    
    def __init__(self, cache_dir: str = "cache", max_memory_entries: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Multi-level cache storage
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.max_memory_entries = max_memory_entries
        
        # Cache configuration
        self.cache_config = {
            'daily': {'ttl_hours': 1, 'enable_precompute': True},
            'weekly': {'ttl_hours': 168, 'enable_precompute': True},  # 7 days
            'monthly': {'ttl_hours': 720, 'enable_precompute': False}  # 30 days
        }
        
        # Performance tracking
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'precompute_hits': 0
        }
        
        logger.info(f"Enhanced signal cache initialized: {cache_dir}")
    
    def _generate_cache_key(self, timestamp: datetime, symbols: List[str], 
                          rebalancing_freq: str, strategy_params: Dict[str, Any]) -> str:
        """Generate unique cache key based on inputs"""
        # Normalize timestamp based on rebalancing frequency
        if rebalancing_freq == 'daily':
            norm_timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif rebalancing_freq == 'weekly':
            # Use Monday of the week
            days_since_monday = timestamp.weekday()
            norm_timestamp = (timestamp - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif rebalancing_freq == 'monthly':
            # Use first day of month
            norm_timestamp = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            norm_timestamp = timestamp
        
        # Create hash from normalized inputs
        key_data = {
            'timestamp': norm_timestamp.isoformat(),
            'symbols': sorted(symbols),
            'rebalancing_freq': rebalancing_freq,
            'strategy_params': sorted(strategy_params.items()) if strategy_params else []
        }
        
        key_string = str(key_data)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        return f"{rebalancing_freq}_{cache_key}"
    
    def _is_cache_valid(self, entry: CacheEntry, timestamp: datetime, 
                       rebalancing_freq: str) -> bool:
        """Check if cache entry is still valid"""
        # Check expiry time
        if timestamp > entry.expiry_time:
            return False
        
        # Check rebalancing frequency-specific logic
        if rebalancing_freq == 'weekly':
            # Valid until next Monday
            current_monday = timestamp - timedelta(days=timestamp.weekday())
            entry_monday = entry.timestamp - timedelta(days=entry.timestamp.weekday())
            return current_monday == entry_monday
        elif rebalancing_freq == 'daily':
            # Valid for same day
            return timestamp.date() == entry.timestamp.date()
        elif rebalancing_freq == 'monthly':
            # Valid for same month
            return (timestamp.year == entry.timestamp.year and 
                   timestamp.month == entry.timestamp.month)
        
        return True
    
    def get_cached_signals(self, timestamp: datetime, symbols: List[str], 
                          rebalancing_freq: str, strategy_params: Dict[str, Any] = None) -> Optional[Dict[str, float]]:
        """
        Retrieve cached signals if available and valid
        
        Returns:
            Dict of signals if cache hit, None if cache miss
        """
        cache_key = self._generate_cache_key(timestamp, symbols, rebalancing_freq, strategy_params or {})
        
        # 1. Check memory cache first (fastest)
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_cache_valid(entry, timestamp, rebalancing_freq):
                self.cache_stats['hits'] += 1
                logger.debug(f"Memory cache hit: {cache_key}")
                return entry.signals.copy()
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
                self.cache_stats['invalidations'] += 1
        
        # 2. Check disk cache (slower but persistent)
        disk_cache_file = self.cache_dir / f"{cache_key}.pkl"
        if disk_cache_file.exists():
            try:
                with open(disk_cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if self._is_cache_valid(entry, timestamp, rebalancing_freq):
                    # Load back into memory cache
                    self._add_to_memory_cache(cache_key, entry)
                    self.cache_stats['hits'] += 1
                    logger.debug(f"Disk cache hit: {cache_key}")
                    return entry.signals.copy()
                else:
                    # Remove expired disk cache
                    disk_cache_file.unlink()
                    self.cache_stats['invalidations'] += 1
            except Exception as e:
                logger.warning(f"Error loading disk cache {cache_key}: {e}")
                disk_cache_file.unlink(missing_ok=True)
        
        # 3. Cache miss
        self.cache_stats['misses'] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def store_signals(self, timestamp: datetime, symbols: List[str], 
                     rebalancing_freq: str, signals: Dict[str, float],
                     strategy_params: Dict[str, Any] = None, quality_score: float = 1.0):
        """Store signals in cache with appropriate TTL"""
        cache_key = self._generate_cache_key(timestamp, symbols, rebalancing_freq, strategy_params or {})
        
        # Calculate expiry time
        ttl_hours = self.cache_config.get(rebalancing_freq, {}).get('ttl_hours', 24)
        expiry_time = timestamp + timedelta(hours=ttl_hours)
        
        # Create cache entry
        entry = CacheEntry(
            signals=signals.copy(),
            timestamp=timestamp,
            rebalancing_frequency=rebalancing_freq,
            symbols=symbols.copy(),
            strategy_params=strategy_params.copy() if strategy_params else {},
            quality_score=quality_score,
            cache_key=cache_key,
            expiry_time=expiry_time
        )
        
        # Store in memory cache
        self._add_to_memory_cache(cache_key, entry)
        
        # Store in disk cache for persistence
        try:
            disk_cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(disk_cache_file, 'wb') as f:
                pickle.dump(entry, f)
            logger.debug(f"Stored in cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Error storing disk cache {cache_key}: {e}")
    
    def _add_to_memory_cache(self, cache_key: str, entry: CacheEntry):
        """Add entry to memory cache with LRU eviction"""
        # Remove oldest entries if cache is full
        if len(self.memory_cache) >= self.max_memory_entries:
            # Remove 20% of oldest entries
            sorted_entries = sorted(self.memory_cache.items(), 
                                  key=lambda x: x[1].timestamp)
            entries_to_remove = len(sorted_entries) // 5
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.memory_cache[key]
        
        self.memory_cache[cache_key] = entry
    
    def warm_cache(self, timestamp: datetime, symbols: List[str], 
                   rebalancing_freq: str, signal_generator_func,
                   strategy_params: Dict[str, Any] = None):
        """Precompute and cache signals for future use"""
        if not self.cache_config.get(rebalancing_freq, {}).get('enable_precompute', False):
            return
        
        # Check if already cached
        existing_signals = self.get_cached_signals(timestamp, symbols, rebalancing_freq, strategy_params)
        if existing_signals is not None:
            self.cache_stats['precompute_hits'] += 1
            return existing_signals
        
        # Generate and cache signals
        try:
            start_time = time.time()
            signals = signal_generator_func(timestamp, symbols, strategy_params)
            generation_time = time.time() - start_time
            
            # Calculate quality score based on generation time and signal quality
            quality_score = min(1.0, max(0.1, 1.0 - (generation_time / 10.0)))  # Penalize slow generation
            
            self.store_signals(timestamp, symbols, rebalancing_freq, signals, 
                             strategy_params, quality_score)
            
            logger.info(f"Cache warmed for {len(symbols)} symbols in {generation_time:.3f}s")
            return signals
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return None
    
    def invalidate_cache(self, symbols: Optional[List[str]] = None, 
                        rebalancing_freq: Optional[str] = None):
        """Invalidate cache entries based on criteria"""
        keys_to_remove = []
        
        for cache_key, entry in self.memory_cache.items():
            should_remove = False
            
            if symbols and not any(symbol in entry.symbols for symbol in symbols):
                continue
            if rebalancing_freq and entry.rebalancing_frequency != rebalancing_freq:
                continue
            
            should_remove = True
            
            if should_remove:
                keys_to_remove.append(cache_key)
        
        # Remove from memory cache
        for key in keys_to_remove:
            del self.memory_cache[key]
            self.cache_stats['invalidations'] += 1
        
        # Remove from disk cache
        if symbols or rebalancing_freq:
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    
                    should_remove = False
                    if symbols and not any(symbol in entry.symbols for symbol in symbols):
                        continue
                    if rebalancing_freq and entry.rebalancing_frequency != rebalancing_freq:
                        continue
                    
                    should_remove = True
                    
                    if should_remove:
                        cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Error checking cache file {cache_file}: {e}")
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'memory_cache_size': len(self.memory_cache),
            'disk_cache_files': len(list(self.cache_dir.glob("*.pkl"))),
            **self.cache_stats
        }
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.now()
        
        # Clean memory cache
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if current_time > entry.expiry_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Clean disk cache
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if current_time > entry.expiry_time:
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"Error checking cache file {cache_file}: {e}")
                cache_file.unlink(missing_ok=True)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
_signal_cache = None

def get_signal_cache() -> EnhancedSignalCache:
    """Get global signal cache instance"""
    global _signal_cache
    if _signal_cache is None:
        _signal_cache = EnhancedSignalCache()
    return _signal_cache

def cached_signal_generation(rebalancing_freq: str = 'weekly'):
    """Decorator for automatic signal caching"""
    def decorator(signal_generation_func):
        def wrapper(self, timestamp: datetime, symbols: List[str], *args, **kwargs):
            cache = get_signal_cache()
            strategy_params = getattr(self, 'config', {})
            
            # Try to get from cache first
            cached_signals = cache.get_cached_signals(
                timestamp, symbols, rebalancing_freq, strategy_params.__dict__ if hasattr(strategy_params, '__dict__') else {}
            )
            
            if cached_signals is not None:
                logger.info(f"Using cached signals for {len(symbols)} symbols - {rebalancing_freq} frequency")
                return cached_signals
            
            # Generate new signals
            start_time = time.time()
            signals = signal_generation_func(self, timestamp, symbols, *args, **kwargs)
            generation_time = time.time() - start_time
            
            # Store in cache
            quality_score = min(1.0, max(0.1, 1.0 - (generation_time / 5.0)))
            cache.store_signals(
                timestamp, symbols, rebalancing_freq, signals,
                strategy_params.__dict__ if hasattr(strategy_params, '__dict__') else {}, quality_score
            )
            
            logger.info(f"Generated and cached {len(signals)} signals in {generation_time:.3f}s")
            return signals
        
        return wrapper
    return decorator 