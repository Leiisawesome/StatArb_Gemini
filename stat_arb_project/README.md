# Statistical Arbitrage Trading System

An institutional-grade statistical arbitrage trading platform for pair trading of stocks, ETFs, and leveraged ETFs.

## 🚀 Production Ready Features

- **Advanced Kalman Filter**: Professional implementation with online updating
- **Robust Cointegration Testing**: Johansen and Engle-Granger tests with structural break detection
- **Walk-Forward Analysis**: Out-of-sample validation for strategy robustness
- **Production Risk Management**: Position sizing, risk limits, and portfolio optimization
- **Execution Quality**: Market impact modeling and slippage estimation
- **Multi-Pair Portfolio Management**: Cross-asset allocation and correlation-based sizing
- **Advanced Signal Generation**: Regime detection, volatility clustering, and ML enhancement
- **Structured Logging**: Production-ready logging with monitoring and alerting
- **Configuration Management**: Environment-based configuration with validation
- **Docker Support**: Complete containerization with monitoring stack

## 📊 System Architecture

```
stat_arb_project/
├── config/                 # Production configuration
├── data/                   # Data loading and validation
├── model/                  # Statistical models (Kalman, cointegration)
├── strategies/             # Trading strategies
├── execution/              # Order management and execution
├── portfolio/              # Portfolio optimization and management
├── signals/                # Advanced signal generation
├── backtesting/            # Production backtesting engine
├── evaluation/             # Performance evaluation
├── utils/                  # Utilities and logging
├── dashboard/              # Web-based monitoring dashboard
└── tests/                  # Comprehensive test suite
```

## 🛠 Installation

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for production deployment)
- PostgreSQL (for production data storage)
- Redis (for caching and real-time data)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd StatArb_Gemini
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r stat_arb_project/requirements.txt
   ```

4. **Run basic test**
   ```bash
   python -c "import stat_arb_project; print('Installation successful!')"
   ```

### Production Deployment

1. **Using Docker Compose (Recommended)**
   ```bash
   # Start all services
   docker-compose up -d
   
   # View logs
   docker-compose logs -f stat-arb-app
   
   # Stop services
   docker-compose down
   ```

2. **Manual Production Setup**
   ```bash
   # Set environment variables
   export ENVIRONMENT=production
   export DB_HOST=localhost
   export DB_PASSWORD=your_password
   export REDIS_HOST=localhost
   
   # Run production system
   python stat_arb_project/production_main.py --mode backtest
   ```

## 🎯 Usage

### Data Loading

The system supports loading data from Polygon.io CSV files for high-quality backtesting:

```bash
# Place your Polygon.io CSV files in /Users/lei/Documents/data/polygon/ directory
# The system will automatically detect and load available data

# Test data loading
python test_data_loading.py
```

**Configuration Options:**

1. **Default Configuration**: Uses `/Users/lei/Documents/data/polygon` by default
2. **Custom Configuration**: Modify `stat_arb_project/config/data_config.yaml`
3. **Environment Variables**: Set `POLYGON_DATA_DIR` environment variable
4. **Code Configuration**: Pass custom `DataConfig` to loaders

### Quick Start - Backtesting

```bash
# Run backtest with default settings
python stat_arb_project/production_main.py --mode backtest

# Custom backtest
python stat_arb_project/production_main.py \
  --mode backtest \
  --symbol1 AAPL \
  --symbol2 MSFT \
  --start-date 2023-01-01 \
  --end-date 2023-12-31
```

### Configuration

The system supports multiple configuration methods:

1. **Environment Variables** (Production)
   ```bash
   # Trading parameters
   export INITIAL_CAPITAL=1000000
   export MAX_POSITION_SIZE=0.15
   export TARGET_VOLATILITY=0.12
   
   # Data directory (optional - defaults to /Users/lei/Documents/data/polygon)
   export POLYGON_DATA_DIR="/Users/lei/Documents/data/polygon"
   ```

2. **Configuration File** (Development)
   ```yaml
   # config.yaml
   environment: production
   trading:
     initial_capital: 1000000
     max_position_size: 0.15
     target_volatility: 0.12
   ```

3. **Command Line Arguments**
   ```bash
   python stat_arb_project/production_main.py \
     --config config.yaml \
     --mode backtest
   ```

## 📈 Key Features

### Advanced Statistical Models
- **Kalman Filter**: Online updating with adaptive parameters
- **Cointegration Testing**: Multiple methodologies with structural break detection
- **Walk-Forward Analysis**: Robust out-of-sample validation

### Risk Management
- **Position Sizing**: Kelly criterion and volatility targeting
- **Risk Limits**: Maximum drawdown, leverage, and concentration limits
- **Portfolio Optimization**: Multi-pair allocation with correlation constraints

### Execution Quality
- **Market Impact Modeling**: Realistic slippage estimation
- **Order Management**: Smart order routing and position tracking
- **Performance Monitoring**: Real-time metrics and alerting

### Signal Generation
- **Regime Detection**: Market state identification
- **Volatility Clustering**: GARCH-based volatility modeling
- **ML Enhancement**: Ensemble methods for signal improvement
- **Alternative Data**: Sentiment, macro, and flow data integration

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest stat_arb_project/tests/

# Run specific test categories
pytest stat_arb_project/tests/test_kalman.py
pytest stat_arb_project/tests/test_cointegration.py
pytest stat_arb_project/tests/test_strategy.py
```

### Code Quality
```bash
# Linting
flake8 stat_arb_project/

# Type checking
mypy stat_arb_project/

# Security scanning
bandit -r stat_arb_project/
```

## 📊 Monitoring

### Dashboard Access
- **Grafana**: http://localhost:3000 (admin/admin)
- **Application Logs**: `docker-compose logs -f stat-arb-app`
- **Database**: PostgreSQL on localhost:5432

### Key Metrics
- **Performance**: Total return, Sharpe ratio, max drawdown
- **Risk**: VaR, position concentration, leverage
- **Execution**: Slippage, fill rates, order latency
- **System**: CPU, memory, database connections

## 🚨 Production Considerations

### Security
- All sensitive data encrypted at rest
- Environment-based configuration
- Secure API endpoints with authentication
- Regular security audits

### Performance
- Optimized data processing pipelines
- Efficient memory management
- Database connection pooling
- Caching for frequently accessed data

### Reliability
- Comprehensive error handling
- Graceful degradation
- Automated failover
- Regular backups

### Scalability
- Horizontal scaling support
- Load balancing capabilities
- Microservices architecture ready
- Cloud deployment support

## 📚 Documentation

- **API Documentation**: Available in code docstrings
- **Configuration Guide**: See `config/` directory
- **Strategy Documentation**: See `strategies/` directory
- **Model Documentation**: See `model/` directory

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not intended for live trading without proper testing and validation. The authors are not responsible for any financial losses incurred through the use of this software.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information
4. Contact the development team

---

**Status**: Production Ready - Research and Paper Trading  
**Version**: 2.0.0  
**Last Updated**: 2024 