# Market Data Layer

This directory contains the enhanced market data components with improved ClickHouse integration, real-time processing capabilities, and AI-ready interfaces.

## Components

### Core Data Management (`data_manager.py`)
- Centralized market data orchestration
- Multi-source data aggregation
- Real-time and historical data coordination
- Caching and optimization

### Real-Time Feeds (`feeds/`)
- `polygon_feed.py` - Polygon.io real-time data
- `alpha_vantage_feed.py` - Alpha Vantage backup feed
- `feed_manager.py` - Feed orchestration and failover
- `market_microstructure.py` - Market structure analysis

### Data Processing (`processors/`)
- `data_cleaner.py` - Data quality and validation
- `feature_engineer.py` - Technical indicators and features
- `regime_detector.py` - Market regime identification
- `correlation_analyzer.py` - Pair correlation analysis

### Storage & Retrieval (`storage/`)
- `clickhouse_adapter.py` - Enhanced ClickHouse integration
- `cache_manager.py` - Multi-level caching
- `query_optimizer.py` - Query performance optimization

### AI Integration (`ai_interfaces/`)
- `data_streams.py` - AI agent data feeds
- `feature_vectors.py` - ML-ready feature engineering
- `anomaly_detection.py` - AI-powered anomaly detection

## Key Improvements

### Enhanced ClickHouse Integration
- Connection pooling and query optimization
- Parallel data loading and processing
- Advanced analytics queries
- Real-time data ingestion

### Real-Time Processing
- WebSocket-based live feeds
- Low-latency data processing
- Market microstructure analysis
- Liquidity and execution cost estimation

### AI-Ready Features
- Structured data feeds for AI agents
- Feature engineering for ML models
- Real-time anomaly detection
- Knowledge base integration

### Production Optimizations
- Comprehensive error handling
- Performance monitoring
- Automatic failover
- Scalable architecture

## Usage Examples

### Basic Data Loading
```python
from market_data import DataManager

# Initialize data manager
data_manager = DataManager()

# Load historical data
data = data_manager.load_pair_data(['AAPL', 'GOOGL'], days_back=252)

# Get real-time quotes
live_data = data_manager.get_real_time_data(['AAPL', 'GOOGL'])
```

### Advanced Features
```python
# Market microstructure analysis
liquidity = data_manager.analyze_liquidity(['AAPL', 'GOOGL'])

# Regime detection
regimes = data_manager.detect_market_regimes(['AAPL', 'GOOGL'])

# AI data feeds
ai_stream = data_manager.create_ai_data_stream(['AAPL', 'GOOGL'])
```

## Performance Targets

- **Query Latency**: < 100ms for standard queries
- **Real-time Latency**: < 10ms for market data updates
- **Throughput**: 10,000+ ticks/second processing
- **Memory Usage**: < 500MB for typical workloads
- **Cache Hit Rate**: > 90% for frequently accessed data

## Integration Points

### Infrastructure Dependencies
- `infrastructure.database.ClickHouseClient` - Database operations
- `infrastructure.monitoring.MetricsCollector` - Performance tracking
- `infrastructure.messaging.MessageBus` - Event communication
- `infrastructure.config.ConfigManager` - Configuration management

### Future AI Integration
- Real-time data streams for AI agents
- Feature engineering for ML models
- Market anomaly detection
- Automated pair screening 