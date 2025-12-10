# Historical Data Replay System

The Historical Data Replay System enables testing of live trading components using historical market data streams, eliminating the need to connect to live market feeds during development and testing.

## Overview

This system streams historical market data from ClickHouse with proper timing to simulate real-time market feeds. It integrates seamlessly with the existing StatArb_Gemini event-driven architecture, allowing you to test signal processing, risk management, and execution components with historical data.

## Key Features

- **Real-time Simulation**: Streams historical data with configurable timing to simulate live market conditions
- **Speed Control**: Replay at various speeds (real-time, 2x, 5x, 10x, 50x, 100x, or instant)
- **Market Hours Simulation**: Optionally simulate only market hours (9:30 AM - 4:00 PM ET)
- **Event-Driven Integration**: Works with existing FeedMessage architecture and signal processors
- **Comprehensive Testing**: Test live trading components without market risk

## Architecture

```
Historical Data (ClickHouse) → Replay Engine → Feed Adapter → Signal Processors
                                      ↓
                               Event-Driven Architecture
```

## Quick Start

### Basic Usage

```python
import asyncio
from core_engine.data.replay import HistoricalDataReplayEngine, ReplayConfig, ReplaySpeed

async def main():
    # Configure replay
    config = ReplayConfig(
        symbols=["AAPL", "TSLA", "NVDA"],
        start_date="2024-12-20",
        end_date="2024-12-20",
        speed=ReplaySpeed.FAST_10X  # 10x speed for faster testing
    )

    # Create and initialize engine
    engine = HistoricalDataReplayEngine(config)
    await engine.initialize()

    # Add message handler
    async def handle_message(message):
        print(f"Received: {message.symbol} at {message.timestamp}")

    engine.add_message_handler(handle_message)

    # Start replay
    await engine.start_replay()

    # Wait for completion
    await asyncio.sleep(60)  # Or monitor progress

    # Stop replay
    await engine.stop_replay()

asyncio.run(main())
```

### Feed Adapter Integration

```python
from core_engine.data.replay import HistoricalReplayFeedAdapter, ReplayFeedConfig

async def test_with_adapter():
    config = ReplayFeedConfig(
        replay_symbols=["AAPL", "TSLA"],
        replay_start_date="2024-12-20",
        replay_end_date="2024-12-20",
        replay_speed=ReplaySpeed.REALTIME
    )

    adapter = HistoricalReplayFeedAdapter(config)
    await adapter.connect()
    await adapter.subscribe(["AAPL", "TSLA"], ["bar"])

    # Add your signal processor
    adapter.add_message_handler(your_signal_processor.on_market_data)

    await adapter.start_replay()
```

## Configuration Options

### ReplayConfig

- `symbols`: List of symbols to replay
- `start_date`/`end_date`: Date range (YYYY-MM-DD format)
- `interval`: Data interval ("1min", "5min", "15min", "1h", etc.)
- `speed`: ReplaySpeed enum value
- `simulate_market_hours`: Whether to only replay during market hours
- `batch_size`: Records to load at once
- `max_concurrent_symbols`: Maximum symbols to process simultaneously

### ReplaySpeed Options

- `PAUSED`: Replay paused
- `REALTIME`: 1x real-time speed
- `FAST_2X`: 2x speed
- `FAST_5X`: 5x speed
- `FAST_10X`: 10x speed
- `FAST_50X`: 50x speed
- `FAST_100X`: 100x speed
- `INSTANT`: Replay all data instantly

## Testing Live Components

### Signal Processing

```python
from core_engine.processing.signals import SignalProcessor

class TestSignalProcessor:
    async def on_market_data(self, message):
        # Your signal processing logic here
        # This will receive the same FeedMessage format as live trading
        pass

# Connect to replay system
processor = TestSignalProcessor()
adapter.add_message_handler(processor.on_market_data)
```

### Risk Management

```python
from core_engine.risk import RiskManager

class TestRiskManager:
    async def evaluate_position(self, message):
        # Test risk evaluation with historical data
        pass
```

### Execution Engine

```python
from core_engine.system import UnifiedExecutionEngine

# Test order execution with simulated fills
execution_engine = UnifiedExecutionEngine(test_mode=True)
# Connect to replay for market data, but use test execution
```

## Running Examples

### Basic Example

```bash
cd /path/to/StatArb_Gemini
python -m core_engine.data.replay.example
```

### Speed Test

```bash
python -m core_engine.data.replay.example --speed-test
```

## Integration with Existing Tests

Add to your test files:

```python
import pytest
from core_engine.data.replay import create_replay_adapter

@pytest.fixture
async def replay_adapter():
    adapter = await create_replay_adapter(
        symbols=["AAPL"],
        start_date="2024-12-20",
        end_date="2024-12-20"
    )
    yield adapter
    await adapter.disconnect()

@pytest.mark.asyncio
async def test_signal_processor_with_historical_data(replay_adapter):
    # Test your signal processor with historical data
    pass
```

## Performance Considerations

- **Memory Usage**: Large date ranges may require significant memory
- **Speed vs Accuracy**: Higher speeds may skip timing precision
- **Concurrent Symbols**: Limit concurrent symbols based on system resources
- **Data Preloading**: Initial data loading may take time for large datasets

## Troubleshooting

### Common Issues

1. **ClickHouse Connection Failed**
   - Ensure ClickHouse is running and accessible
   - Check connection configuration in ClickHouseDataConfig

2. **No Data Available**
   - Verify symbols exist in ClickHouse for the specified date range
   - Check data format and column names

3. **Slow Performance**
   - Reduce batch_size or max_concurrent_symbols
   - Use faster replay speeds for testing
   - Consider data indexing in ClickHouse

4. **Memory Issues**
   - Reduce date range or symbol count
   - Increase batch_size to reduce memory fragmentation
   - Monitor system resources during replay

## Advanced Usage

### Custom Data Sources

Extend the replay system to work with other data sources:

```python
class CustomReplayEngine(HistoricalDataReplayEngine):
    async def _load_data_buffer(self):
        # Custom data loading logic
        pass
```

### Event Filtering

Filter events during replay:

```python
def market_hours_only(message):
    # Only process messages during market hours
    return message.timestamp.time() >= time(9, 30) and message.timestamp.time() <= time(16, 0)

adapter.add_message_handler(market_hours_only)
```

### Progress Monitoring

Monitor replay progress:

```python
def progress_handler(status):
    stats = adapter.get_replay_statistics()
    print(f"Progress: {stats['progress_percentage']:.1f}%")

adapter.add_status_handler(progress_handler)
```

## Dependencies

- ClickHouse database with historical market data
- core_engine.data.manager.ClickHouseDataManager
- core_engine.data.feeds.adapters (FeedMessage, etc.)
- asyncio for async operations
- pandas for data manipulation

## Contributing

When adding new features:

1. Maintain compatibility with existing FeedMessage architecture
2. Add comprehensive error handling
3. Include performance monitoring
4. Update documentation and examples
5. Add unit tests for new functionality