# Paper Trading System

Professional paper trading platform with advanced monitoring, analytics, and reporting capabilities.

## 🚀 System Overview

This paper trading system provides a complete suite of professional trading tools:

- **Multi-Strategy Trading** - Momentum, Mean Reversion, and Pairs Trading strategies
- **Advanced Order Management** - Stop-loss, take-profit, and trailing stops
- **Real-Time Dashboard** - Web-based monitoring with live updates
- **Advanced Charting** - Technical indicators and performance visualization
- **Alert System** - Multi-channel notifications (Email, SMS, Slack, Discord)
- **Automated Reporting** - Comprehensive reports in multiple formats

## 📁 Directory Structure

```
paper_trading/
├── README.md                           # This file
├── config/                            # Configuration management
│   ├── paper_trading_config_manager.py
│   └── paper_trading_config.yaml
├── dashboard/                         # Advanced dashboard suite
│   ├── __init__.py                   # Package exports
│   ├── data_collector.py            # Real-time data collection
│   ├── analytics_engine.py          # Advanced analytics
│   ├── dashboard_server.py          # Web dashboard server
│   ├── charting_engine.py           # Interactive charts & indicators
│   ├── alert_system.py              # Multi-channel alerts
│   ├── reporting_engine.py          # Automated reporting
│   └── requirements.txt             # Dashboard dependencies
├── multi_strategy_paper_trading.py   # Main multi-strategy engine
├── single_strategy_paper_trading.py  # Single strategy engine
├── multi_strategy_engine.py         # Core multi-strategy coordinator
├── order_manager.py                 # Advanced order management
├── strategy_bridge.py               # Strategy integration bridge
└── priority_3_simple_demo.py        # Complete system demonstration
```

## 🎯 Quick Start

### 1. Basic Multi-Strategy Paper Trading

```bash
python paper_trading/multi_strategy_paper_trading.py
```

### 2. Single Strategy Paper Trading

```bash
python paper_trading/single_strategy_paper_trading.py
```

### 3. Complete System Demonstration

```bash
python paper_trading/priority_3_simple_demo.py
```

## 🏗️ System Architecture

### Core Components

**1. Trading Engines**
- `multi_strategy_paper_trading.py` - Main production system
- `single_strategy_paper_trading.py` - Single strategy testing
- `multi_strategy_engine.py` - Core coordination logic

**2. Advanced Dashboard Suite**
- `data_collector.py` - Real-time data aggregation
- `analytics_engine.py` - Performance and risk analytics
- `dashboard_server.py` - Web-based monitoring interface
- `charting_engine.py` - Technical indicators and charts
- `alert_system.py` - Multi-channel notification system
- `reporting_engine.py` - Automated report generation

**3. Order Management**
- `order_manager.py` - Advanced order types and execution
- `strategy_bridge.py` - Strategy integration layer

**4. Configuration**
- `config/` - Centralized configuration management

## 📈 Features

### Trading Capabilities
- ✅ **3 Trading Strategies** - Momentum, Mean Reversion, Pairs Trading
- ✅ **Advanced Orders** - Stop-loss, take-profit, trailing stops
- ✅ **Risk Management** - Unified risk control across all strategies
- ✅ **IBKR Integration** - Interactive Brokers paper trading
- ✅ **Real-Time Execution** - Live market data and order execution

### Monitoring & Analytics
- ✅ **Real-Time Dashboard** - Web-based interface with live updates
- ✅ **Technical Indicators** - SMA, EMA, Bollinger Bands, RSI, MACD
- ✅ **Performance Analytics** - Sharpe ratio, drawdown, volatility analysis
- ✅ **Strategy Comparison** - Multi-strategy performance attribution
- ✅ **Risk Monitoring** - Real-time risk metrics and alerts

### Alerts & Notifications
- ✅ **Custom Alert Rules** - Flexible condition-based alerts
- ✅ **Multiple Channels** - Email, SMS, Slack, Discord, Webhooks
- ✅ **Severity Levels** - LOW, MEDIUM, HIGH, CRITICAL
- ✅ **Alert History** - Complete audit trail of all alerts
- ✅ **Acknowledgment System** - Alert management and tracking

### Reporting & Export
- ✅ **Automated Reports** - Daily, weekly, monthly summaries
- ✅ **Multiple Formats** - JSON, CSV, HTML, PDF
- ✅ **Performance Reports** - Comprehensive analysis and metrics
- ✅ **Data Export** - Real-time and historical data export
- ✅ **Scheduled Delivery** - Automated report distribution

## 🔧 Configuration

### IBKR Setup
1. Configure TWS API settings
2. Enable paper trading account
3. Set up market data subscriptions
4. Configure connection parameters

### Alert Configuration
```python
# Email notifications
email_config = NotificationConfig(
    channel=NotificationChannel.EMAIL,
    smtp_server="smtp.gmail.com",
    email_username="your_email@gmail.com",
    email_password="your_app_password",
    from_email="your_email@gmail.com",
    to_emails=["recipient@example.com"]
)

# Slack notifications
slack_config = NotificationConfig(
    channel=NotificationChannel.SLACK,
    slack_webhook_url="https://hooks.slack.com/services/...",
    slack_channel="#trading-alerts"
)
```

