# 🚀 Production Setup Guide for Backtest Framework

## 📋 Overview

This guide will help you set up the production dependencies needed to connect your backtest framework with the core system infrastructure, enabling real momentum strategy backtesting with ClickHouse data.

## 🎯 What You'll Achieve

- ✅ **Full Core System Integration**: Connect to production DataManager and ClickHouse
- ✅ **Real Data Access**: Load actual market data from your ClickHouse database  
- ✅ **Production-Ready Backtesting**: Run momentum strategies with real data
- ✅ **Performance Optimization**: Leverage caching and optimized data loading

## 🛠️ Prerequisites

- Python 3.8+
- ClickHouse database (running locally or remotely)
- Market data in ClickHouse (OHLCV format)
- Basic terminal/command line knowledge

## 📦 Step 1: Install Production Dependencies

Run the automated setup script:

```bash
cd backtesting_framework
python setup_production_dependencies.py
```

This script will:
- ✅ Install `clickhouse-driver` and other core dependencies
- ✅ Create production requirements file
- ✅ Set up environment configuration (.env file)
- ✅ Test basic connections and imports
- ✅ Validate framework structure

### Manual Installation (Alternative)

If you prefer manual installation:

```bash
# Install core dependencies
pip install clickhouse-driver>=0.2.6
pip install psycopg2-binary>=2.9.7  
pip install redis>=4.6.0
pip install python-dotenv>=1.0.0
pip install pydantic>=2.0.0

# Install all production requirements
pip install -r requirements_production.txt
```

## 🔧 Step 2: Configure Environment

### 2.1 Edit .env File

The setup script creates a `.env` file. Edit it with your ClickHouse configuration:

```bash
# ClickHouse Database Configuration
CLICKHOUSE_HOST=localhost          # Your ClickHouse host
CLICKHOUSE_PORT=9000              # Your ClickHouse port  
CLICKHOUSE_DATABASE=polygon_data   # Your database name
CLICKHOUSE_USER=default           # Your username
CLICKHOUSE_PASSWORD=              # Your password (if any)

# Environment Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
```

### 2.2 ClickHouse Connection Options

**Local ClickHouse:**
```bash
# If using Docker
docker run -d --name clickhouse -p 9000:9000 clickhouse/clickhouse-server

# If installed locally, ClickHouse typically runs on localhost:9000
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
```

**Remote ClickHouse:**
```bash
CLICKHOUSE_HOST=your-clickhouse-server.com
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=your_username
CLICKHOUSE_PASSWORD=your_password
```

## 🗃️ Step 3: Verify ClickHouse Setup

### 3.1 Test Connection

```bash
# Test ClickHouse connection directly
python Tests/ClickHouse_Manager/clickhouse_manager.py list-tables

# Or test with the integration script
python backtesting_framework/test_production_integration.py
```

### 3.2 Check Your Data

Verify you have market data available:

```bash
# List all tables
python Tests/ClickHouse_Manager/clickhouse_manager.py list-tables

# Check a specific table
python Tests/ClickHouse_Manager/clickhouse_manager.py query "SELECT COUNT(*) FROM your_market_data_table"

# See sample data
python Tests/ClickHouse_Manager/clickhouse_manager.py query "SELECT * FROM your_market_data_table LIMIT 5"
```

### 3.3 Expected Data Format

Your ClickHouse tables should contain OHLCV data in this format:

```sql
-- Example table structure
CREATE TABLE market_data (
    symbol String,
    timestamp DateTime64(3),
    open Float64,
    high Float64, 
    low Float64,
    close Float64,
    volume UInt64
) ENGINE = MergeTree()
ORDER BY (symbol, timestamp);
```

## 🧪 Step 4: Test Integration

### 4.1 Run Integration Tests

```bash
# Comprehensive integration test
python backtesting_framework/test_production_integration.py
```

This will test:
- ✅ Environment configuration
- ✅ Core dependencies 
- ✅ ClickHouse connection
- ✅ Core system imports
- ✅ Data integration manager
- ✅ Actual data loading
- ✅ Experiment framework

### 4.2 Test Framework Components

```bash
# Test data integration only
python backtesting_framework/test_data_integration.py

# Test lightweight framework
python backtesting_framework/test_lightweight_momentum.py
```

## 🚀 Step 5: Run Real Momentum Backtest

Once integration tests pass:

```bash
# Run the real momentum strategy backtest
python backtesting_framework/run_momentum_backtest.py
```

This will:
- 🔄 Connect to your ClickHouse database
- 📊 Load real market data for 50 stocks
- 📈 Execute momentum strategy with risk-adjusted scoring
- 💰 Calculate performance metrics and generate reports
- 📁 Save results to `results/momentum_backtest/`

