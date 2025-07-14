# Infrastructure Layer

This directory contains the core infrastructure components for the StatArb system. These components provide foundational services and utilities used throughout the application.

## Components

### Database (`database/`)
- ClickHouse abstraction layer
- Connection pooling
- Query optimization
- Data schema management

### Messaging (`messaging/`)
- Event-driven architecture
- Message queues for component communication
- Real-time data streaming
- Agent communication bus (AI-ready)

### Monitoring (`monitoring/`)
- System health monitoring
- Performance metrics collection
- Alerting system
- AI agent activity tracking

### Config (`config/`)
- Configuration management
- Environment handling
- Feature flags
- Dynamic settings

## Design Principles

1. **Modularity**: Each component is self-contained with clear interfaces
2. **Scalability**: Built to handle increasing data and computational loads
3. **Observability**: Comprehensive monitoring and debugging capabilities
4. **AI-Ready**: Infrastructure designed for AI/LLM integration
5. **Type Safety**: Strong typing throughout the codebase

## Usage

Each component provides a high-level interface that abstracts away implementation details:

```python
from infrastructure.database import ClickHouseClient
from infrastructure.messaging import MessageBus
from infrastructure.monitoring import MetricsCollector
from infrastructure.config import ConfigManager

# Database usage
db = ClickHouseClient()
data = db.fetch_market_data(symbols=['AAPL', 'GOOGL'])

# Messaging usage
bus = MessageBus()
bus.publish('market_data_update', data)

# Monitoring usage
metrics = MetricsCollector()
metrics.record_latency('data_fetch', 100)

# Configuration usage
config = ConfigManager()
settings = config.get_strategy_settings('pair_trading')
```

## Testing

Each component has its own test suite:
- Unit tests
- Integration tests
- Performance benchmarks
- Failure scenario testing

Run component tests:
```bash
pytest tests/infrastructure/
``` 