### Report Configuration
```python
# Daily report
daily_report = ReportConfig(
    report_id="daily_summary",
    name="Daily Trading Summary",
    report_type=ReportType.DAILY_SUMMARY,
    format=ReportFormat.HTML,
    auto_generate=True,
    schedule_time="18:00"
)
```

## 📊 Technical Indicators

### Implemented Indicators
- **SMA (Simple Moving Average)** - 20 and 50 period
- **EMA (Exponential Moving Average)** - 12 and 26 period
- **Bollinger Bands** - 20 period with 2 standard deviations
- **RSI (Relative Strength Index)** - 14 period momentum oscillator
- **MACD** - Moving Average Convergence Divergence with signal line

### Chart Types
- **Price Charts** - OHLCV candlestick data with technical overlays
- **Performance Charts** - Portfolio value, P&L, returns, drawdown
- **Strategy Comparison** - Multi-strategy performance analysis
- **Risk Charts** - Volatility, correlation, risk metrics

## 🚨 Alert System

### Alert Types
- **Risk Alerts** - Drawdown, volatility, position size limits
- **Performance Alerts** - P&L thresholds, return targets
- **Technical Alerts** - Price levels, indicator signals
- **System Alerts** - Connection issues, data problems

### Notification Channels
- **Email** - SMTP integration with HTML formatting
- **SMS** - Email-to-SMS gateway support
- **Slack** - Webhook integration with rich formatting
- **Discord** - Webhook integration with embeds
- **Webhooks** - Custom HTTP endpoints
- **Console** - Real-time console notifications

## 📋 Reports

### Report Types
- **Daily Summary** - End-of-day performance overview
- **Weekly Analysis** - Weekly performance and risk metrics
- **Monthly Reports** - Comprehensive monthly analysis
- **Performance Analysis** - Detailed return and risk analysis
- **Risk Analysis** - VaR, drawdown, correlation analysis
- **Strategy Comparison** - Multi-strategy performance comparison

### Output Formats
- **JSON** - Structured data for API consumption
- **CSV** - Spreadsheet-compatible data export
- **HTML** - Professional web-based reports
- **PDF** - Publication-ready formatted reports

## 🎯 Usage Examples

### Run Multi-Strategy Paper Trading
```bash
# Standard 30-minute session
python paper_trading/multi_strategy_paper_trading.py

# Quick 15-minute test
# Select option 1 when prompted
```

### Test Complete System
```bash
# Full Priority 3 demonstration
python paper_trading/priority_3_simple_demo.py

# Shows all features:
# - Advanced charting with technical indicators
# - Alert system with custom rules
# - Reporting engine with multiple formats
```

### Access Web Dashboard
```bash
# Start dashboard server (requires FastAPI)
python paper_trading/dashboard/dashboard_server.py

# Access at: http://localhost:8080
```

## 🔍 Monitoring

### Real-Time Metrics
- Portfolio value and P&L
- Strategy-specific performance
- Risk metrics (drawdown, volatility, Sharpe ratio)
- Active positions and orders
- Technical indicator values

### Performance Analytics
- Total return and risk-adjusted returns
- Maximum drawdown and current drawdown
- Volatility and correlation analysis
- Win rate and profit factor
- Strategy attribution and comparison

## 🛡️ Risk Management

### Unified Risk Control
- Maximum portfolio drawdown limits
- Position size constraints
- Stop-loss and take-profit automation
- Volatility-based position sizing
- Real-time risk monitoring and alerts

### Risk Metrics
- Value at Risk (VaR) calculations
- Maximum drawdown tracking
- Portfolio volatility monitoring
- Strategy correlation analysis
- Real-time risk limit enforcement

## 🚀 Production Deployment

### Requirements
- Python 3.8+
- Interactive Brokers TWS or IB Gateway
- Market data subscriptions
- Email/SMS service for notifications (optional)
- Web server for dashboard (optional)

### Dependencies
```bash
# Core dependencies
pip install numpy pandas asyncio

# Dashboard dependencies (optional)
pip install fastapi uvicorn websockets

# Notification dependencies (optional)
pip install requests smtplib

# Charting dependencies (optional)
pip install matplotlib plotly
```

### Security Considerations
- Secure credential management
- API rate limiting
- Input validation and sanitization
- Audit logging for all operations
- Configurable access controls

## 📞 Support

For questions or issues:
1. Check the configuration files in `config/`
2. Review the demonstration script: `priority_3_simple_demo.py`
3. Examine the logs for error messages
4. Verify IBKR connection and market data subscriptions

## 🎉 System Evolution

This paper trading system represents the complete evolution from basic backtesting to a professional trading platform:

- ✅ **Foundation** - Backtesting system with 3 strategies
- ✅ **Priority 1** - Advanced Order Management
- ✅ **Priority 2** - Real-Time Dashboard
- ✅ **Priority 3** - Advanced Features (Charting, Alerts, Reporting)

**Result**: Professional-grade trading platform ready for live deployment! 🚀