## 📊 Expected Output

### Successful Backtest Output:
```
🚀 REAL MOMENTUM STRATEGY BACKTEST
============================================================
Using optimized ExperimentRunner with strategy-first architecture

✅ Successfully imported ExperimentRunner
📊 EXPERIMENT CONFIGURATION:
   Strategy: MomentumStrategy
   Universe Size: 50 stocks
   Trading Period: 2024-01-01 to 2024-06-30
   Initial Capital: $250,000

✅ Data Requirements Resolved:
   Symbols: 50 symbols
   Start Date: 2023-01-01
   End Date: 2024-06-30

🎉 BACKTEST COMPLETED SUCCESSFULLY!
📈 PERFORMANCE RESULTS:
Total Return: 12.34%
Annualized Return: 25.67%
Sharpe Ratio: 1.45
Max Drawdown: -8.23%
```

## 🔧 Troubleshooting

### Common Issues and Solutions

**1. ImportError: No module named 'clickhouse_driver'**
```bash
# Solution: Install the dependency
pip install clickhouse-driver>=0.2.6
```

**2. ClickHouse connection failed**
```bash
# Check if ClickHouse is running
docker ps | grep clickhouse

# Start ClickHouse if needed
docker run -d --name clickhouse -p 9000:9000 clickhouse/clickhouse-server

# Test connection manually
python Tests/ClickHouse_Manager/clickhouse_manager.py query "SELECT version()"
```

**3. No data found in ClickHouse**
```bash
# Check available tables
python Tests/ClickHouse_Manager/clickhouse_manager.py list-tables

# Check if tables have data
python Tests/ClickHouse_Manager/clickhouse_manager.py query "SELECT COUNT(*) FROM your_table"
```

**4. Core system import failures**
```bash
# Check if all paths are correct
python -c "import sys; print(sys.path)"

# Verify core_structure directory exists
ls core_structure/market_data/
```

**5. Framework test failures**
```bash
# Run step-by-step diagnosis
python backtesting_framework/test_production_integration.py

# Check specific component
python -c "from utils.data_integration import DataIntegrationManager; print('Success')"
```

## 🎛️ Advanced Configuration

### Performance Optimization

**1. Enable Redis Caching (Optional):**
```bash
# Install Redis
pip install redis>=4.6.0

# Start Redis
docker run -d --name redis -p 6379:6379 redis:alpine

# Add to .env
REDIS_HOST=localhost
REDIS_PORT=6379
```

**2. Optimize ClickHouse Settings:**
```bash
# Edit ClickHouse config for better performance
# In your ClickHouse config.xml:
<max_memory_usage>10000000000</max_memory_usage>
<max_threads>8</max_threads>
```

### Custom Data Sources

**1. Add Custom Tables:**
```python
# In your experiment configuration
strategy_params = {
    "data_table": "your_custom_table",
    "symbol_column": "ticker", 
    "price_columns": ["open", "high", "low", "close"]
}
```

**2. Custom Universe Selection:**
```python
# Override universe selection
strategy_params = {
    "symbols": ["AAPL", "MSFT", "GOOGL"],  # Explicit symbols
    # OR
    "universe_query": "SELECT DISTINCT symbol FROM market_data WHERE market_cap > 1e9"
}
```

## 📈 Next Steps

### 1. Expand Your Strategies
- Create new strategy classes in `strategies/`
- Implement custom momentum variants
- Add mean reversion or pairs trading strategies

### 2. Enhanced Analytics  
- Set up performance attribution analysis
- Add risk management overlays
- Implement portfolio optimization

### 3. Production Deployment
- Set up automated backtesting pipelines
- Add monitoring and alerting
- Implement live trading connections

### 4. Data Enhancement
- Add alternative data sources
- Implement real-time data feeds
- Add fundamental data integration

## 🔗 Resources

- **ClickHouse Manager**: `Tests/ClickHouse_Manager/README.md`
- **Framework Documentation**: `backtesting_framework/README.md`
- **Data Integration Guide**: `backtesting_framework/DATA_INTEGRATION_GUIDE.md`
- **Strategy Development**: `backtesting_framework/strategies/README.md`

## ✅ Success Checklist

- [ ] Python 3.8+ installed
- [ ] Core dependencies installed (`clickhouse-driver`, etc.)
- [ ] `.env` file configured with ClickHouse credentials
- [ ] ClickHouse running and accessible
- [ ] Market data available in ClickHouse
- [ ] Integration tests passing
- [ ] Momentum backtest running successfully
- [ ] Results generated and saved

---

🎉 **Congratulations!** Your backtest framework is now connected to the production core system and ready for serious quantitative research and strategy development!
