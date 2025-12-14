"""
Unit tests for Streaming Buffer Manager.

Tests the StreamingBufferManager class for thread-safe buffer management.
"""

import pytest
import pandas as pd
import threading
from datetime import datetime, timezone

from core_engine.processing.streaming.buffer_manager import StreamingBufferManager

class TestStreamingBufferManager:
    """Test StreamingBufferManager class."""

    @pytest.fixture
    def buffer_manager(self):
        """Create test buffer manager instance."""
        return StreamingBufferManager(buffer_size=100, warmup_required=20)

    def test_initialization(self):
        """Test buffer manager initialization."""
        bm = StreamingBufferManager(buffer_size=50, warmup_required=10)

        assert bm._buffer_size == 50
        assert bm._warmup_required == 10
        assert bm._buffers == {}
        assert bm._warmed_up == set()
        assert bm._column_mapping == {}
        assert hasattr(bm, '_lock')  # Thread lock exists
        assert bm._lock is not None

        expected_stats = {
            'total_updates': 0,
            'symbols_tracked': 0,
            'symbols_warmed_up': 0,
        }
        assert bm._stats == expected_stats

    def test_initialization_default_params(self):
        """Test buffer manager initialization with defaults."""
        bm = StreamingBufferManager()

        assert bm._buffer_size == 500  # default
        assert bm._warmup_required == 200  # default

    def test_normalize_bar_standard_columns(self, buffer_manager):
        """Test bar normalization with standard OHLCV columns."""
        bar = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }

        result = buffer_manager._normalize_bar(bar)

        assert result == bar  # Should be unchanged for standard columns

    def test_normalize_bar_alternate_columns(self, buffer_manager):
        """Test bar normalization with alternate column names."""
        bar = {
            'time': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'o': 100.0,
            'h': 105.0,
            'l': 95.0,
            'c': 102.0,
            'v': 1000,
        }

        result = buffer_manager._normalize_bar(bar)

        expected = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }
        assert result == expected

    def test_normalize_bar_custom_mapping(self):
        """Test bar normalization with custom column mapping."""
        custom_mapping = {'price': 'close', 'qty': 'volume'}
        bm = StreamingBufferManager(column_mapping=custom_mapping)

        bar = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'price': 102.0,
            'qty': 1000,
        }

        result = bm._normalize_bar(bar)

        expected = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'close': 102.0,
            'volume': 1000,
        }
        assert result == expected

    def test_update_new_symbol(self, buffer_manager):
        """Test updating buffer for new symbol."""
        bar = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }

        buffer_manager.update('AAPL', bar)

        # Check buffer was created
        assert 'AAPL' in buffer_manager._buffers
        assert len(buffer_manager._buffers['AAPL']) == 1

        # Check stats
        assert buffer_manager._stats['total_updates'] == 1
        assert buffer_manager._stats['symbols_tracked'] == 1
        assert buffer_manager._stats['symbols_warmed_up'] == 0  # Not warmed up yet

    def test_update_existing_symbol(self, buffer_manager):
        """Test updating buffer for existing symbol."""
        bar1 = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }
        bar2 = {
            'timestamp': datetime(2023, 1, 1, 0, 1, tzinfo=timezone.utc),
            'open': 102.0,
            'high': 107.0,
            'low': 97.0,
            'close': 104.0,
            'volume': 1100,
        }

        buffer_manager.update('AAPL', bar1)
        buffer_manager.update('AAPL', bar2)

        assert len(buffer_manager._buffers['AAPL']) == 2
        assert buffer_manager._stats['total_updates'] == 2
        assert buffer_manager._stats['symbols_tracked'] == 1

    def test_update_buffer_size_limit(self, buffer_manager):
        """Test buffer size limiting."""
        # Create buffer manager with small size
        bm = StreamingBufferManager(buffer_size=3, warmup_required=2)

        # Add 5 bars
        for i in range(5):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            bm.update('AAPL', bar)

        # Should only keep last 3 bars
        assert len(bm._buffers['AAPL']) == 3
        assert bm._buffers['AAPL'].iloc[0]['close'] == 104.0  # Should be bar 2, 3, 4
        assert bm._buffers['AAPL'].iloc[-1]['close'] == 106.0

    def test_update_warmup_trigger(self, buffer_manager):
        """Test warmup status triggering."""
        # Add exactly warmup_required bars
        for i in range(20):  # warmup_required = 20
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        assert buffer_manager.is_warmed_up('AAPL')
        assert buffer_manager._stats['symbols_warmed_up'] == 1

    def test_get_buffer_existing_symbol(self, buffer_manager):
        """Test getting buffer for existing symbol."""
        bar = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }
        buffer_manager.update('AAPL', bar)

        result = buffer_manager.get_buffer('AAPL')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['close'] == 102.0

        # Should be a copy, not the original
        assert result is not buffer_manager._buffers['AAPL']

    def test_get_buffer_nonexistent_symbol(self, buffer_manager):
        """Test getting buffer for nonexistent symbol."""
        result = buffer_manager.get_buffer('NONEXISTENT')

        assert result is None

    def test_get_buffer_view_existing_symbol(self, buffer_manager):
        """Test getting buffer view for existing symbol."""
        bar = {
            'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000,
        }
        buffer_manager.update('AAPL', bar)

        result = buffer_manager.get_buffer_view('AAPL')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Should be the actual buffer, not a copy
        assert result is buffer_manager._buffers['AAPL']

    def test_get_buffer_view_nonexistent_symbol(self, buffer_manager):
        """Test getting buffer view for nonexistent symbol."""
        result = buffer_manager.get_buffer_view('NONEXISTENT')

        assert result is None

    def test_is_warmed_up_true(self, buffer_manager):
        """Test warmup check for warmed up symbol."""
        # Add enough bars to trigger warmup
        for i in range(20):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        assert buffer_manager.is_warmed_up('AAPL')

    def test_is_warmed_up_false(self, buffer_manager):
        """Test warmup check for non-warmed up symbol."""
        # Add fewer bars than required
        for i in range(10):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        assert not buffer_manager.is_warmed_up('AAPL')
        assert not buffer_manager.is_warmed_up('NONEXISTENT')

    def test_get_buffer_length_existing_symbol(self, buffer_manager):
        """Test getting buffer length for existing symbol."""
        for i in range(5):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        assert buffer_manager.get_buffer_length('AAPL') == 5

    def test_get_buffer_length_nonexistent_symbol(self, buffer_manager):
        """Test getting buffer length for nonexistent symbol."""
        assert buffer_manager.get_buffer_length('NONEXISTENT') == 0

    def test_load_warmup_data_with_normalization(self, buffer_manager):
        """Test loading warmup data with column normalization."""
        historical_df = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=50, freq='1min'),
            'o': [100 + i for i in range(50)],
            'h': [105 + i for i in range(50)],
            'l': [95 + i for i in range(50)],
            'c': [102 + i for i in range(50)],
            'v': [1000 + i * 100 for i in range(50)],
        })

        buffer_manager.load_warmup_data('AAPL', historical_df)

        # Should have loaded data
        assert 'AAPL' in buffer_manager._buffers
        assert len(buffer_manager._buffers['AAPL']) == 50  # buffer_size = 100, so all fit

        # Should be warmed up (50 >= 20)
        assert buffer_manager.is_warmed_up('AAPL')

        # Check column names were normalized
        df = buffer_manager._buffers['AAPL']
        assert 'timestamp' in df.columns
        assert 'open' in df.columns
        assert 'close' in df.columns

    def test_load_warmup_data_without_normalization(self, buffer_manager):
        """Test loading warmup data without column normalization."""
        historical_df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=30, freq='1min'),
            'open': [100 + i for i in range(30)],
            'high': [105 + i for i in range(30)],
            'low': [95 + i for i in range(30)],
            'close': [102 + i for i in range(30)],
            'volume': [1000 + i * 100 for i in range(30)],
        })

        buffer_manager.load_warmup_data('AAPL', historical_df, normalize_columns=False)

        # Should have loaded data without renaming
        assert 'AAPL' in buffer_manager._buffers
        assert len(buffer_manager._buffers['AAPL']) == 30

    def test_load_warmup_data_buffer_size_limit(self, buffer_manager):
        """Test that warmup data is limited to buffer size."""
        # Create large historical dataset
        historical_df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=200, freq='1min'),
            'open': [100 + i for i in range(200)],
            'high': [105 + i for i in range(200)],
            'low': [95 + i for i in range(200)],
            'close': [102 + i for i in range(200)],
            'volume': [1000 + i * 100 for i in range(200)],
        })

        buffer_manager.load_warmup_data('AAPL', historical_df)

        # Should only keep last 100 bars (buffer_size)
        assert len(buffer_manager._buffers['AAPL']) == 100
        assert buffer_manager._buffers['AAPL'].iloc[0]['close'] == 102.0 + 100  # First kept bar

    def test_clear_symbol_existing(self, buffer_manager):
        """Test clearing buffer for existing symbol."""
        # Add data and warmup
        for i in range(25):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        assert 'AAPL' in buffer_manager._buffers
        assert buffer_manager.is_warmed_up('AAPL')

        buffer_manager.clear_symbol('AAPL')

        assert 'AAPL' not in buffer_manager._buffers
        assert not buffer_manager.is_warmed_up('AAPL')
        assert buffer_manager._stats['symbols_tracked'] == 0
        assert buffer_manager._stats['symbols_warmed_up'] == 0

    def test_clear_symbol_nonexistent(self, buffer_manager):
        """Test clearing buffer for nonexistent symbol."""
        # Should not raise error
        buffer_manager.clear_symbol('NONEXISTENT')

    def test_clear_all(self, buffer_manager):
        """Test clearing all buffers."""
        # Add multiple symbols
        for symbol in ['AAPL', 'GOOGL', 'MSFT']:
            for i in range(25):
                bar = {
                    'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                    'open': 100.0 + i,
                    'high': 105.0 + i,
                    'low': 95.0 + i,
                    'close': 102.0 + i,
                    'volume': 1000 + i * 100,
                }
                buffer_manager.update(symbol, bar)

        assert len(buffer_manager._buffers) == 3
        assert buffer_manager._stats['symbols_tracked'] == 3

        buffer_manager.clear_all()

        assert len(buffer_manager._buffers) == 0
        assert len(buffer_manager._warmed_up) == 0
        assert buffer_manager._stats['symbols_tracked'] == 0
        assert buffer_manager._stats['symbols_warmed_up'] == 0

    def test_get_tracked_symbols(self, buffer_manager):
        """Test getting list of tracked symbols."""
        symbols = ['AAPL', 'GOOGL', 'MSFT']

        for symbol in symbols:
            bar = {
                'timestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 1000,
            }
            buffer_manager.update(symbol, bar)

        tracked = buffer_manager.get_tracked_symbols()
        assert set(tracked) == set(symbols)

    def test_get_warmed_up_symbols(self, buffer_manager):
        """Test getting list of warmed up symbols."""
        # Add symbols with different warmup status
        for symbol in ['AAPL', 'GOOGL']:
            bars_needed = 25 if symbol == 'AAPL' else 15  # Only AAPL gets enough bars
            for i in range(bars_needed):
                bar = {
                    'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                    'open': 100.0 + i,
                    'high': 105.0 + i,
                    'low': 95.0 + i,
                    'close': 102.0 + i,
                    'volume': 1000 + i * 100,
                }
                buffer_manager.update(symbol, bar)

        warmed_up = buffer_manager.get_warmed_up_symbols()
        assert warmed_up == ['AAPL']

    def test_get_stats(self, buffer_manager):
        """Test getting buffer manager statistics."""
        # Add some data
        for i in range(25):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        stats = buffer_manager.get_stats()

        assert stats['total_updates'] == 25
        assert stats['symbols_tracked'] == 1
        assert stats['symbols_warmed_up'] == 1
        assert stats['buffer_size'] == 100
        assert stats['warmup_required'] == 20

    def test_get_last_bar_existing_symbol(self, buffer_manager):
        """Test getting last bar for existing symbol."""
        for i in range(3):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        last_bar = buffer_manager.get_last_bar('AAPL')

        assert last_bar is not None
        assert last_bar['close'] == 104.0  # Last bar
        assert last_bar['volume'] == 1200

    def test_get_last_bar_nonexistent_symbol(self, buffer_manager):
        """Test getting last bar for nonexistent symbol."""
        result = buffer_manager.get_last_bar('NONEXISTENT')

        assert result is None

    def test_get_last_bar_empty_buffer(self, buffer_manager):
        """Test getting last bar when buffer exists but is empty."""
        # This shouldn't happen in practice, but test edge case
        buffer_manager._buffers['AAPL'] = pd.DataFrame()

        result = buffer_manager.get_last_bar('AAPL')

        assert result is None

    def test_get_last_n_bars_existing_symbol(self, buffer_manager):
        """Test getting last N bars for existing symbol."""
        for i in range(10):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        last_3 = buffer_manager.get_last_n_bars('AAPL', 3)

        assert isinstance(last_3, pd.DataFrame)
        assert len(last_3) == 3
        assert last_3.iloc[-1]['close'] == 111.0  # Bar 9

    def test_get_last_n_bars_nonexistent_symbol(self, buffer_manager):
        """Test getting last N bars for nonexistent symbol."""
        result = buffer_manager.get_last_n_bars('NONEXISTENT', 5)

        assert result is None

    def test_get_state_for_checkpoint(self, buffer_manager):
        """Test getting state for checkpointing."""
        # Add some data
        for i in range(5):
            bar = {
                'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                'open': 100.0 + i,
                'high': 105.0 + i,
                'low': 95.0 + i,
                'close': 102.0 + i,
                'volume': 1000 + i * 100,
            }
            buffer_manager.update('AAPL', bar)

        state = buffer_manager.get_state_for_checkpoint()

        assert state['buffer_size'] == 100
        assert state['warmup_required'] == 20
        assert 'AAPL' in state['buffers']
        assert len(state['buffers']['AAPL']) == 5

    def test_restore_from_checkpoint(self, buffer_manager):
        """Test restoring state from checkpoint."""
        state = {
            'buffer_size': 50,
            'warmup_required': 10,
            'buffers': {
                'AAPL': [
                    {
                        'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                        'open': 100.0 + i,
                        'high': 105.0 + i,
                        'low': 95.0 + i,
                        'close': 102.0 + i,
                        'volume': 1000 + i * 100,
                    }
                    for i in range(15)  # More than warmup_required
                ]
            }
        }

        buffer_manager.restore_from_checkpoint(state)

        assert buffer_manager._buffer_size == 50
        assert buffer_manager._warmup_required == 10
        assert 'AAPL' in buffer_manager._buffers
        assert len(buffer_manager._buffers['AAPL']) == 15
        assert buffer_manager.is_warmed_up('AAPL')
        assert buffer_manager._stats['symbols_tracked'] == 1
        assert buffer_manager._stats['symbols_warmed_up'] == 1

    def test_thread_safety(self, buffer_manager):
        """Test thread safety of buffer operations."""
        results = []
        errors = []

        def worker(symbol, num_updates):
            try:
                for i in range(num_updates):
                    bar = {
                        'timestamp': datetime(2023, 1, 1, 0, i, tzinfo=timezone.utc),
                        'open': 100.0 + i,
                        'high': 105.0 + i,
                        'low': 95.0 + i,
                        'close': 102.0 + i,
                        'volume': 1000 + i * 100,
                    }
                    buffer_manager.update(symbol, bar)
                results.append(f"{symbol}: {buffer_manager.get_buffer_length(symbol)}")
            except Exception as e:
                errors.append(f"{symbol}: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            symbol = f'SYMBOL_{i}'
            t = threading.Thread(target=worker, args=(symbol, 20))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5

        # Each symbol should have 20 updates
        for result in results:
            assert "20" in result

        # Total updates should be 100 (5 symbols * 20 updates each)
        assert buffer_manager._stats['total_updates'] == 100