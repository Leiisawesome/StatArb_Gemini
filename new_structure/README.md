# Statistical Arbitrage Trading System

## Overview

A modern, production-ready statistical arbitrage trading system built with Python, featuring advanced AI/ML capabilities, real-time data processing, and comprehensive risk management.

## Architecture

The system is organized into the following core modules:

### 🏗️ Infrastructure
- **Database**: ClickHouse, Redis integration with connection pooling
- **Configuration**: Centralized configuration management
- **Deployment**: Docker containerization and production deployment tools
- **Monitoring**: Real-time system monitoring and alerting
- **Messaging**: Event-driven messaging system

### 📊 Data & Analytics
- **Market Data**: Real-time and historical data processing
- **Signal Generation**: Advanced feature engineering and signal detection
- **Analytics**: Performance analytics, reporting, and visualization
- **AI Infrastructure**: LLM integration, vector databases, and AI agents

### 🎯 Trading Engine
- **Strategy Engine**: Multi-strategy execution framework
- **Portfolio Management**: Dynamic portfolio optimization
- **Risk Management**: Real-time risk monitoring and controls
- **Execution Engine**: Smart order routing and execution algorithms

### 🧪 Testing & Optimization
- **Backtesting**: High-fidelity backtesting engine
- **Integration Testing**: End-to-end system validation
- **Optimization**: Performance optimization and parameter tuning
- **Production Validation**: System health and compliance checks

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- ClickHouse database
- Redis cache

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd StatArb_Gemini/new_structure
   ```

2. **Install dependencies**
   ```bash
   pip install -r infrastructure/deployment/requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp infrastructure/config/base_config.yaml.example infrastructure/config/base_config.yaml
   # Edit configuration files as needed
   ```

4. **Start services**
   ```bash
   docker-compose -f infrastructure/deployment/docker-compose.production.yml up -d
   ```

5. **Run tests**
   ```bash
   pytest tests/ -v
   ```

## Configuration

The system uses a hierarchical configuration system:

- `infrastructure/config/base_config.py`: Core system configuration
- `infrastructure/config/database_config.py`: Database connection settings
- `infrastructure/config/trading_config.py`: Trading parameters
- `infrastructure/config/risk_config.py`: Risk management settings
- `infrastructure/config/ai_config.py`: AI/ML model configurations

## Usage

### Basic Trading Workflow

```python
from strategy_engine.strategy_engine import StrategyEngine
from portfolio_management.portfolio_manager import PortfolioManager
from risk_management.risk_manager import RiskManager

# Initialize components
strategy_engine = StrategyEngine()
portfolio_manager = PortfolioManager()
risk_manager = RiskManager()

# Run trading loop
await strategy_engine.run()
```

### Backtesting

```python
from benchmarks.backtesting.engine import BacktestEngine

engine = BacktestEngine()
results = await engine.run_backtest(
    strategy="stat_arb",
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

### Performance Analytics

```python
from analytics.performance_analytics import PerformanceAnalytics

analytics = PerformanceAnalytics()
report = analytics.generate_performance_report()
```

## Development

### Code Structure
```
new_structure/
├── ai_infrastructure/          # AI/ML components
├── analytics/                  # Performance analytics
├── benchmarks/                 # Backtesting framework
├── execution_engine/           # Order execution
├── infrastructure/             # Core infrastructure
├── integration_testing/        # End-to-end tests
├── logs/                       # System logs
├── market_data/               # Data processing
├── optimization/              # Performance optimization
├── portfolio_management/       # Portfolio management
├── production_validation/      # Production checks
├── risk_management/           # Risk controls
├── signal_generation/         # Signal processing
├── strategy_engine/           # Strategy framework
└── tests/                     # Unit tests
```

### Testing

The system includes comprehensive testing:

- **Unit Tests**: `tests/unit/`
- **Integration Tests**: `tests/integration/`
- **Performance Tests**: `tests/performance/`
- **End-to-End Tests**: `integration_testing/`

Run tests with:
```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Contributing

1. Follow PEP 8 style guidelines
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all tests pass before submitting PRs

## Monitoring & Operations

### Health Checks
```bash
# System health
python -m production_validation.system_validator

# Performance metrics
python -m analytics.monitoring_system
```

### Logging
Logs are stored in `logs/` directory with the following structure:
- `logs/system/`: System-level logs
- `logs/trading/`: Trading operation logs
- `logs/archive/`: Archived logs

### Deployment

Production deployment uses Docker:
```bash
docker-compose -f infrastructure/deployment/docker-compose.production.yml up -d
```

## Performance

The system is optimized for:
- **Low Latency**: Sub-millisecond signal processing
- **High Throughput**: 10,000+ trades per second
- **Scalability**: Horizontal scaling support
- **Reliability**: 99.9% uptime target

## Risk Management

Comprehensive risk controls include:
- Real-time position monitoring
- Dynamic exposure limits
- Drawdown protection
- Regulatory compliance checks

## AI/ML Features

- **Signal Generation**: Advanced ML models for pattern detection
- **Portfolio Optimization**: AI-driven allocation strategies
- **Risk Prediction**: ML-based risk forecasting
- **Market Regime Detection**: Automated regime classification

## Support

For technical support or questions:
- Check the documentation in `docs/`
- Review existing issues and discussions
- Contact the development team

## License

[License information]

---

*Built with ❤️ for quantitative finance*
